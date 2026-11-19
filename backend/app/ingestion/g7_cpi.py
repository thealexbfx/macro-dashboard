"""Original publisher CPI contracts for the explicit private G7 pilot."""

import csv
import io
import math
import re
import zipfile
from datetime import datetime
from html import unescape
from types import SimpleNamespace
from zoneinfo import ZoneInfo

from backend.app.ingestion.contracts import ProviderError
from backend.app.ingestion.native import Definition, Observation, SourceCalendar

CA = "https://www150.statcan.gc.ca"
JP = "https://www.e-stat.go.jp/en/stat-search"
JP_LIST = (
    JP + "/files?cycle=0&layout=datalist&page=1&tclass1=000001243880"
    "&tclass2=000001243881&tclass3=000001243883&tclass4=000001243886"
    "&toukei=00200573&toukei_kind=9&tstat=000001243876"
)
JP_TITLE = "Indices of Items (January 1970 - the Recent Month)"
CA_LICENCE = "https://www.statcan.gc.ca/en/terms-conditions/open-licence"
JP_LICENCE = "https://www.stat.go.jp/english/info/riyou.html"

CANADA = (
    ("ca_cpi_all_items_nsa", "18100004", "v41690973", "2.2", "All-items",
     "2002=100", "Not seasonally adjusted", "1914-01"),
    ("ca_cpi_trim_yoy", "18100256", "v108785715", "1.3",
     "Measure of core inflation based on a trimmed mean approach, CPI-trim (year-over-year percent change)",
     "Percent", "YoY from seasonally adjusted components", "1949-01"),
    ("ca_cpi_median_yoy", "18100256", "v108785714", "1.2",
     "Measure of core inflation based on a weighted median approach, CPI-median (year-over-year percent change)",
     "Percent", "YoY from seasonally adjusted components", "1949-01"),
)
JAPAN = (
    ("jp_cpi_all_items_2025_nsa", "0001", "All items"),
    ("jp_cpi_ex_fresh_food_2025_nsa", "0161", "All items, less fresh food"),
    ("jp_cpi_ex_fresh_food_energy_2025_nsa", "0178", "All items, less fresh food and energy"),
)


def configuration():
    rules, publications, entries = {}, {}, {}
    for key, pid, vector, coordinate, label, units, adjustment, first in CANADA:
        url = f"{CA}/n1/tbl/csv/{pid}-eng.zip"
        landing = f"{CA}/t1/tbl1/en/tv.action?pid={pid}01"
        entries[key] = dict(pid=pid, vector=vector, coordinate=coordinate, label=label,
                            first=first, landing=landing, licence=CA_LICENCE)
        publications[key] = SimpleNamespace(
            source_url=url,
            definition=Definition(key, "statcan_cpi", f"{pid}/{vector}/{coordinate}",
                                  units, "monthly", adjustment,
                                  SourceCalendar("statcan_cpi", "America/Toronto")),
        )
    for key, member, label in JAPAN:
        entries[key] = dict(member=member, label=label, first="1970-01", licence=JP_LICENCE)
        publications[key] = SimpleNamespace(
            source_url=JP_LIST,
            definition=Definition(key, "estat_cpi", f"0004052037/2025/Japan/{member}",
                                  "2025=100", "monthly", "Not seasonally adjusted",
                                  SourceCalendar("estat_cpi", "Asia/Tokyo")),
        )
    for key, pub in publications.items():
        entries[key]["source"] = dict(provider=pub.definition.provider, endpoint=pub.source_url)
        rules[key] = dict(mode="stage", automation_ready=True, check_seconds=86400)
    return rules, publications, entries


def resolve(entry, fetch):
    url = entry["source"]["endpoint"]
    if "pid" in entry:
        raw, _ = fetch(entry["landing"])
        text = unescape(re.sub(r"<[^>]*>", " ", raw.decode("utf-8")))
        match = re.search(r"Release date:\s*(\d{4}-\d{2}-\d{2})", text)
        if not match:
            raise ProviderError("statcan_release_metadata")
        return url, {"discovery_url": entry["landing"], "release_date": match[1]}
    raw, _ = fetch(url)
    markup = unescape(raw.decode("utf-8"))
    matches = {
        m.group(1)
        for m in re.finditer(
            r'href=["\x27][^"\x27]*stat_infid=(\d+)[^"\x27]*["\x27][^>]*>\s*'
            + re.escape(JP_TITLE), markup
        )
    }
    if len(matches) != 1:
        raise ProviderError("estat_missing_or_ambiguous_history")
    file_id = matches.pop()
    landing = f"{JP}/files?stat_infid={file_id}"
    raw, _ = fetch(landing)
    text = unescape(re.sub(r"<[^>]*>", " ", raw.decode("utf-8")))
    match = re.search(r"Published date and time\s*(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2})", text)
    survey = re.search(r"Survey date\s*(\d{4})\s+([A-Za-z]{3})", text)
    if not match or not survey or "2025-Base Consumer Price Index" not in text:
        raise ProviderError("estat_release_metadata")
    return f"{JP}/file-download?fileKind=1&statInfId={file_id}", {
        "discovery_url": landing, "release_date": match[1],
        "release_time": match[2],
        "end": f"{survey[1]}-{['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'].index(survey[2])+1:02d}",
    }


def statcan_rows(definition, entry, body):
    pid = entry["pid"]
    with zipfile.ZipFile(io.BytesIO(body)) as archive:
        data, meta = [archive.getinfo(pid + suffix) for suffix in (".csv", "_MetaData.csv")]
        if data.file_size > 220 * 1024**2 or meta.file_size > 1024**2:
            raise ProviderError("statcan_uncompressed_size")
        metadata = list(csv.reader(io.StringIO(archive.read(meta).decode("utf-8-sig"))))
        header, cube = metadata[:2]
        info = dict(zip(header, cube))
        if info["Product Id"] != pid or info["Frequency"] != "Monthly":
            raise ProviderError("statcan_cube_drift")
        dimension = "Products and product groups" if pid == "18100004" else "Alternative measures"
        units_id = "17" if pid == "18100004" else "239"
        points = []
        with archive.open(data) as stream:
            for row in csv.DictReader(io.TextIOWrapper(stream, encoding="utf-8-sig", newline="")):
                selected = row["GEO"] == "Canada" and row[dimension] == entry["label"]
                if not selected and row["VECTOR"] != entry["vector"]:
                    continue
                if (
                    not selected or row["DGUID"] != "2016A000011124"
                    or row["VECTOR"] != entry["vector"] or row["COORDINATE"] != entry["coordinate"]
                    or row["UOM"] != definition.units or row["UOM_ID"] != units_id
                    or row["SCALAR_ID"] != "0" or row["TERMINATED"]
                ):
                    raise ProviderError("statcan_series_contract_drift")
                flags = tuple(f"{k.lower()}={row[k]}" for k in ("STATUS", "SYMBOL") if row[k])
                value = float(row["VALUE"]) if row["VALUE"] else None
                points.append(Observation(row["REF_DATE"], row["REF_DATE"], value, flags))
        return points, info["End Reference Period"][:7]


def japan_rows(entry, body):
    rows = list(csv.reader(io.StringIO(body.decode("cp932"), newline="")))
    labels = rows[1]
    codes = rows[2]
    if labels[0] != "Group/Item" or "(Group/Item code)" not in codes[0]:
        raise ProviderError("estat_header_drift")
    selected = [i for i, code in enumerate(codes) if code == entry["member"]]
    if len(selected) != 1 or labels[selected[0]] != entry["label"]:
        raise ProviderError("estat_member_drift")
    index = selected[0]
    points = []
    for row in rows[6:]:
        if len(row) != len(codes) or not re.fullmatch(r"\d{6}", row[0]):
            raise ProviderError("estat_month_row_drift")
        month = row[0][:4] + "-" + row[0][4:]
        raw = row[index].strip()
        points.append(Observation(month, row[0], float(raw) if raw else None,
                                  () if raw else ("source_missing",)))
    return points


def parse_history(definition, entry, body, release):
    try:
        if "pid" in entry:
            points, end = statcan_rows(definition, entry, body)
        else:
            points, end = japan_rows(entry, body), release["end"]
        points.sort(key=lambda point: point.period)
        start_year, start_month = map(int, entry["first"].split("-"))
        end_year, end_month = map(int, end.split("-"))
        expected = [f"{i // 12:04d}-{i % 12 + 1:02d}"
                    for i in range(start_year * 12 + start_month - 1, end_year * 12 + end_month)]
        if (
            not points or [p.period for p in points] != expected or points[-1].value is None
            or any(p.value is not None and not math.isfinite(p.value) for p in points)
        ):
            raise ProviderError("cpi_history_coverage_mismatch")
        published = datetime.fromisoformat(
            f'{release["release_date"]}T{release.get("release_time", "08:30")}'
        ).replace(tzinfo=ZoneInfo(definition.calendar.timezone))
        if published.year * 12 + published.month != end_year * 12 + end_month + 1:
            raise ProviderError("cpi_release_reference_mismatch")
        # Vintage release dates describe this artifact. Individual historical
        # observations have no original publication timestamp in these files.
        from dataclasses import replace

        points[-1] = replace(points[-1], release_at=published)
        return definition, points, release | {"licence_url": entry["licence"]}
    except (KeyError, IndexError, ValueError, UnicodeError, zipfile.BadZipFile, csv.Error) as exc:
        raise ProviderError("invalid_cpi_publisher_payload") from exc
