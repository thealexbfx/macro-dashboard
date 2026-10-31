"""One bounded multi-series BLS backfill in documented ten-year request windows."""

import json
import time
from datetime import date
from hashlib import sha256

from backend.app.ingestion.contracts import ProviderError
from backend.app.ingestion.official_snapshots import MAX_BYTES, download


def capture(selectors, *, start=1910, end=None, fetch=download, pause=time.sleep):
    end = end or date.today().year
    if (
        not 1 <= len(selectors) <= 25
        or len(set(selectors)) != len(selectors)
        or not 1900 <= start <= end
        or (end - start) // 10 + 1 > 12
    ):
        raise ValueError("BLS free-access request budget exceeded")
    series = {key: [] for key in selectors}
    proofs = []
    for first in range(start, end + 1, 10):
        last = min(end, first + 9)
        payload = json.dumps(
            {"seriesid": selectors, "startyear": str(first), "endyear": str(last)}
        ).encode()
        raw, _ = fetch(
            "https://api.bls.gov/publicAPI/v2/timeseries/data/", payload=payload
        )
        data = json.loads(raw)
        if data.get("status") != "REQUEST_SUCCEEDED":
            raise ProviderError("bls_history_request_failed")
        returned = data.get("Results", {}).get("series", [])
        if {r["seriesID"] for r in returned} != set(selectors):
            raise ProviderError("bls_incomplete_series_batch")
        for row in returned:
            if any(not first <= int(p["year"]) <= last for p in row["data"]):
                raise ProviderError("bls_year_window_changed")
            series[row["seriesID"]].extend(row["data"])
        proofs.append(
            {
                "start": first,
                "end": last,
                "source_hash": sha256(raw).hexdigest(),
                "bytes": len(raw),
            }
        )
        if sum(p["bytes"] for p in proofs) > MAX_BYTES:
            raise ProviderError("bls_history_byte_budget")
        pause(1)
    combined = json.dumps(
        {
            "status": "REQUEST_SUCCEEDED",
            "Results": {
                "series": [
                    {"seriesID": key, "data": rows} for key, rows in series.items()
                ]
            },
            "source_windows": proofs,
        }
    ).encode()
    if len(combined) > MAX_BYTES:
        raise ProviderError("bls_history_byte_budget")
    return combined, {
        "url": "https://api.bls.gov/publicAPI/v2/timeseries/data/",
        "source_windows": proofs,
    }
