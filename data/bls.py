import datetime as dt
from pathlib import Path
import time
import os
import tempfile

import pandas as pd
import requests
import streamlit as st

from config import BLS_API_KEY


CACHE_DIR = Path("data_cache") / "bls"
CACHE_TTL_DAYS = 1


def _cache_path(series_id: str, start_year: int) -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR / f"{series_id}_{start_year}.csv"


def _cache_is_fresh(path: Path) -> bool:
    if not path.exists():
        return False

    modified_time = dt.datetime.fromtimestamp(path.stat().st_mtime)
    age = dt.datetime.now() - modified_time

    return age.days < CACHE_TTL_DAYS


def _read_cached_series(path: Path, stale=False, error=None) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["date"] = pd.to_datetime(df["date"])
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df = df.sort_values("date").reset_index(drop=True)
    df.attrs['retrieval'] = {'provider':'BLS','cache':'stale' if stale else 'fresh',
                             'cache_saved_at':dt.datetime.fromtimestamp(path.stat().st_mtime, dt.timezone.utc).isoformat(),
                             'error':error}
    return df


def _write_cached_series(df: pd.DataFrame, path: Path) -> None:
    with tempfile.NamedTemporaryFile(mode='w', dir=path.parent, suffix='.csv', delete=False) as out:
        temporary = out.name
        df.to_csv(out, index=False)
    try:
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary): os.unlink(temporary)


def _post_json(payload):
    """At most three attempts for transient failures; no retry on invalid requests.

    Short waits bound UI latency. Never include the registration key in errors.
    """
    for attempt in range(3):
        try:
            response = requests.post('https://api.bls.gov/publicAPI/v2/timeseries/data/', json=payload, timeout=(5,10))
        except (requests.Timeout, requests.ConnectionError):
            if attempt == 2: raise RuntimeError('BLS connection/timeout failure after 3 attempts') from None
        else:
            if response.status_code == 200:
                try: return response.json()
                except ValueError: raise RuntimeError('BLS returned invalid JSON') from None
            if response.status_code not in (429,500,502,503,504) or attempt == 2:
                raise RuntimeError(f'BLS HTTP {response.status_code} after {attempt+1} attempt(s)')
        time.sleep(2 ** attempt)


def _request_or_cache(payload, cache_file):
    try:
        data = _post_json(payload)
        if data.get('status') != 'REQUEST_SUCCEEDED':
            raise RuntimeError('BLS rejected the query (check quota, registration and series/date range)')
        return data
    except (RuntimeError, requests.RequestException) as exc:
        if cache_file.exists():
            return _read_cached_series(cache_file, stale=True, error=str(exc))
        raise


@st.cache_data(ttl=3600, show_spinner=False)
def get_bls_series(series_id: str, start_year: int = 2000):
    """Fetch a BLS time series with persistent CSV cache."""
    cache_file = _cache_path(series_id, start_year)

    if _cache_is_fresh(cache_file):
        return _read_cached_series(cache_file)

    current_year = dt.date.today().year

    all_rows = []
    chunk_size = 20 if BLS_API_KEY else 10

    for chunk_start in range(start_year, current_year + 1, chunk_size):
        chunk_end = min(chunk_start + chunk_size - 1, current_year)

        payload = {
            "seriesid": [series_id],
            "startyear": str(chunk_start),
            "endyear": str(chunk_end),
        }

        if BLS_API_KEY:
            payload["registrationkey"] = BLS_API_KEY

        data = _request_or_cache(payload, cache_file)
        if isinstance(data, pd.DataFrame):
            return data

        series_list = data.get("Results", {}).get("series", [])

        if not series_list:
            return pd.DataFrame(columns=["date", "value"])

        series = series_list[0].get("data", [])

        for item in series:
            period = item["period"]

            if period == "M13":
                continue

            value_str = item.get("value")

            try:
                value = float(value_str)
            except (ValueError, TypeError):
                value = float('nan')

            year = int(item["year"])

            if period.startswith("M"):
                month = int(period.replace("M", ""))
                date = pd.Timestamp(year=year, month=month, day=1) + pd.offsets.MonthEnd(0)

            elif period.startswith("Q"):
                quarter = int(period.replace("Q", ""))
                month = {1: 3, 2: 6, 3: 9, 4: 12}.get(quarter)

                if month is None:
                    continue

                date = pd.Timestamp(year=year, month=month, day=1) + pd.offsets.MonthEnd(0)

            else:
                continue

            all_rows.append({
                "date": date,
                "value": value,
            })

    df = pd.DataFrame(all_rows)

    if df.empty:
        return pd.DataFrame(columns=["date", "value"])

    df = df.drop_duplicates(subset=["date"])
    df = df.sort_values("date").reset_index(drop=True)

    _write_cached_series(df, cache_file)
    df.attrs['retrieval'] = {'provider':'BLS','cache':'live','fetched_at':dt.datetime.now(dt.timezone.utc).isoformat()}
    return df
