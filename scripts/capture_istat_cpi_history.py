"""Link Istat's published NIC base segments using its published coefficients."""
import argparse
import io
import json
import re
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
from xml.etree import ElementTree
from zipfile import ZipFile

from openpyxl import load_workbook

from scripts.capture_insee_core_history import MESSAGE, MAX_BYTES
from scripts.capture_istat_core_history import HOST, QUERY

PATH = "/SDMXWS/rest/data/IT1,167_745_DF_DCSP_NIC1B2025_6,1.0/M.IT..4.00/ALL/"
SOURCE = HOST + PATH + "?" + QUERY
COEFFICIENTS = HOST + "/databrowser/DWL/Prezzi/DCSP_NIC1B2025/DCSP_NIC_CR_Ecoicov2_rev.xlsx"
SEGMENTS = {
    "1": (1995, "1996-01", "2010-12"),
    "9": (2010, "2011-01", "2015-12"),
    "39": (2015, "2016-01", "2025-12"),
    "85": (2025, "2026-01", None),
}
METHOD = "Divide each older index level by the product of Istat’s published linking coefficients through base 2025."


def read_coefficients(raw):
    if len(raw) > 2 * 1024**2:
        raise ValueError("Istat coefficient workbook exceeds capture limit")
    with ZipFile(io.BytesIO(raw)) as archive:
        if sum(entry.file_size for entry in archive.infolist()) > 16 * 1024**2:
            raise ValueError("Istat coefficient workbook exceeds expanded size limit")
    workbook = load_workbook(io.BytesIO(raw), read_only=True, data_only=True)
    try:
        it, en = workbook["IT"], workbook["EN"]
        expected = tuple(f"splicing coefficient from base {left} to base {right}"
                         for left, right in [(1995, 2010), (2010, 2015), (2015, 2025)])
        if tuple(en.cell(16, c).value for c in (4, 5, 6)) != expected:
            raise ValueError("Istat coefficient direction changed")
        rows = [tuple(s.cell(row, c).value for c in range(1, 7)) for s, row in [(it, 16), (en, 17)]]
        if rows[0] != rows[1] or rows[0][:3] != ("00", "Gen.", "Indice generale"):
            raise ValueError("Istat national all-items coefficients disagree")
        coeff = tuple(Decimal(str(value)) for value in rows[0][3:])
        if any(not value.is_finite() or value <= 0 for value in coeff):
            raise ValueError("Invalid Istat coefficients")
        return coeff
    finally:
        workbook.close()


def capture(raw, weights):
    if len(raw) > MAX_BYTES:
        raise ValueError("Istat NIC response exceeds capture limit")
    xml = raw.decode("utf-8-sig")
    if "<!DOCTYPE" in xml or "<!ENTITY" in xml:
        raise ValueError("Istat response includes unsupported XML declarations")
    root = ElementTree.fromstring(xml)
    sender = root.find(f"./{MESSAGE}Header/{MESSAGE}Sender")
    structure = root.find(f"./{MESSAGE}Header/{MESSAGE}Structure")
    series = root.findall(f"./{MESSAGE}DataSet/Series")
    if (root.tag != f"{MESSAGE}StructureSpecificData" or sender is None
            or sender.get("id") != "ISTAT" or structure is None
            or structure.get("structureID") != "IT1_167_745_DF_DCSP_NIC1B2025_6_1_0"
            or len(series) != len(SEGMENTS)
            or {s.get("DATA_TYPE") for s in series} != SEGMENTS.keys()):
        raise ValueError("Istat NIC dataflow or base segments changed")
    a, b, c = read_coefficients(weights)
    divisors = {1995: a * b * c, 2010: b * c, 2015: c, 2025: Decimal(1)}
    points = {}
    for segment in series:
        if any(segment.get(k) != v for k, v in {"FREQ": "M", "REF_AREA": "IT",
                                               "MEASURE": "4", "ECOICOP_2": "00"}.items()):
            raise ValueError("Istat national all-items NIC selection changed")
        base, first, last = SEGMENTS[segment.attrib["DATA_TYPE"]]
        for row in segment:
            month = row.get("TIME_PERIOD", "")
            if (row.tag != "Obs" or not re.fullmatch(r"[0-9]{4}-(0[1-9]|1[0-2])", month)
                    or month in points or month < first or (last is not None and month > last)):
                raise ValueError("Invalid or overlapping Istat NIC reference period")
            publisher_value = row.get("OBS_VALUE", "")
            if not re.fullmatch(r"[0-9]{1,4}(\.[0-9]+)?", publisher_value) or Decimal(publisher_value) <= 0:
                raise ValueError("Invalid Istat NIC observation")
            status = row.get("OBS_STATUS")
            flag = f"rebased_from_{base}" if base != 2025 else "publisher_2025_base"
            points[month] = {
                "period": month, "value": float(Decimal(publisher_value) / divisors[base]),
                "publisher_flag": f"{flag} OBS_STATUS={status}" if status else flag,
                "publisher_value": publisher_value, "publisher_base_year": base,
            }
    periods = sorted(points)
    ordinals = [int(p[:4]) * 12 + int(p[5:]) for p in periods]
    if (not periods or periods[0] != "1996-01" or periods[-1] < "2026-10"
            or ordinals != list(range(ordinals[0], ordinals[-1] + 1))):
        raise ValueError("Incomplete Istat NIC history")
    return {
        "mapping": "G7-IT-07", "publisher_series": "M.IT.1+9+39+85.4.00",
        "source_url": SOURCE, "source_sha256": sha256(raw).hexdigest(),
        "coefficient_source_url": COEFFICIENTS, "coefficient_source_sha256": sha256(weights).hexdigest(),
        "linking_coefficients": {"1995_to_2010": str(a), "2010_to_2015": str(b), "2015_to_2025": str(c)},
        "transformation": METHOD, "unit": "2025=100 (historical levels linked)",
        "first": periods[0], "last": periods[-1], "valid_observations": len(periods), "publisher_nulls": 0,
        "rights_status": "PENDING", "production_approval": "NOT_APPROVED",
        "observations": [points[month] for month in periods],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("publisher_file", type=Path)
    parser.add_argument("coefficient_file", type=Path)
    parser.add_argument("receipt", type=Path)
    args = parser.parse_args()
    with args.publisher_file.open("rb") as source, args.coefficient_file.open("rb") as coefficients:
        receipt = capture(source.read(MAX_BYTES + 1), coefficients.read(2 * 1024**2 + 1))
    with args.receipt.open("x", encoding="utf-8") as stream:
        json.dump(receipt, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps({key: value for key, value in receipt.items() if key != "observations"}))


if __name__ == "__main__":
    main()
