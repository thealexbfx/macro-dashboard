"""Capture the original unadjusted ILO unemployment rate from Destatis."""
import argparse
import json
import re
from pathlib import Path

from scripts.capture_destatis_cpi_history import read_flat_archive

SOURCE = "https://genesis.destatis.de/datenbank/online/statistic/13231/table/13231-0001"
IDENTITY = {
    "statistics_code": "13231", "time_code": "JAHR",
    "1_variable_code": "MONAT", "2_variable_code": "DINSG",
    "2_variable_attribute_code": "DG", "3_variable_code": "WERT06",
    "3_variable_attribute_code": "WERTORG", "3_variable_attribute_label": "Originalwerte",
    "value_variable_code": "ERW089", "value_variable_label": "Erwerbslosenquote",
    "value_unit": "Prozent",
}


def capture(path):
    reader, checksum = read_flat_archive(path, "13231-0001", 2 * 1024**2)
    if not (set(IDENTITY) | {"time", "1_variable_attribute_code", "value", "value_q"}).issubset(reader.fieldnames or ()):
        raise ValueError("Missing Destatis labor export columns")
    points = {}
    for row in reader:
        if row["value_variable_code"] != "ERW089" or row["3_variable_attribute_code"] != "WERTORG":
            continue
        if any(row[key] != value for key, value in IDENTITY.items()):
            raise ValueError("Destatis unemployment series definition changed")
        year, month = row["time"], row["1_variable_attribute_code"]
        if not re.fullmatch(r"[0-9]{4}", year) or not re.fullmatch(r"MONAT(0[1-9]|1[0-2])", month):
            raise ValueError("Invalid Destatis labor month")
        period = f"{year}-{month[-2:]}"
        raw_value = row["value"]
        if period in points:
            raise ValueError(f"Duplicate Destatis labor month: {period}")
        if (raw_value == "-" and period < "2007-01") or raw_value == "...":
            value, flag = None, raw_value
        else:
            if not re.fullmatch(r"[0-9]{1,3},[0-9]+", raw_value):
                raise ValueError(f"Unexpected Destatis unemployment value in {period}")
            value, flag = float(raw_value.replace(",", ".")), row["value_q"] or None
            if period < "2007-01" or not 0 <= value <= 100:
                raise ValueError(f"Destatis unemployment coverage or domain changed in {period}")
        points[period] = {"period": period, "value": value, "publisher_flag": flag}
    periods = sorted(points)
    months = [int(p[:4]) * 12 + int(p[-2:]) for p in periods]
    if not periods or periods[0] != "1991-01" or months != list(range(months[0], months[-1] + 1)):
        raise ValueError("Destatis labor history must start in January 1991 with no skipped months")
    valid = [p for p in periods if points[p]["value"] is not None]
    if (not valid or valid[0] != "2007-01" or valid[-1] < "2026-09"
            or valid != [p for p in periods if valid[0] <= p <= valid[-1]]):
        raise ValueError("Incomplete Destatis unemployment history")
    published = [p for p in periods if p <= valid[-1]]
    return {
        "mapping": "G7-DE-11", "publisher_series": "13231-0001/ERW089/WERTORG",
        "source_url": SOURCE, "source_sha256": checksum, "unit": "Percent",
        "first": valid[0], "last": valid[-1], "valid_observations": len(valid),
        "publisher_nulls": len(published) - len(valid), "rights_status": "PENDING",
        "production_approval": "NOT_APPROVED",
        "observations": [points[p] for p in published],
        "unpublished_periods": [points[p] for p in periods[len(published):]],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("receipt", type=Path)
    args = parser.parse_args()
    receipt = capture(args.archive)
    with args.receipt.open("x", encoding="utf-8") as stream:
        json.dump(receipt, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps({key: value for key, value in receipt.items() if key != "observations"}))


if __name__ == "__main__":
    main()
