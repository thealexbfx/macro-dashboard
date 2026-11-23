"""Capture original Istat real GDP and unemployment histories."""
import argparse
import json
import math
import re
from datetime import datetime
from hashlib import sha256
from pathlib import Path
from xml.etree import ElementTree

from scripts.capture_insee_core_history import MESSAGE, MAX_BYTES

PATH = (
    "/SDMXWS/rest/data/IT1,NAG_08,1.0/"
    "..NFI_R_CH_SA_EUR+NGDP_R_CH_SA_EUR+NM_R_CH_SA_EUR+NX_R_CH_SA_EUR../ALL/"
)
QUERY = "detail=full&dimensionAtObservation=TIME_PERIOD&format=structurespecificdata"
HOST = "https://esploradati.istat.it"
GDP_SOURCE = HOST + PATH + "?" + QUERY
LABOR_PATH = (
    "/SDMXWS/rest/data/IT1,151_874_DF_DCCV_TAXDISOCCUMENS1_1,1.0/"
    "M.IT.UNEM_R.Y.9.Y15-74.2026M10G29/ALL/"
)
LABOR_SOURCE = HOST + LABOR_PATH + "?" + QUERY
SERIES = {
    "G7-IT-01": (
        GDP_SOURCE, "NGDP_R_CH_SA_EUR", "IT1_NAG_08_1_0",
        {"DATA_DOMAIN": "NAG", "REF_AREA": "IT", "COUNTERPART_AREA": "_Z",
         "FREQ": "Q", "UNIT_MULT": "6", "INDICATOR": "NGDP_R_CH_SA_EUR"},
        "Millions of chained 2020 euros", "1996-Q1", "2026-Q3",
    ),
    "G7-IT-11": (
        LABOR_SOURCE, "M.IT.UNEM_R.Y.9.Y15-74", "IT1_151_874_DF_DCCV_TAXDISOCCUMENS1_1_1_0",
        {"FREQ": "M", "REF_AREA": "IT", "DATA_TYPE": "UNEM_R", "ADJUSTMENT": "Y",
         "SEX": "9", "AGE": "Y15-74", "EDITION": "2026M10G29"},
        "Percent", "2004-01", "2026-09",
    ),
}


def capture(mapping, raw):
    source, selector, structure_id, expected, unit, first, last = SERIES[mapping]
    monthly = expected["FREQ"] == "M"
    if len(raw) > MAX_BYTES:
        raise ValueError("Istat response exceeds capture budget")
    xml = raw.decode("utf-8-sig")
    if "<!DOCTYPE" in xml or "<!ENTITY" in xml:
        raise ValueError("Istat response includes unsupported XML declarations")
    root = ElementTree.fromstring(xml)
    header = root.find(f"./{MESSAGE}Header")
    data = root.findall(f"./{MESSAGE}DataSet")
    if root.tag != f"{MESSAGE}StructureSpecificData" or header is None or len(data) != 1:
        raise ValueError("Expected one Istat structure-specific dataset")
    sender = header.find(f"{MESSAGE}Sender")
    structure = header.find(f"{MESSAGE}Structure")
    if (sender is None or sender.get("id") != "ISTAT" or structure is None
            or structure.get("structureID") != structure_id):
        raise ValueError("Istat source or dataflow differs")
    prepared = datetime.fromisoformat(header.findtext(f"{MESSAGE}Prepared", ""))
    series = [row for row in data[0].findall("Series")
              if all(row.get(key) == value for key, value in expected.items())]
    if len(series) != 1:
        raise ValueError("Istat series identity, unit or geographic coverage differs")
    pattern = r"[0-9]{4}-(0[1-9]|1[0-2])" if monthly else r"[0-9]{4}-Q([1-4])"
    points = {}
    for row in series[0]:
        period = row.get("TIME_PERIOD", "")
        match = re.fullmatch(pattern, period)
        if row.tag != "Obs" or not match or period in points:
            raise ValueError("Invalid or duplicate Istat reference period")
        value = float(row.get("OBS_VALUE", "nan"))
        if not math.isfinite(value) or (not 0 <= value <= 100 if monthly else value <= 0):
            raise ValueError("Invalid Istat observation value")
        points[period] = {"period": period, "value": value, "publisher_flag": row.get("OBS_STATUS")}
    periods = sorted(points)
    periods_per_year = 12 if monthly else 4
    ordinals = [int(p[:4]) * periods_per_year + int(p[5:].lstrip("Q")) for p in periods]
    if (not periods or periods[0] != first
            or ordinals != list(range(ordinals[0], ordinals[-1] + 1))
            or (periods[-1] != last if monthly else periods[-1] < last)):
        raise ValueError("Incomplete Istat history")
    return {
        "mapping": mapping, "publisher_series": selector, "source_url": source,
        "source_sha256": sha256(raw).hexdigest(), "publisher_response_prepared": prepared.isoformat(),
        "publisher_edition": expected.get("EDITION"), "unit": unit, "first": periods[0], "last": periods[-1],
        "valid_observations": len(periods), "publisher_nulls": 0,
        "rights_status": "PENDING", "production_approval": "NOT_APPROVED",
        "observations": [points[period] for period in periods],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mapping", choices=SERIES)
    parser.add_argument("publisher_file", type=Path)
    parser.add_argument("receipt", type=Path)
    args = parser.parse_args()
    with args.publisher_file.open("rb") as stream:
        receipt = capture(args.mapping, stream.read(MAX_BYTES + 1))
    with args.receipt.open("x", encoding="utf-8") as stream:
        json.dump(receipt, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps({key: value for key, value in receipt.items() if key != "observations"}))


if __name__ == "__main__":
    main()
