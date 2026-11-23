"""Capture official Japanese quarterly GDP and monthly unemployment release files."""

import argparse
import csv
import io
import json
import math
import re
from hashlib import sha256
from pathlib import Path
from zipfile import ZipFile

GDP_SOURCE = "https://www.esri.cao.go.jp/jp/sna/data/data_list/sokuhou/files/2026/qe262_2/tables/gaku-jk2622.csv"
LFS_SOURCE = "https://www.e-stat.go.jp/en/stat-search/file-download?fileKind=0&statInfId=000031831358"


def capture_gdp(raw):
    rows = list(csv.reader(io.StringIO(raw.decode("cp932"))))
    if (rows[1][0] != "Real, Seasonally Adjusted Series"
        or "(Billions of Chained (2020) Yen)" not in rows[1]
        or rows[5][1] != "GDP(Expenditure Approach)"
        or not any(row and row[0] == "＊年率で表示している。" for row in rows)):
        raise ValueError("Unexpected Cabinet Office GDP definition")
    points = []
    for row in rows[7:]:
        match = re.fullmatch(r"(?:(\d{4})/)?\s*(1|4|7|10)-\s*(3|6|9|12)\.", row[0])
        if not match:
            if row[0].startswith("＊") and not any(row[1:]):
                continue
            raise ValueError("Unexpected GDP reference quarter")
        year, start, end = match.groups()
        index = 1994 * 4 + len(points)
        expected_year, quarter = divmod(index, 4)
        if (int(start) != 1 + quarter * 3 or int(end) != 3 + quarter * 3
            or year != (str(expected_year) if quarter == 0 else None)):
            raise ValueError("GDP quarterly coverage mismatch")
        value = float(row[1].replace(",", "").strip())
        if not math.isfinite(value) or value <= 0:
            raise ValueError("Invalid GDP level")
        points.append({"period": f"{expected_year}-Q{quarter + 1}", "value": value})
    return points


def capture_lfs(raw):
    from openpyxl import load_workbook

    with ZipFile(io.BytesIO(raw)) as archive:
        members = archive.infolist()
        if len(members) > 100 or sum(member.file_size for member in members) > 64 * 1024**2:
            raise ValueError("Unemployment workbook exceeds expansion budget")
    workbook = load_workbook(io.BytesIO(raw), read_only=True, data_only=True)
    try:
        sheet = workbook["季節調整値"]
        if sheet.max_row > 2000 or sheet.max_column != 22:
            raise ValueError("Unexpected unemployment worksheet size")
        rows = list(sheet.values)
    finally:
        workbook.close()
    if ("Whole Japan, Monthly Data" not in rows[1][4]
        or "Seasonally adjusted series" not in rows[4][4]
        or " ".join(rows[6][19].split()) != "Unemployment rate (percent)"
        or rows[8][19] != "Both sexes"):
        raise ValueError("Unexpected Labour Force Survey definition")
    points = []
    for row in rows[10:]:
        if row[1] is None:
            if row[19] is not None:
                raise ValueError("Unemployment observation lacks reference month")
            continue
        index = 1953 * 12 + len(points)
        year, month = divmod(index, 12)
        if row[1] != f"{month + 1}月" or (month == 1 and row[0] != year):
            raise ValueError("Unemployment monthly coverage mismatch")
        value = row[19]
        if value is not None and (type(value) not in (int, float) or not 0 <= value <= 100):
            raise ValueError("Invalid unemployment rate")
        points.append({"period": f"{year}-{month + 1:02d}", "value": value, "publisher_flag": row[3]})
    # The workbook prints placeholder rows for unpublished months of the current year.
    while points and points[-1]["value"] is None:
        points.pop()
    return points


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("series", choices=("gdp", "unemployment"))
    parser.add_argument("publisher_file", type=Path)
    parser.add_argument("receipt", type=Path)
    args = parser.parse_args()
    budget = 8 * 1024**2
    with args.publisher_file.open("rb") as source:
        raw = source.read(budget + 1)
    if len(raw) > budget:
        raise ValueError("Publisher file exceeds capture budget")
    if args.series == "gdp":
        mapping, source, unit = "G7-JP-01", GDP_SOURCE, "Billions of chained 2020 yen, annual rate"
        points = capture_gdp(raw)
    else:
        mapping, source, unit = "G7-JP-11", LFS_SOURCE, "Percent, both sexes"
        points = capture_lfs(raw)
    if not points:
        raise ValueError("No publisher observations")
    summary = {
        "mapping": mapping, "source_url": source, "source_sha256": sha256(raw).hexdigest(),
        "unit": unit, "seasonal_adjustment": "Seasonally adjusted",
        "first": points[0]["period"], "last": points[-1]["period"],
        "valid_observations": sum(point["value"] is not None for point in points),
        "publisher_nulls": sum(point["value"] is None for point in points),
        "rights_status": "PENDING", "production_approval": "NOT_APPROVED",
    }
    with args.receipt.open("x", encoding="utf-8") as output:
        json.dump(summary | {"observations": points}, output, indent=2, allow_nan=False)
        output.write("\n")
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
