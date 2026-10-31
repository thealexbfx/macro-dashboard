"""Exact selected official-source parsers. Never infer panels or unit conversions."""

import csv
import io
import json
import re
from datetime import datetime

from backend.app.ingestion.formats import parse_payload, source_key
from backend.app.ingestion.native import Definition, Observation, SourceCalendar


def definition(entry, *, dimensions=(), units=None, adjustment=None, multiplier=0):
    return Definition(
        entry["id"],
        entry["source"]["provider"],
        entry["source"]["selector"],
        units or entry["units"],
        entry["frequency"],
        adjustment or entry["seasonal_adjustment"],
        SourceCalendar(
            f"{entry['source']['provider']}_{entry['frequency']}",
            week_ending=4 if entry["frequency"] == "weekly" else None,
        ),
        tuple(sorted(dimensions)),
        multiplier,
    )


def parse_eurostat(entry, body):
    data = json.loads(body)
    dimensions = []
    labels = {}
    for axis in data["id"]:
        if axis == "time":
            continue
        category = data["dimension"][axis]["category"]
        keys = list(category["index"])
        if len(keys) != 1:
            raise ValueError("Unpinned Eurostat selection")
        dimensions.append((axis, keys[0]))
        labels[axis] = category.get("label", {}).get(keys[0], keys[0])
    # Compare actual returned dimensions with the documented exact SDMX key.
    expected = entry["source"]["selector"].split(" | ")[-1].split(".")
    if set(expected) != {v for _, v in dimensions}:
        raise ValueError("Eurostat selection drift")
    if dict(dimensions).get("geo") not in {
        "DE",
        "FR",
        "IT",
        "EA20",
        "EA21",
        "EA19",
        "EU27_2020",
    }:
        raise ValueError("Country is outside this reviewed Eurostat release")
    d = definition(entry, dimensions=dimensions)
    points = parse_payload(d, body, max_rows=1000)
    return (
        d,
        points,
        {
            "title": data.get("label"),
            "updated": data.get("updated"),
            "dimension_labels": labels,
            "unit_label": labels.get("unit"),
            "source": data.get("source"),
        },
    )


def parse_ons(entry, body):
    data = json.loads(body)
    desc = data["description"]
    if desc["cdid"].casefold() != entry["source"]["selector"].split("/")[0].casefold():
        raise ValueError("ONS identity mismatch")
    field = {"monthly": "months", "quarterly": "quarters", "annual": "years"}[
        entry["frequency"]
    ]
    # Unit/base must be supplied by the producer; never infer a current index base.
    unit = desc.get("unit", "").strip()
    preunit = desc.get("preUnit", "").strip()
    if not unit and not preunit:
        raise ValueError("ONS unit not supplied; producer metadata review needed")
    actual_unit = f"{preunit} {unit}".strip()
    title = desc.get("title", "")
    d = definition(entry, units=actual_unit)
    records = data[field]
    points = []
    for offset in range(0, len(records), 1000):
        part = {"description": desc, field: records[offset : offset + 1000]}
        points.extend(parse_payload(d, json.dumps(part).encode(), max_rows=1000))
    return (
        d,
        tuple(points),
        {
            "title": title,
            "unit_label": actual_unit,
            "release_date": desc.get("releaseDate"),
            "next_release": desc.get("nextRelease"),
            "notes": desc.get("summary", "")[:2000],
        },
    )


def parse_sdmx(entry, body):
    rows = list(csv.DictReader(io.StringIO(body.decode("utf-8-sig"))))
    if not rows:
        raise ValueError("Empty SDMX selection")
    excluded = {
        "TIME_PERIOD",
        "OBS_VALUE",
        "OBS_STATUS",
        "DECIMALS",
        "UNIT_MULT",
        "BASE_PER",
        "DATAFLOW",
        "STRUCTURE",
        "STRUCTURE_ID",
        "ACTION",
    }
    dimensions = [(k, v) for k, v in rows[0].items() if k not in excluded]
    if entry["source"]["provider"] == "ecb":
        expected_key = entry["source"]["selector"].replace("/", ".")
        unit = rows[0].get("UNIT") or rows[0].get("UNIT_MEASURE")
        expected_unit = (
            "EUR"
            if expected_key.startswith("BSI.")
            else "PC"
            if expected_key.startswith("EST.")
            else "PCPA"
            if expected_key.startswith("FM.")
            else expected_key.split(".")[2]
        )
        if unit != expected_unit or any(
            r.get("KEY") != expected_key
            or (r.get("UNIT") or r.get("UNIT_MEASURE")) != expected_unit
            for r in rows
        ):
            raise ValueError("ECB source identity/unit changed")
        dimensions = [("KEY", expected_key), ("FREQ", rows[0]["FREQ"])]
    if any(any(r.get(k) != v for k, v in dimensions) for r in rows):
        raise ValueError("Multiple SDMX series returned")
    multiplier = int(rows[0].get("UNIT_MULT") or 0)
    if any(int(r.get("UNIT_MULT") or 0) != multiplier for r in rows):
        raise ValueError("Historical unit multiplier changed")
    d = definition(entry, dimensions=dimensions, multiplier=multiplier)
    points = []
    for row in rows:
        value = row["OBS_VALUE"]
        points.append(
            Observation(
                source_key(row["TIME_PERIOD"], d.frequency, d.provider),
                row["TIME_PERIOD"],
                float(value) if value not in {"", ":", "NA"} else None,
                tuple(
                    f"{k}={row[k]}"
                    for k in ("OBS_STATUS", "UNIT_MULT", "BASE_PER")
                    if row.get(k)
                ),
            )
        )
    return (
        d,
        tuple(points),
        {
            "dimensions": dict(dimensions),
            "unit_multiplier": multiplier,
            "title": rows[0].get("TITLE_COMPL", ""),
            "source_unit": rows[0].get("UNIT") or rows[0].get("UNIT_MEASURE"),
            "base_periods": sorted({r.get("BASE_PER", "") for r in rows}),
        },
    )


def excel_rows(body, sheet):
    # The provider's zip safety guard is reused by the workbook-specific parser.
    # openpyxl read-only mode avoids constructing the full workbook in memory.
    import zipfile

    from openpyxl import load_workbook

    with zipfile.ZipFile(io.BytesIO(body)) as archive:
        if sum(i.file_size for i in archive.infolist()) > 64 * 1024 * 1024:
            raise ValueError("Workbook expansion exceeds budget")
    workbook = load_workbook(io.BytesIO(body), read_only=True, data_only=True)
    try:
        if sheet not in workbook.sheetnames:
            raise ValueError("Source sheet changed")
        return list(workbook[sheet].values)
    finally:
        workbook.close()


PARSERS = {
    "eurostat": parse_eurostat,
    "ons": parse_ons,
    "oecd": parse_sdmx,
    "ecb": parse_sdmx,
}


def workbook_number(value):
    if value is None or str(value).strip() in {"", "[x]", "[c]", "[z]", "--", "NA"}:
        return None
    if isinstance(value, bool):
        raise TypeError("Boolean source value")
    return float(value)


def parse_desnz(entry, body):
    selector = entry["source"]["selector"]
    column = re.search(r"column ([A-Z]+)$", selector).group(1)
    sheet = "Month (GWh)" if "4.2" in selector else "Month"
    rows = excel_rows(body, sheet)
    title = str(rows[0][0])
    expected = {
        "3.13": ("thousand tonnes", {"I": "White diesel", "M": "Bitumen"}),
        "3.10": ("thousand tonnes", {"C": "Crude oil"}),
        "5.3": ("million tonnes of oil equivalent", {"E": "Gas"}),
        "5.4": ("TWh", {"V": "Total electricity"}),
        "4.2": ("GWh", {"B": "Gross production"}),
    }
    table = selector.split()[1]
    unit, headers = expected[table]
    index = ord(column) - ord("A")
    if unit.casefold() not in title.casefold() or not any(
        headers[column] in str(r[index]) for r in rows[:9]
    ):
        raise ValueError("DESNZ source unit/header changed")
    d = definition(entry)
    points = []
    for row in rows:
        label = str(row[0])
        match = re.fullmatch(r"([A-Za-z]+) ([0-9]{4})(?:\s*\[([pr])\])?", label)
        if not match:
            continue
        period = datetime.strptime(f"{match[1]} {match[2]}", "%B %Y").strftime("%Y-%m")
        flags = (f"source_status={match[3]}",) if match[3] else ()
        points.append(Observation(period, label, workbook_number(row[index]), flags))
    return (
        d,
        tuple(points),
        {
            "title": title,
            "sheet": sheet,
            "column": column,
            "unit_label": unit,
            "source": "DESNZ Energy Trends",
        },
    )


def parse_ons_construction(entry, body):
    code = entry["source"]["selector"].split(" | ")[0]
    if not re.fullmatch(r"MV[A-Z0-9]{2}", code):
        raise ValueError("New-order selector still unresolved")
    rows = excel_rows(body, "Table 1a")
    if (
        "volume, seasonally adjusted, index numbers" not in str(rows[0][0])
        or rows[3][0] != "2024=100"
    ):
        raise ValueError(
            "Construction benchmark/adjustment changed; review a new definition"
        )
    if rows[5].count(code) != 1:
        raise ValueError("ONS construction CDID missing or duplicated")
    index = rows[5].index(code)
    d = definition(
        entry, units="Volume index 2024=100", adjustment="Seasonally adjusted"
    )
    points = []
    for row in rows[6:]:
        label = str(row[0])
        if not re.fullmatch(r"[A-Z][a-z]{2} [0-9]{4}", label):
            continue  # Annual and quarterly summaries are NOT monthly observations.
        period = datetime.strptime(label, "%b %Y").strftime("%Y-%m")
        points.append(Observation(period, label, workbook_number(row[index])))
    return (
        d,
        tuple(points),
        {
            "title": rows[0][0],
            "column_header": rows[4][index],
            "cdid": code,
            "unit_label": "2024=100",
            "source": rows[2][0],
        },
    )


def parse_uk_materials(entry, body):
    sheet, column = re.search(
        r"sheet-column ([0-9]+[a-z]?)/([A-Z])$", entry["source"]["selector"]
    ).groups()
    rows = excel_rows(body, sheet)
    attribution = str(rows[3][0])
    if attribution.strip() != "Source: DBT":
        raise ValueError(
            "Underlying BCIS/MPA rights need permission; not cleared by OGL alone"
        )
    headers = rows[4]
    index = ord(column) - ord("A")
    header = str(headers[index])
    if (
        sheet == "4a"
        and column == "C"
        or sheet == "9a"
        and column == "C"
        or sheet == "11a"
        and column == "C"
    ):
        if "Seasonally adjusted" not in header:
            raise ValueError("Expected seasonally adjusted materials selection")
        adjustment = "Seasonally adjusted"
    else:
        adjustment = "Not seasonally adjusted"
    d = definition(entry, adjustment=adjustment)
    points, year = [], None
    for row in rows[5:]:
        if (
            isinstance(row[0], (float, int))
            and 1900 <= row[0] <= 2100
            or str(row[0]).isdigit()
            and len(str(row[0])) == 4
        ):
            year = int(row[0])
        elif row[0] not in (None, ""):
            year = None
        if year is None or not row[1]:
            continue
        label = str(row[1])
        if d.frequency == "monthly":
            if label not in (
                "January",
                "February",
                "March",
                "April",
                "May",
                "June",
                "July",
                "August",
                "September",
                "October",
                "November",
                "December",
            ):
                continue
            period = datetime.strptime(f"{label} {year}", "%B %Y").strftime("%Y-%m")
        elif d.frequency == "quarterly" and re.fullmatch(r"Q[1-4]", label):
            period = f"{year}-{label}"
        else:
            continue
        points.append(
            Observation(period, f"{year} {label}", workbook_number(row[index]))
        )
    return (
        d,
        tuple(points),
        {
            "title": rows[0][0],
            "source": attribution,
            "column_header": header,
            "sheet": sheet,
            "column": column,
            "definition_note": "Planning adjustment corrected to the actual selected column; no existing public ID changed",
        },
    )


def parse_usgs(entry, body):
    selector = entry["source"]["selector"]
    points = []
    if "T1AP1" in selector or "T1BP1" in selector:
        prefix = "T1A" if "T1AP1" in selector else "T1B"
        for suffix in ("P1", "P2", "P3"):
            rows = excel_rows(body, prefix + suffix)
            if "Data are in metric tons" not in str(rows[1][0]):
                raise ValueError("USGS cement units changed")
            year = re.match(r"([0-9]{4})", str(rows[2][1])).group(1)
            totals = [r for r in rows if str(r[0]).startswith("Grand total")]
            if len(totals) != 1:
                raise ValueError("USGS grand total is ambiguous")
            for i, month in enumerate(rows[3]):
                if month not in (
                    "January",
                    "February",
                    "March",
                    "April",
                    "May",
                    "June",
                    "July",
                    "August",
                    "September",
                    "October",
                    "November",
                    "December",
                ):
                    continue
                period = datetime.strptime(f"{month} {year}", "%B %Y").strftime("%Y-%m")
                points.append(
                    Observation(
                        period,
                        f"{year} {month}",
                        workbook_number(totals[0][i]),
                        ("source_total_contains_estimates",),
                    )
                )
        metadata = {
            "title": rows[0][0],
            "unit_label": "Metric tonnes",
            "scope": "Grand total by district of origin, includes imported clinker; not all cement imports",
            "history_limit": "18 months in this official issue; older archive needs reconciliation",
        }
    elif any(f" / {s} / " in selector for s in ("T1", "T3", "T5")):
        sheet = selector.split(" / ")[1]
        rows = excel_rows(body, sheet)
        if "thousand metric tons" not in str(rows[1][0]):
            raise ValueError("USGS aggregates units changed")
        totals = [r for r in rows if re.fullmatch(r"Total[0-9, ]*", str(r[0]))]
        if len(totals) != 1:
            raise ValueError("USGS total is ambiguous")
        year = str(rows[2][1])[:4]
        previous = str(rows[2][3])[:4]
        if not year.isdigit() or not previous.isdigit():
            raise ValueError("USGS year headers changed")
        for index, period in [(1, f"{year}-Q1")] + [
            (i + 3, f"{previous}-Q{i + 1}") for i in range(4)
        ]:
            points.append(
                Observation(
                    period,
                    period,
                    workbook_number(totals[0][index]),
                    ("estimated_source_total",),
                )
            )
        metadata = {
            "title": rows[0][0],
            "unit_label": "Thousand metric tonnes",
            "history_limit": "Five quarters in official Q1 issue; older archive not manufactured",
        }
    else:
        raise ValueError("Unresolved USGS source row/unit; no image extraction")
    return definition(entry), tuple(points), metadata


def parse_eia_xls(entry, body):
    import xlrd

    book = xlrd.open_workbook(file_contents=body, on_demand=True)
    try:
        sheet = book.sheet_by_index(1)
        key = entry["source"]["selector"].split(".")[-2]
        if sheet.cell_value(1, 1) != key:
            raise ValueError("EIA sourcekey mismatch")
        title = sheet.cell_value(2, 1)
        expected_units = {
            "WCESTUS1": "Thousand Barrels",
            "WCRFPUS2": "Thousand Barrels per Day",
            "WGTSTUS1": "Thousand Barrels",
            "WDISTUS1": "Thousand Barrels",
            "MAPUPUS2": "Thousand Barrels per Day",
            "NW2_EPG0_SWO_R48_BCF": "Billion Cubic Feet",
            "RWTC": "Dollars per Barrel",
        }
        units = expected_units[key]
        if f"({units})" not in title:
            raise ValueError("EIA native units changed")
        d = definition(entry, units=units, adjustment="Not seasonally adjusted")
        points = []
        for i in range(3, sheet.nrows):
            cell, value = sheet.cell(i, 0), sheet.cell_value(i, 1)
            if cell.ctype != xlrd.XL_CELL_DATE:
                raise ValueError("EIA date column changed")
            day = xlrd.xldate_as_datetime(cell.value, book.datemode)
            period = day.strftime("%Y-%m" if d.frequency == "monthly" else "%Y-%m-%d")
            points.append(
                Observation(period, day.strftime("%Y-%m-%d"), workbook_number(value))
            )
        return d, tuple(points), {"title": title, "sourcekey": key, "unit_label": units}
    finally:
        book.release_resources()


PARSERS.update(
    {
        "desnz": parse_desnz,
        "uk_building_materials": parse_uk_materials,
        "usgs": parse_usgs,
        "eia": parse_eia_xls,
    }
)


def parse_bls(entry, body):
    data = json.loads(body)
    if data["status"] != "REQUEST_SUCCEEDED":
        raise ValueError("BLS request failed")
    matches = [
        r
        for r in data["Results"]["series"]
        if r["seriesID"] == entry["source"]["selector"]
    ]
    if len(matches) != 1:
        raise ValueError("BLS series identity mismatch")
    d = definition(entry)
    points = []
    for row in matches[0]["data"]:
        period = row["period"]
        if period == "M13":  # Published annual average, not a thirteenth month.
            continue
        if not re.fullmatch(r"M(?:0[1-9]|1[0-2])", period):
            raise ValueError("Unexpected BLS native period")
        label = f"{row['year']}-{period[1:]}"
        flags = tuple(
            str(f["code"]) + "=" + str(f.get("text", ""))
            for f in row.get("footnotes", [])
            if f.get("code")
        )
        points.append(
            Observation(
                label, f"{row['year']} {period}", workbook_number(row["value"]), flags
            )
        )
    return (
        d,
        tuple(points),
        {
            "source": "BLS",
        "history_limit": "All observations actually returned within the requested source windows; no missing earlier years fabricated",
        "source_windows": data.get("source_windows", [{"start":2017,"end":2026}]),
            "unit_label": d.units,
        },
    )


PARSERS["bls"] = parse_bls


def parse_census_construction(entry, body):
    sheet, expected = entry["source"]["selector"].split("/")
    rows = excel_rows(body, sheet)
    if "Seasonally Adjusted Annual Rate" not in str(
        rows[0][0]
    ) or "Millions of dollars" not in str(rows[1][0]):
        raise ValueError("Census construction units/annualization changed")

    def cleaned(value):
        return re.sub(r"\s+", " ", str(value).replace("_x000D_", " ")).strip()

    headers = [cleaned(x) for x in rows[3]]
    if headers.count(expected) != 1:
        raise ValueError("Census construction header changed")
    column = headers.index(expected)
    d = definition(
        entry,
        units="Millions of US dollars, annual rate",
        adjustment="Seasonally adjusted annual rate",
    )
    points = []
    for row in rows[4:]:
        match = re.fullmatch(r"([A-Z][a-z]{2})-([0-9]{2})([pr]?)", str(row[0]))
        if not match:
            continue
        year = int(match[2]) + (1900 if int(match[2]) >= 70 else 2000)
        period = datetime.strptime(f"{match[1]} {year}", "%b %Y").strftime("%Y-%m")
        flags = (f"source_status={match[3]}",) if match[3] else ()
        points.append(
            Observation(period, str(row[0]), workbook_number(row[column]), flags)
        )
    return (
        d,
        tuple(points),
        {
            "title": rows[0][0],
            "column_header": expected,
            "unit_label": "Millions of US dollars, seasonally adjusted annual rate",
            "scope": "Construction spending flow, not physical materials consumed",
        },
    )


PARSERS["census"] = parse_census_construction


def parse_bea(entry, body):
    sheet, code = entry["source"]["selector"].split("/")
    rows = excel_rows(body, sheet)
    matches = [r for r in rows if len(r) > 2 and r[2] == code]
    if len(matches) != 1 or "Bureau of Economic Analysis" != rows[3][0]:
        raise ValueError("BEA source series identity mismatch")
    expected = entry["expected_row_label"]
    if expected not in str(matches[0][1]):
        raise ValueError("BEA row definition changed")
    # Unit checks use both table and row: saving rate is not a dollar amount.
    unit_context = str(rows[1][0]) + " " + str(matches[0][1])
    if entry["expected_unit_text"] not in unit_context:
        raise ValueError("BEA benchmark or units changed")
    d = definition(entry)
    points = []
    for i, label in enumerate(rows[7]):
        if i < 3:
            continue
        label = str(label)
        if d.frequency == "quarterly" and re.fullmatch(r"[0-9]{4}Q[1-4]", label):
            period = label[:4] + "-" + label[4:]
        elif d.frequency == "monthly" and re.fullmatch(
            r"[0-9]{4}M(?:0[1-9]|1[0-2])", label
        ):
            period = label[:4] + "-" + label[5:]
        else:
            raise ValueError("Unexpected BEA native period")
        value = matches[0][i]
        points.append(
            Observation(
                period, label, None if value == "....." else workbook_number(value)
            )
        )
    return (
        d,
        tuple(points),
        {
            "title": rows[0][0],
            "table_units": rows[1][0],
            "selected_row": matches[0][1],
            "publication_label": rows[4][0],
            "unit_label": d.units,
            "source": "Bureau of Economic Analysis",
            "revision_note": "Current revised history; annual/comprehensive updates may revise history. Chained components need not add.",
        },
    )


PARSERS["bea"] = parse_bea
