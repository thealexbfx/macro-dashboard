import datetime as dt
from pathlib import Path
import time

import pandas as pd
import requests
import streamlit as st

from config import BLS_API_KEY
from macro_engine.cache.storage import (
    cache_exists,
    load_cache,
    save_cache,
)


CACHE_DIR = Path("data_cache") / "bls"
CACHE_TTL_DAYS = 1


def _cache_path(
    series_id: str,
    start_year: int,
) -> Path:
    CACHE_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    return CACHE_DIR / f"{series_id}_{start_year}.csv"


def _shared_cache_name(
    series_id: str,
    start_year: int,
) -> str:
    return f"bls_{series_id}_{start_year}"


def _cache_is_fresh(
    path: Path,
) -> bool:
    if not path.exists():
        return False

    modified_time = dt.datetime.fromtimestamp(
        path.stat().st_mtime
    )

    age = dt.datetime.now() - modified_time

    return age.days < CACHE_TTL_DAYS


def _read_cached_series(
    path: Path,
) -> pd.DataFrame:
    df = pd.read_csv(path)

    df["date"] = pd.to_datetime(
        df["date"]
    )

    df["value"] = pd.to_numeric(
        df["value"],
        errors="coerce",
    )

    return (
        df.dropna()
        .sort_values("date")
        .reset_index(drop=True)
    )


def _write_cached_series(
    df: pd.DataFrame,
    path: Path,
) -> None:
    df.to_csv(
        path,
        index=False,
    )


def _load_stale_series(
    *,
    series_id: str,
    start_year: int,
    cache_file: Path,
) -> pd.DataFrame | None:
    """
    Try to load the last known-good BLS series.

    Local CSV is preferred when available. If this process is running
    on Render and the local filesystem does not contain the previous
    cache, fall back to the shared Redis/Valkey cache.
    """
    if cache_file.exists():
        try:
            return _read_cached_series(
                cache_file
            )

        except Exception as exc:
            print(
                f"Could not read local stale BLS cache "
                f"for {series_id}: {exc}"
            )

    shared_name = _shared_cache_name(
        series_id,
        start_year,
    )

    if cache_exists(shared_name):
        try:
            cached = load_cache(
                shared_name
            )

            if isinstance(
                cached,
                pd.DataFrame,
            ):
                cached = cached.copy()

                cached["date"] = pd.to_datetime(
                    cached["date"]
                )

                cached["value"] = pd.to_numeric(
                    cached["value"],
                    errors="coerce",
                )

                cached = (
                    cached.dropna()
                    .sort_values("date")
                    .reset_index(drop=True)
                )

                return cached

        except Exception as exc:
            print(
                f"Could not read shared stale BLS cache "
                f"for {series_id}: {exc}"
            )

    return None


def _save_successful_series(
    *,
    df: pd.DataFrame,
    series_id: str,
    start_year: int,
    cache_file: Path,
) -> None:
    """
    Save the latest successful series to both local storage and the
    shared MacroLens cache.
    """
    _write_cached_series(
        df,
        cache_file,
    )

    shared_name = _shared_cache_name(
        series_id,
        start_year,
    )

    try:
        save_cache(
            shared_name,
            df,
        )

    except Exception as exc:
        print(
            f"Warning: Could not save shared BLS cache "
            f"for {series_id}: {exc}"
        )


@st.cache_data(
    ttl=3600,
    show_spinner=False,
)
def get_bls_series(
    series_id: str,
    start_year: int = 2000,
):
    """
    Fetch a BLS time series.

    Uses:
    1. Fresh local CSV cache
    2. BLS API with retries
    3. Stale local cache on API failure
    4. Shared Redis/Valkey cache on API failure
    """
    cache_file = _cache_path(
        series_id,
        start_year,
    )

    if _cache_is_fresh(
        cache_file
    ):
        return _read_cached_series(
            cache_file
        )

    url = (
        "https://api.bls.gov/"
        "publicAPI/v2/timeseries/data/"
    )

    current_year = dt.date.today().year

    all_rows = []

    chunk_size = (
        20
        if BLS_API_KEY
        else 10
    )

    for chunk_start in range(
        start_year,
        current_year + 1,
        chunk_size,
    ):
        chunk_end = min(
            chunk_start + chunk_size - 1,
            current_year,
        )

        payload = {
            "seriesid": [
                series_id
            ],
            "startyear": str(
                chunk_start
            ),
            "endyear": str(
                chunk_end
            ),
        }

        if BLS_API_KEY:
            payload[
                "registrationkey"
            ] = BLS_API_KEY

        last_error = None
        data = None

        for attempt in range(3):
            try:
                response = requests.post(
                    url,
                    json=payload,
                    timeout=30,
                )

                response.raise_for_status()

                data = response.json()

                last_error = None
                break

            except requests.RequestException as exc:
                last_error = exc

                print(
                    f"BLS request failed for "
                    f"{series_id} "
                    f"({chunk_start}-{chunk_end}), "
                    f"attempt {attempt + 1}/3: "
                    f"{exc}"
                )

                if attempt < 2:
                    time.sleep(
                        5 * (attempt + 1)
                    )

        if last_error is not None:
            stale = _load_stale_series(
                series_id=series_id,
                start_year=start_year,
                cache_file=cache_file,
            )

            if stale is not None:
                print(
                    f"WARNING: BLS request failed "
                    f"for {series_id} after retries. "
                    f"Using last known-good cached data."
                )

                return stale

            raise last_error

        if data is None:
            raise RuntimeError(
                f"No response data returned "
                f"for BLS series {series_id}."
            )

        if (
            data.get("status")
            != "REQUEST_SUCCEEDED"
        ):
            message = data.get(
                "message",
                ["Unknown BLS error"],
            )

            stale = _load_stale_series(
                series_id=series_id,
                start_year=start_year,
                cache_file=cache_file,
            )

            if stale is not None:
                print(
                    f"WARNING: BLS returned an error "
                    f"for {series_id}. "
                    f"Using last known-good cached data. "
                    f"Error: {message}"
                )

                return stale

            raise RuntimeError(
                f"BLS request failed "
                f"for {series_id}: {message}"
            )

        series_list = (
            data
            .get(
                "Results",
                {},
            )
            .get(
                "series",
                [],
            )
        )

        if not series_list:
            stale = _load_stale_series(
                series_id=series_id,
                start_year=start_year,
                cache_file=cache_file,
            )

            if stale is not None:
                print(
                    f"WARNING: BLS returned no series "
                    f"for {series_id}. "
                    f"Using last known-good cached data."
                )

                return stale

            return pd.DataFrame(
                columns=[
                    "date",
                    "value",
                ]
            )

        series = (
            series_list[0]
            .get(
                "data",
                [],
            )
        )

        for item in series:
            period = item["period"]

            if period == "M13":
                continue

            value_str = item.get(
                "value"
            )

            if value_str in [
                "-",
                "",
                None,
            ]:
                continue

            try:
                value = float(
                    value_str
                )

            except ValueError:
                continue

            year = int(
                item["year"]
            )

            if period.startswith(
                "M"
            ):
                month = int(
                    period.replace(
                        "M",
                        "",
                    )
                )

                date = (
                    pd.Timestamp(
                        year=year,
                        month=month,
                        day=1,
                    )
                    + pd.offsets.MonthEnd(0)
                )

            elif period.startswith(
                "Q"
            ):
                quarter = int(
                    period.replace(
                        "Q",
                        "",
                    )
                )

                month = {
                    1: 3,
                    2: 6,
                    3: 9,
                    4: 12,
                }.get(
                    quarter
                )

                if month is None:
                    continue

                date = (
                    pd.Timestamp(
                        year=year,
                        month=month,
                        day=1,
                    )
                    + pd.offsets.MonthEnd(0)
                )

            else:
                continue

            all_rows.append(
                {
                    "date": date,
                    "value": value,
                }
            )

    df = pd.DataFrame(
        all_rows
    )

    if df.empty:
        stale = _load_stale_series(
            series_id=series_id,
            start_year=start_year,
            cache_file=cache_file,
        )

        if stale is not None:
            print(
                f"WARNING: BLS returned no usable "
                f"observations for {series_id}. "
                f"Using last known-good cached data."
            )

            return stale

        return pd.DataFrame(
            columns=[
                "date",
                "value",
            ]
        )

    df = (
        df.drop_duplicates(
            subset=[
                "date"
            ]
        )
        .sort_values(
            "date"
        )
        .reset_index(
            drop=True
        )
    )

    _save_successful_series(
        df=df,
        series_id=series_id,
        start_year=start_year,
        cache_file=cache_file,
    )

    return df