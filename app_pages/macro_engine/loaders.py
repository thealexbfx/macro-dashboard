from __future__ import annotations

from datetime import date
from typing import Callable

import streamlit as st

from macro_engine.models.environment import MacroEnvironmentResult
from macro_engine.pipelines.environment import (
    run_euro_macro_environment,
    run_japan_macro_environment,
    run_uk_macro_environment,
    run_usa_macro_environment,
)
from macro_engine.pipelines.history import (
    HistoricalEnvironmentRun,
    run_euro_environment_history,
    run_japan_environment_history,
    run_uk_environment_history,
    run_usa_environment_history,
)


CACHE_TTL_SECONDS = 1800
STANDARD_HISTORY_START_DATE = date(2024, 1, 1)
JAPAN_HISTORY_START_DATE = date(2015, 12, 1)


@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False)
def load_usa_macro_environment() -> MacroEnvironmentResult:
    return run_usa_macro_environment()


@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False)
def load_euro_macro_environment() -> MacroEnvironmentResult:
    return run_euro_macro_environment()


@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False)
def load_uk_macro_environment() -> MacroEnvironmentResult:
    return run_uk_macro_environment()


@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False)
def load_japan_macro_environment() -> MacroEnvironmentResult:
    return run_japan_macro_environment()


def _run_history(
    runner: Callable[..., HistoricalEnvironmentRun],
    start_date: date,
    end_date: date,
) -> HistoricalEnvironmentRun:
    return runner(
        start_date=start_date,
        end_date=end_date,
        frequency="monthly",
        continue_on_error=True,
    )


@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False)
def load_usa_environment_history(
    start_date: date,
    end_date: date,
) -> HistoricalEnvironmentRun:
    return _run_history(run_usa_environment_history, start_date, end_date)


@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False)
def load_euro_environment_history(
    start_date: date,
    end_date: date,
) -> HistoricalEnvironmentRun:
    return _run_history(run_euro_environment_history, start_date, end_date)


@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False)
def load_uk_environment_history(
    start_date: date,
    end_date: date,
) -> HistoricalEnvironmentRun:
    return _run_history(run_uk_environment_history, start_date, end_date)


@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False)
def load_japan_environment_history(
    start_date: date,
    end_date: date,
) -> HistoricalEnvironmentRun:
    return _run_history(run_japan_environment_history, start_date, end_date)
