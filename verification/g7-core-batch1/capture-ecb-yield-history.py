"""Capture national monthly ten-year convergence yields from the ECB."""

import argparse
import csv
import io
import json
import math
from datetime import date
from hashlib import sha256
from pathlib import Path
from urllib.request import urlopen

COUNTRIES = ("DE", "FR", "IT")
MAX_BYTES = 2_000_000


def capture(country, body):
    if len(body) > MAX_BYTES:
        raise ValueError("ECB response exceeds capture budget")
    series = f"IRS.M.{country}.L.L40.CI.0000.EUR.N.Z"
    expected = {
        "KEY": series, "FREQ": "M", "REF_AREA": country, "IR_TYPE": "L",
        "TR_TYPE": "L40", "MATURITY_CAT": "CI", "CURRENCY_TRANS": "EUR",
        "UNIT": "PC", "UNIT_MULT": "0", "COLLECTION": "A",
    }
    points = {}
    for row in csv.DictReader(io.StringIO(body.decode("utf-8-sig"))):
        if any(row.get(field) != value for field, value in expected.items()):
            raise ValueError("ECB series definition mismatch")
        period = row["TIME_PERIOD"]
        month = date.fromisoformat(period + "-01")
        if month.isoformat()[:7] != period or month in points:
            raise ValueError("Invalid or duplicate reference month")
        value = float(row["OBS_VALUE"]) if row["OBS_VALUE"] else None
        if value is not None and not math.isfinite(value):
            raise ValueError("Nonfinite ECB observation")
        points[month] = {"period": period, "value": value, "status": row["OBS_STATUS"]}
    months = sorted(points)
    if not any(point["value"] is not None for point in points.values()):
        raise ValueError("ECB response has no usable observations")
    missing = []
    for offset in range(months[0].year * 12 + months[0].month - 1,
                        months[-1].year * 12 + months[-1].month):
        month = date(offset // 12, offset % 12 + 1, 1)
        if month not in points:
            missing.append(month.isoformat()[:7])
    return {
        "mapping": f"G7-{country}-23", "source_url": source_url(country),
        "definition": expected, "source_sha256": sha256(body).hexdigest(),
        "missing_months": missing, "rights_status": "PENDING",
        "production_approval": "NOT_APPROVED",
        "observations": [points[month] for month in months],
    }


def source_url(country):
    return f"https://data-api.ecb.europa.eu/service/data/IRS/M.{country}.L.L40.CI.0000.EUR.N.Z?format=csvdata"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("country", choices=COUNTRIES)
    parser.add_argument("receipt", type=Path)
    parser.add_argument("--publisher-csv", type=Path)
    args = parser.parse_args()
    if args.publisher_csv:
        with args.publisher_csv.open("rb") as source:
            result = capture(args.country, source.read(MAX_BYTES + 1))
    else:
        url = source_url(args.country)
        with urlopen(url, timeout=20) as source:
            if source.geturl() != url:
                raise ValueError("Unexpected ECB response URL")
            result = capture(args.country, source.read(MAX_BYTES + 1))
    with args.receipt.open("x", encoding="utf-8") as target:
        json.dump(result, target, indent=2, allow_nan=False)
        target.write("\n")
    points = result["observations"]
    print(json.dumps({
        "mapping": result["mapping"], "first": points[0]["period"], "last": points[-1]["period"],
        "observations": sum(point["value"] is not None for point in points),
        "nulls": sum(point["value"] is None for point in points),
        "missing_months": len(result["missing_months"]), "source_sha256": result["source_sha256"],
    }))


if __name__ == "__main__":
    main()
