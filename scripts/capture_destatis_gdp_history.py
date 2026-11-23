"""Capture the official German X13 real GDP level from the Destatis workbook."""
import argparse
import io
import json
import math
import re
from hashlib import sha256
from pathlib import Path
from zipfile import ZipFile

from openpyxl import load_workbook

PATH = (
    "/DE/Themen/Wirtschaft/Volkswirtschaftliche-Gesamtrechnungen-Inlandsprodukt/"
    "Publikationen/Downloads-Inlandsprodukt/inlandsprodukt-saisonbereinigt-xlsx-2180130.xlsx"
)
SOURCE = "https://www.destatis.de" + PATH + "?__blob=publicationFile&v=60"


def quarters(sheet, column, last):
    if sheet.max_row > 400 or sheet.max_column > 30:
        raise ValueError("Unexpected Destatis workbook dimensions")
    rows = sheet.iter_rows(min_row=11, max_col=column, values_only=True)
    year = None
    values = {}
    for row in rows:
        label = row[1]
        if label is None:
            if any(cell is not None for cell in row[1:]):
                raise ValueError("Destatis workbook has an unlabeled quarterly value")
            continue
        if not isinstance(label, str) or not re.fullmatch(r"[1-4]\.Vj", label):
            raise ValueError("Unexpected Destatis quarterly label")
        quarter = int(label[0])
        if quarter == 1:
            year = row[0]
            if type(year) is not int or not 1991 <= year <= last[0]:
                raise ValueError("Unexpected Destatis year")
        elif row[0] is not None or year is None:
            raise ValueError("Destatis year grouping changed")
        value = row[column - 1]
        key = year * 4 + quarter - 1
        if key in values or type(value) not in (float, int) or not math.isfinite(value) or value <= 0:
            raise ValueError("Invalid or duplicate Destatis GDP value")
        values[key] = value
    if list(values) != list(range(1991 * 4, last[0] * 4 + last[1])):
        raise ValueError("Incomplete Destatis quarterly history")
    return values


def capture(path):
    with path.open("rb") as stream:
        raw = stream.read(8 * 1024**2 + 1)
    if len(raw) > 8 * 1024**2:
        raise ValueError("Destatis workbook exceeds size limit")
    with ZipFile(io.BytesIO(raw)) as archive:
        if sum(entry.file_size for entry in archive.infolist()) > 64 * 1024**2:
            raise ValueError("Destatis workbook exceeds expanded size limit")
    workbook = load_workbook(io.BytesIO(raw), read_only=True, data_only=True)
    try:
        cover, primary, check = (workbook[name] for name in ("Vorblatt", "1.1", "1.2"))
        edition = cover["B48"].value
        if (edition != "2. Vierteljahr 2026"
                or primary["A1"].value != "1 Bruttoinlandsprodukt, preisbereinigt"
                or primary["A2"].value != "1.1 Ergebnisse nach X13"
                or primary["I8"].value != "saison- und kalenderbereinigt"
                or primary["I10"].value != "2020 = 100"
                or check["A2"].value != "1.2 Komponentenzerlegung nach X13"
                or check["E10"].value != "2020 = 100"):
            raise ValueError("Destatis GDP series definition changed")
        latest = (2026, 2)
        values = quarters(primary, 9, latest)
        if values != quarters(check, 5, latest):
            raise ValueError("Destatis workbook GDP columns disagree")
        points = [{"period": f"{k // 4}-Q{k % 4 + 1}", "value": value}
                  for k, value in values.items()]
        return {
            "mapping": "G7-DE-01", "publisher_series": "2180130/1.1/I",
            "source_url": SOURCE, "source_sha256": sha256(raw).hexdigest(),
            "publisher_edition": edition, "publisher_release_note": cover["B53"].value,
            "unit": "Volume index, 2020=100", "first": points[0]["period"],
            "last": points[-1]["period"], "valid_observations": len(points),
            "publisher_nulls": 0, "rights_status": "PENDING",
            "production_approval": "NOT_APPROVED", "observations": points,
        }
    finally:
        workbook.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workbook", type=Path)
    parser.add_argument("receipt", type=Path)
    args = parser.parse_args()
    receipt = capture(args.workbook)
    with args.receipt.open("x", encoding="utf-8") as stream:
        json.dump(receipt, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps({key: value for key, value in receipt.items() if key != "observations"}))


if __name__ == "__main__":
    main()
