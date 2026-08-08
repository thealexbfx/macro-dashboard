import datetime as dt
from pathlib import Path
import time

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


def _read_cached_series(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["date"] = pd.to_datetime(df["date"])
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    return df.dropna().sort_values("date").reset_index(drop=True)


def _write_cached_series(df: pd.DataFrame, path: Path) -> None:
    df.to_csv(path, index=False)


@st.cache_data(ttl=3600, show_spinner=False)
def get_bls_series(series_id: str, start_year: int = 2000):
    """Fetch a BLS time series with persistent CSV cache."""
    cache_file = _cache_path(series_id, start_year)

    if _cache_is_fresh(cache_file):
        return _read_cached_series(cache_file)

    url = "https://api.bls.gov/publicAPI/v2/timeseries/data/"
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

        last_error = None

        for attempt in range(3):
            try:
                r = requests.post(
                    url,
                    json=payload,
                    timeout=30,
                )
                r.raise_for_status()
                data = r.json()
                last_error = None
                break

            except requests.RequestException as exc:
                last_error = exc

                if attempt < 2:
                    time.sleep(5 * (attempt + 1))

        if last_error is not None:
            if cache_file.exists():
                st.warning(
                    f"BLS request failed for {series_id} after retries. "
                    f"Using stale cached data instead. Error: {last_error}"
                )
                return _read_cached_series(cache_file)

            raise last_error

        if data.get("status") != "REQUEST_SUCCEEDED":
            message = data.get("message", ["Unknown BLS error"])

            if cache_file.exists():
                st.warning(
                    f"BLS request failed for {series_id}. "
                    f"Using stale cached data instead. Error: {message}"
                )
                return _read_cached_series(cache_file)

            raise RuntimeError(f"BLS request failed for {series_id}: {message}")

        series_list = data.get("Results", {}).get("series", [])

        if not series_list:
            return pd.DataFrame(columns=["date", "value"])

        series = series_list[0].get("data", [])

        for item in series:
            period = item["period"]

            if period == "M13":
                continue

            value_str = item.get("value")

            if value_str in ["-", "", None]:
                continue

            try:
                value = float(value_str)
            except ValueError:
                continue

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

    return df