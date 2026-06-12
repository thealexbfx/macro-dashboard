import datetime as dt
from pathlib import Path

import numpy as np
import pandas as pd
import requests
import streamlit as st

from config import BEA_API_KEY


CACHE_DIR = Path("data_cache") / "bea"
CACHE_TTL_DAYS = 1


def _cache_path(table_name: str, line_number: int, frequency: str) -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR / f"{table_name}_{line_number}_{frequency}.csv"


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
def get_bea_nipa_series(table_name: str, line_number: int, frequency: str = "Q"):
    """Fetch a BEA NIPA series and return date/value columns with persistent cache."""
    cache_file = _cache_path(table_name, line_number, frequency)

    if _cache_is_fresh(cache_file):
        return _read_cached_series(cache_file)

    url = "https://apps.bea.gov/api/data/"

    params = {
        "UserID": BEA_API_KEY,
        "method": "GetData",
        "DataSetName": "NIPA",
        "TableName": table_name,
        "Frequency": frequency,
        "Year": "ALL",
        "ResultFormat": "JSON",
    }

    try:
        r = requests.get(url, params=params, timeout=30)
        r.raise_for_status()

        try:
            data = r.json()
        except ValueError:
            if cache_file.exists():
                st.warning(
                    f"BEA returned a non-JSON response for {table_name} line {line_number}. "
                    "Using cached data instead."
                )
                return _read_cached_series(cache_file)

            raise RuntimeError(
                f"BEA API returned non-JSON response. Status code: {r.status_code}. "
                f"Response preview: {r.text[:300]}"
            )

        rows = data["BEAAPI"]["Results"]["Data"]

        df = pd.DataFrame(rows)
        df = df[df["LineNumber"].astype(int) == line_number].copy()

        df["value"] = (
            df["DataValue"]
            .astype(str)
            .str.replace(",", "", regex=False)
            .replace("(NA)", np.nan)
        )

        df["value"] = pd.to_numeric(df["value"], errors="coerce")

        def parse_bea_period(p):
            p = str(p)

            if "Q" in p:
                year = int(p[:4])
                quarter = int(p[-1])
                month = {1: 3, 2: 6, 3: 9, 4: 12}[quarter]
                return pd.Timestamp(year=year, month=month, day=1) + pd.offsets.MonthEnd(0)

            if "M" in p:
                year = int(p[:4])
                month = int(p[-2:])
                return pd.Timestamp(year=year, month=month, day=1) + pd.offsets.MonthEnd(0)

            year = int(p[:4])
            return pd.Timestamp(year=year, month=12, day=31)

        df["date"] = df["TimePeriod"].apply(parse_bea_period)

        df = df[["date", "value"]].dropna()
        df = df.sort_values("date").reset_index(drop=True)

        _write_cached_series(df, cache_file)

        return df

    except Exception as e:
        if cache_file.exists():
            st.warning(
                f"BEA request failed for {table_name} line {line_number}. "
                f"Using cached data instead. Error: {e}"
            )
            return _read_cached_series(cache_file)

        raise