"""Validate official GENESIS flat CSV exports for the private German CPI history."""
import argparse
import csv
import io
import json
import re
from hashlib import sha256
from pathlib import Path
from zipfile import ZipFile

SOURCE = "https://genesis.destatis.de/datenbank/online/table/61111-0002"
HISTORY = "https://genesis.destatis.de/datenbank/online/url/d843791e"
LIMIT = 1024 * 1024
IDENTITY = {
    "statistics_code": "61111", "time_code": "JAHR",
    "1_variable_code": "MONAT", "2_variable_code": "DINSG",
    "2_variable_attribute_code": "DG", "value_variable_code": "PREIS1",
    "value_variable_label": "Verbraucherpreisindex",
}


def read_export(path):
    with path.open("rb") as stream:
        raw = stream.read(LIMIT + 1)
    if len(raw) > LIMIT:
        raise ValueError("Destatis archive exceeds size limit")
    with ZipFile(io.BytesIO(raw)) as archive:
        entries = archive.infolist()
        if (len(entries) != 1 or entries[0].filename != "61111-0002_de_flat.csv"
                or entries[0].file_size > LIMIT):
            raise ValueError("Unexpected Destatis archive")
        content = archive.read(entries[0]).decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(content), delimiter=";")
    required = set(IDENTITY) | {"value_unit", "time", "1_variable_attribute_code", "value", "value_q"}
    if not required.issubset(reader.fieldnames or ()):
        raise ValueError("Missing Destatis export columns")
    points = {}
    for row in reader:
        if row["value_unit"] == "%":
            continue
        if row["value_unit"] != "2020=100" or any(row[key] != value for key, value in IDENTITY.items()):
            raise ValueError("Destatis CPI definition changed")
        year, month = row["time"], row["1_variable_attribute_code"]
        if not re.fullmatch(r"\d{4}", year) or not re.fullmatch(r"MONAT(0[1-9]|1[0-2])", month):
            raise ValueError("Invalid Destatis month")
        period = f"{year}-{month[-2:]}"
        if period in points:
            raise ValueError(f"Duplicate Destatis month: {period}")
        raw_value = row["value"]
        if raw_value == "...":
            value, flag = None, "..."
        else:
            if not re.fullmatch(r"[0-9]{1,4},[0-9]+", raw_value):
                raise ValueError(f"Unexpected Destatis CPI value in {period}")
            value, flag = float(raw_value.replace(",", ".")), row["value_q"] or None
            if value <= 0:
                raise ValueError(f"Nonpositive Destatis CPI in {period}")
        points[period] = {"period": period, "value": value, "publisher_flag": flag}
    return points, sha256(raw).hexdigest()


def capture(history, recent):
    older, old_hash = read_export(history)
    newer, new_hash = read_export(recent)
    overlap = older.keys() & newer.keys()
    if not overlap or any(older[key] != newer[key] for key in overlap):
        raise ValueError("Destatis exports require matching overlapping periods")
    points = older | newer
    periods = sorted(points)
    months = [int(p[:4]) * 12 + int(p[-2:]) for p in periods]
    if not periods or periods[0] != "1991-01" or months != list(range(months[0], months[-1] + 1)):
        raise ValueError("Destatis history must be contiguous from January 1991")
    valid = [p for p in periods if points[p]["value"] is not None]
    if not valid or valid != periods[:len(valid)]:
        raise ValueError("Unexpected missing CPI inside published history")
    return {
        "mapping": "G7-DE-07", "publisher_series": "61111-0002/PREIS1/DG",
        "source_url": SOURCE, "metadata_source_url": HISTORY,
        "source_archives": [
            {"selection_url": HISTORY, "sha256": old_hash},
            {"selection_url": SOURCE, "sha256": new_hash},
        ],
        "matched_overlap": len(overlap), "unit": "2020=100",
        "first": valid[0], "last": valid[-1], "valid_observations": len(valid),
        "publisher_nulls": len(periods) - len(valid), "rights_status": "PENDING",
        "production_approval": "NOT_APPROVED", "observations": [points[p] for p in valid],
        "unpublished_periods": [points[p] for p in periods[len(valid):]],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("history", type=Path)
    parser.add_argument("recent", type=Path)
    parser.add_argument("receipt", type=Path)
    args = parser.parse_args()
    result = capture(args.history, args.recent)
    with args.receipt.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps({key: value for key, value in result.items() if key != "observations"}))


if __name__ == "__main__":
    main()
