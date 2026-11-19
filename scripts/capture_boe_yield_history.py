"""Write a development receipt for an official Bank of England IUDMNPY CSV."""

import argparse
import json
import math
from dataclasses import asdict
from hashlib import sha256
from pathlib import Path

from backend.app.ingestion.expansion_sources import parse_boe

SOURCE = (
    "https://www.bankofengland.co.uk/boeapps/database/_iadb-fromshowcolumns.asp"
    "?csv.x=yes&Datefrom=01%2FJan%2F1963&Dateto=now&SeriesCodes=IUDMNPY&UsingCodes=Y&CSVF=CT"
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("publisher_csv", type=Path)
    parser.add_argument("receipt", type=Path)
    args = parser.parse_args()
    limit = 2_000_000
    with args.publisher_csv.open("rb") as source:
        body = source.read(limit + 1)
    if len(body) > limit:
        raise ValueError("BoE response exceeds capture budget")
    definition, points, metadata = parse_boe({
        "id": "g7_gb_10y_nominal_par_yield",
        "frequency": "daily",
        "source": {"provider": "boe", "selector": "IUDMNPY"},
    }, body)
    dates = [point.period for point in points]
    values = [point.value for point in points if point.value is not None]
    if dates != sorted(set(dates)) or not values or not all(map(math.isfinite, values)):
        raise ValueError("Invalid British government yield history")
    result = {
        "mapping": "G7-GB-23", "definition": asdict(definition), "metadata": metadata,
        "source_url": SOURCE, "source_sha256": sha256(body).hexdigest(),
        "first": dates[0], "last": dates[-1], "valid_observations": len(values),
        "publisher_nulls": len(points) - len(values), "rights_status": "PENDING",
        "production_approval": "NOT_APPROVED",
    }
    with args.receipt.open("x", encoding="utf-8") as target:
        json.dump(result | {"observations": [asdict(point) for point in points]},
                  target, indent=2, allow_nan=False)
        target.write("\n")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
