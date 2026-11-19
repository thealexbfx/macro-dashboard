"""Capture Japan's daily 10-year constant-maturity government yield."""

import argparse
import csv
import io
import json
import math
from datetime import date, datetime
from hashlib import sha256
from pathlib import Path

ROOT = "https://www.mof.go.jp/english/policy/jgbs/reference/interest_rate/"
FILES = {"history": "historical/jgbcme_all.csv", "current": "jgbcme.csv"}
COLUMNS = ["Date", *(f"{n}Y" for n in range(1, 11)), "15Y", "20Y", "25Y", "30Y", "40Y"]


def read_archive(path, *, current=False):
    budget = 4_000_000
    with path.open("rb") as source:
        raw = source.read(budget + 1)
    if len(raw) > budget:
        raise ValueError("MOF CSV exceeds capture budget")
    rows = csv.reader(io.StringIO(raw.decode("cp932" if current else "utf-8-sig")))
    label, columns = next(rows), next(rows)
    month = None
    if current and label[0].startswith("Interest Rate (") and label[0].endswith(")"):
        month = datetime.strptime(label[0][15:-1], "%B %Y").strftime("%Y-%m")
    if (month is None if current else label[0] != "Interest Rate") or label[-1] != "(Unit : %)" or columns != COLUMNS:
        raise ValueError("MOF maturity or unit header changed")
    observations = {}
    for row in rows:
        if current and (not any(cell.strip() for cell in row) or (
            row[0].strip() == "※If you cannot download the latest csv data, please clear the browser's cache and download again."
            and not any(row[1:])
        )):
            continue
        if len(row) != len(columns):
            raise ValueError("Unexpected MOF row width")
        day = date(*map(int, row[0].split("/"))).isoformat()
        if current and not day.startswith(month + "-"):
            raise ValueError("MOF current row outside declared month")
        value = None if row[10] == "-" else float(row[10])
        if day in observations or (value is not None and not math.isfinite(value)):
            raise ValueError("Duplicate date or nonfinite MOF observation")
        observations[day] = value
    if not any(value is not None for value in observations.values()):
        raise ValueError("MOF 10-year column has no usable observations")
    return observations, sha256(raw).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("history", type=Path)
    parser.add_argument("receipt", type=Path)
    parser.add_argument("--current", type=Path)
    args = parser.parse_args()
    points, digest = read_archive(args.history)
    evidence = {"history": {"url": ROOT + FILES["history"], "sha256": digest}}
    if args.current:
        current, digest = read_archive(args.current, current=True)
        overlap = set(points) & set(current)
        last_archive = date.fromisoformat(max(points))
        next_month = date(last_archive.year + (last_archive.month == 12), last_archive.month % 12 + 1, 1)
        if (not overlap and min(current)[:7] != next_month.isoformat()[:7]) or any(points[day] != current[day] for day in overlap):
            raise ValueError("Current MOF file does not reconcile with historical archive")
        points.update(current)
        evidence["current"] = {
            "url": ROOT + FILES["current"], "sha256": digest, "matched_dates": len(overlap),
        }
    dates = sorted(points)
    valid = [day for day in dates if points[day] is not None]
    result = {
        "mapping": "G7-JP-23", "series": "10Y", "frequency": "Daily",
        "unit": "Percent", "definition": "Semiannually compounded constant-maturity JGB yield",
        "archive_start": dates[0], "first_valid": valid[0], "last_valid": valid[-1],
        "valid_observations": len(valid), "publisher_nulls": len(dates) - len(valid),
        "sources": evidence, "rights_status": "PENDING", "production_approval": "NOT_APPROVED",
    }
    with args.receipt.open("x", encoding="utf-8") as target:
        json.dump(result | {"observations": [
            {"period": day, "value": points[day]} for day in dates
        ]}, target, indent=2, allow_nan=False)
        target.write("\n")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
