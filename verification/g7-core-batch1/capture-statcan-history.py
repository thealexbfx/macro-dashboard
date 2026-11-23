"""Extract exact G7 vectors from separately downloaded official StatCan ZIPs."""

import argparse
import csv
import io
import json
import math
from datetime import date
from hashlib import file_digest
from pathlib import Path
from zipfile import ZipFile

SERIES = {
    "G7-CA-01": ("36100104", "Quarterly", "v62305752", {
        "COORDINATE": "1.1.1.30", "Prices": "Chained (2017) dollars",
        "Seasonal adjustment": "Seasonally adjusted at annual rates",
        "Estimates": "Gross domestic product at market prices",
        "UOM": "Dollars", "SCALAR_FACTOR": "millions",
    }),
    "G7-CA-11": ("14100287", "Monthly", "v2062815", {
        "COORDINATE": "1.7.1.1.1.1", "Labour force characteristics": "Unemployment rate",
        "Gender": "Total - Gender", "Age group": "15 years and over",
        "Statistics": "Estimate", "Data type": "Seasonally adjusted",
        "UOM": "Percent", "SCALAR_FACTOR": "units",
    }),
}


def capture(mapping, path):
    table, frequency, vector, dimensions = SERIES[mapping]
    if path.stat().st_size > 128 * 1024**2:
        raise ValueError("Compressed archive exceeds capture budget")
    with path.open("rb") as compressed:
        digest = file_digest(compressed, "sha256").hexdigest()
        compressed.seek(0)
        with ZipFile(compressed) as archive:
            members = archive.infolist()
            metadata_name = f"{table}_MetaData.csv"
            data_name = f"{table}.csv"
            if sorted(x.filename for x in members) != sorted([metadata_name, data_name]):
                raise ValueError("Unexpected archive members")
            if archive.getinfo(metadata_name).file_size > 1024**2 or archive.getinfo(data_name).file_size > 1536 * 1024**2:
                raise ValueError("Uncompressed archive exceeds capture budget")
            with archive.open(metadata_name) as source:
                metadata = next(csv.DictReader(io.TextIOWrapper(source, encoding="utf-8-sig")))
            if metadata["Product Id"] != table or metadata["Frequency"] != frequency:
                raise ValueError("Publisher table or frequency mismatch")
            points = {}
            with archive.open(data_name) as source:
                columns = next(csv.reader([source.readline().decode("utf-8-sig")]))
                token = f'"{vector}"'.encode()
                rows = (line.decode("utf-8") for line in source if token in line)
                for row in csv.DictReader(rows, fieldnames=columns):
                    if row["VECTOR"] != vector:
                        continue
                    if row["GEO"] != "Canada" or row["TERMINATED"] or any(row[k] != v for k, v in dimensions.items()):
                        raise ValueError("Publisher vector definition mismatch")
                    period = row["REF_DATE"]
                    day = date.fromisoformat(period + "-01")
                    if period in points or day.isoformat()[:7] != period:
                        raise ValueError("Duplicate or invalid reference period")
                    value = float(row["VALUE"]) if row["VALUE"] else None
                    if value is not None and not math.isfinite(value):
                        raise ValueError("Nonfinite observation")
                    points[period] = {"period": period, "value": value, "publisher_status": row["STATUS"] or None}
    periods = sorted(points)
    step = 3 if frequency == "Quarterly" else 1
    first = date.fromisoformat(metadata["Start Reference Period"])
    last = date.fromisoformat(metadata["End Reference Period"])
    expected = [
        f"{month // 12:04d}-{month % 12 + 1:02d}"
        for month in range(first.year * 12 + first.month - 1, last.year * 12 + last.month, step)
    ]
    if not periods or periods != expected or not any(p["value"] is not None for p in points.values()):
        raise ValueError("Vector coverage does not match the publisher table window")
    return {
        "mapping": mapping, "vector": vector, "frequency": frequency, "dimensions": dimensions,
        "source_url": f"https://www150.statcan.gc.ca/n1/tbl/csv/{table}-eng.zip",
        "archive_sha256": digest, "rights_status": "PENDING", "production_approval": "NOT_APPROVED",
        "observations": [points[period] for period in periods],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mapping", choices=SERIES)
    parser.add_argument("archive", type=Path)
    parser.add_argument("receipt", type=Path)
    args = parser.parse_args()
    result = capture(args.mapping, args.archive)
    with args.receipt.open("x", encoding="utf-8") as output:
        json.dump(result, output, indent=2, allow_nan=False)
        output.write("\n")
    points = result["observations"]
    print(json.dumps({
        "mapping": args.mapping, "first": points[0]["period"], "last": points[-1]["period"],
        "observations": sum(point["value"] is not None for point in points),
        "publisher_nulls": sum(point["value"] is None for point in points),
        "archive_sha256": result["archive_sha256"],
    }))


if __name__ == "__main__":
    main()
