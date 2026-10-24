"""Bounded Yahoo chart request for closing observations; no local database."""

from datetime import datetime, timezone
from urllib.parse import quote
import pandas as pd
import requests


def get_fx_data_yahoo(ticker="GBPUSD=X", start_date=None, end_date=None):
    def epoch(value, default):
        return (
            int(pd.Timestamp(value).tz_localize("UTC").timestamp())
            if value is not None
            else default
        )

    end = epoch(end_date, int(datetime.now(timezone.utc).timestamp()))
    start = epoch(start_date, end - 365 * 86400)
    response = requests.get(
        "https://query1.finance.yahoo.com/v8/finance/chart/" + quote(ticker, safe=""),
        params={"period1": start, "period2": end, "interval": "1d"},
        headers={"User-Agent": "MacroLensResearch/1.0"},
        timeout=(10, 20),
    )
    response.raise_for_status()
    raw = response.json()
    result = (raw.get("chart", {}).get("result") or [None])[0]
    if not result:
        raise RuntimeError("No source observations returned")
    stamps = result.get("timestamp", [])
    closes = (((result.get("indicators") or {}).get("quote") or [{}])[0]).get(
        "close", []
    )
    if len(stamps) != len(closes):
        raise RuntimeError("Incomplete provider response")
    return (
        pd.DataFrame(
            {
                "date": pd.to_datetime(stamps, unit="s", utc=True)
                .tz_convert(None)
                .normalize(),
                "value": closes,
            }
        )
        .sort_values("date")
        .reset_index(drop=True)
    )
