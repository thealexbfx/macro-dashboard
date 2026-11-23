"""Capture original INSEE national GDP, CPI and unemployment histories."""
import argparse
import json
import math
import re
from datetime import date
from hashlib import sha256
from pathlib import Path
from xml.etree import ElementTree

SOURCE = "https://www.bdm.insee.fr/series/sdmx/data/SERIES_BDM/"
MESSAGE = "{http://www.sdmx.org/resources/sdmxml/schemas/v2_1/message}"
MAX_BYTES = 256 * 1024
SERIES = {
    "G7-FR-01": (
        "011794860", "T", "EUROS", "FE", "Millions of chained 2020 euros", "1949-Q1",
        "Total gross domestic product - Volumes chained at previous year prices - SA-WDA series",
    ),
    "G7-FR-07": (
        "011814630", "M", "SO", "FE", "2025=100", "1996-01",
        "Consumer Price Index - Base 2025 - All households - France - COICOP classification: 00 - All items",
    ),
    "G7-FR-11": (
        "001688527", "T", "POURCENT", "FR-D976", "Percent", "1975-Q1",
        "ILO unemployment rate - Total - France excluding Mayotte - SA data",
    ),
}


def capture(mapping, raw):
    selector, freq, unit_code, area, unit, first, title = SERIES[mapping]
    if len(raw) > MAX_BYTES:
        raise ValueError("INSEE response exceeds capture budget")
    xml = raw.decode("utf-8-sig")
    if "<!DOCTYPE" in xml or "<!ENTITY" in xml:
        raise ValueError("INSEE response includes unsupported XML declarations")
    root = ElementTree.fromstring(xml)
    data = root.findall(f"./{MESSAGE}DataSet")
    if root.tag != f"{MESSAGE}StructureSpecificData" or len(data) != 1:
        raise ValueError("Expected one INSEE SDMX structure-specific dataset")
    series = list(data[0])
    if len(series) != 1 or series[0].tag != "Series":
        raise ValueError("Expected one INSEE series")
    series = series[0]
    expected = {
        "IDBANK": selector, "FREQ": freq, "UNIT_MEASURE": unit_code,
        "UNIT_MULT": "6" if mapping == "G7-FR-01" else "0", "REF_AREA": area, "TITLE_EN": title,
    }
    if any(series.get(key) != value for key, value in expected.items()):
        raise ValueError("INSEE series identity, unit, scope or title differs")
    publisher_update = date.fromisoformat(series.attrib["LAST_UPDATE"]).isoformat()
    pattern = r"[0-9]{4}-(0[1-9]|1[0-2])" if freq == "M" else r"[0-9]{4}-Q([1-4])"
    points = {}
    for obs in series:
        period = obs.get("TIME_PERIOD", "")
        match = re.fullmatch(pattern, period)
        if obs.tag != "Obs" or not match or period in points:
            raise ValueError("Invalid or duplicate INSEE reference period")
        raw_value, status = obs.get("OBS_VALUE"), obs.get("OBS_STATUS")
        value = float(raw_value) if raw_value is not None else None
        if value is None and status not in {"L", "M"}:
            raise ValueError("INSEE value missing without publisher flag")
        if value is not None and (
            not math.isfinite(value) or (not 0 <= value <= 100 if unit == "Percent" else value <= 0)
        ):
            raise ValueError("INSEE observation outside its valid domain")
        flags = " ".join(f"{field}={obs.get(field)}" for field in (
            "OBS_STATUS", "OBS_QUAL", "OBS_TYPE", "OBS_REV"
        ) if obs.get(field))
        points[period] = {"period": period, "value": value, "publisher_flag": flags}
    periods = sorted(points)
    if not periods or periods[0] != first:
        raise ValueError("INSEE history does not start at the reviewed first period")
    periods_per_year = 12 if freq == "M" else 4
    ordinals = [int(key[:4]) * periods_per_year + int(key[5:].lstrip("Q")) for key in periods]
    if ordinals != list(range(ordinals[0], ordinals[-1] + 1)):
        raise ValueError("Missing INSEE reference period")
    observations = [points[key] for key in periods]
    return {
        "mapping": mapping,
        "publisher_series": selector,
        "source_url": SOURCE + selector,
        "source_sha256": sha256(raw).hexdigest(),
        "publisher_last_update": publisher_update,
        "unit": unit,
        "first": periods[0],
        "last": periods[-1],
        "valid_observations": sum(row["value"] is not None for row in observations),
        "publisher_nulls": sum(row["value"] is None for row in observations),
        "rights_status": "PENDING",
        "production_approval": "NOT_APPROVED",
    }, observations


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mapping", choices=SERIES)
    parser.add_argument("publisher_file", type=Path)
    parser.add_argument("receipt", type=Path)
    args = parser.parse_args()
    with args.publisher_file.open("rb") as source:
        summary, observations = capture(args.mapping, source.read(MAX_BYTES + 1))
    with args.receipt.open("x", encoding="utf-8") as output:
        json.dump(summary | {"observations": observations}, output, indent=2, allow_nan=False)
        output.write("\n")
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
