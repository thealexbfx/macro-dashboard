"""Import six official release excerpts into a new development SQLite file."""
import argparse
from datetime import date
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import re
import sqlite3


def observations(series):
    row = series["row"]
    if series["cells"] == "html":
        values = re.findall(r"<td><strong>([0-9.]+)</strong></td>", row)[:3]
    elif series["cells"] == "markdown":
        values = [value.strip() for value in row.strip("|").split("|")[1:]]
    elif series["cells"] == "whitespace":
        values = row.split()
    else:
        raise ValueError("Unknown source row format")
    months = series["months"]
    if len(values) != len(months) or months != sorted(set(months)):
        raise ValueError(f"Invalid source dates or column count: {series['id']}")
    if not values or Decimal(values[-1]) != Decimal(series["expected"]):
        raise ValueError(f"Release headline mismatch: {series['id']}")
    for month, value in zip(months, values, strict=True):
        if not re.fullmatch(r"\d{4}-\d{2}", month):
            raise ValueError(f"Invalid reference month: {month}")
        date.fromisoformat(month + "-01")
        if not Decimal(value).is_finite():
            raise ValueError(f"Invalid observation: {value}")
    return list(zip(months, values, strict=True))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("snapshot", type=Path)
    parser.add_argument("database", type=Path)
    args = parser.parse_args()
    payload = args.snapshot.read_bytes()
    digest = hashlib.sha256(payload).hexdigest()
    prepared = []
    for release in json.loads(payload)["release_snapshots"]:
        released = date.fromisoformat(release["release"])
        for series in release["series"]:
            points = observations(series)
            if date.fromisoformat(points[-1][0] + "-01") >= released:
                raise ValueError(f"Reference period precedes release check failed: {series['id']}")
            prepared.append((release, series, points))
    if len({series["id"] for _, series, _ in prepared}) != len(prepared):
        raise ValueError("Duplicate series IDs")
    # Exclusive creation keeps this tool away from every pre-existing database.
    with args.database.open("xb"):
        pass
    try:
        with sqlite3.connect(args.database) as db:
            db.execute("CREATE TABLE series (id TEXT PRIMARY KEY, selector TEXT, units TEXT, adjustment TEXT, producer TEXT, source TEXT, release TEXT, licence TEXT, excerpt_sha256 TEXT, paid_display INTEGER CHECK(paid_display = 0), export INTEGER CHECK(export = 0), ai INTEGER CHECK(ai = 0), radar INTEGER CHECK(radar = 0))")
            db.execute("CREATE TABLE observations (id TEXT, month TEXT, value TEXT, PRIMARY KEY (id, month), FOREIGN KEY (id) REFERENCES series(id))")
            db.execute("PRAGMA foreign_keys = ON")
            for release, series, points in prepared:
                db.execute(
                    "INSERT INTO series VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0, 0, 0)",
                    (series["id"], series["selector"], series["units"], series["adjustment"],
                     release["producer"], release["url"], release["release"], release["licence"], digest),
                )
                db.executemany(
                    "INSERT INTO observations VALUES (?, ?, ?)",
                    ((series["id"], month, value) for month, value in points),
                )
            print(json.dumps(db.execute(
                "SELECT id, count(*), min(month), max(month) FROM observations GROUP BY id ORDER BY id"
            ).fetchall(), indent=2))
    except Exception:
        args.database.unlink()
        raise


if __name__ == "__main__":
    main()
