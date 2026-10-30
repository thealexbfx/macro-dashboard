from __future__ import annotations

import csv
import json
import logging
import os
import secrets
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from dataclasses import asdict
from datetime import UTC, date, datetime, timedelta
from io import StringIO
from threading import Lock
from time import monotonic
from typing import Literal
from urllib.parse import quote
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import requests
from fastapi import FastAPI, Header, HTTPException, Query
from fastapi import Path as ApiPath
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from backend.app.ingestion.runner import IngestionWorker
from backend.app.registry.markets import MarketRegistry
from backend.app.services.direct_answers import PublicTimeSeriesProvider
from backend.app.v2.ai_guard import AIGuard, BudgetBlocked
from backend.app.v2.catalog_api import PublicCatalog
from backend.app.v2.definitions import SPECS, Spec
from backend.app.v2.integrity import (
    assess_freshness,
    evaluate_evidence,
    market_change,
    validate_frame,
)
from backend.app.v2.movements import movement
from backend.app.v2.native_compare import compare_native
from backend.app.v2.native_reader import NativeReader
from backend.app.v2.refresh import scheduled_service_class
from backend.app.v2.request_bounds import RequestBounds
from backend.app.v2.runtime import DynamicDiscovery
from backend.app.v2.scheduler import RefreshScheduler
from backend.app.v2.state import Store
from backend.app.v2.stored_datasets import PermissionedDataService, StoredDatasetReader
from backend.app.v2.workload import WorkloadBusy, WorkloadLimit, analytical_workload
from backend.app.v2.workspace import RecessionContext, prepare_series, source_at
from macro_engine.research.analytics import SeriesMetadata, align, clean, relationship

Transform = Literal[
    "level", "percent", "yoy", "mom", "pp", "indexed", "standardized", "jobs"
]


class Observation(BaseModel):
    date: str
    value: float | None


class Dataset(BaseModel):
    id: str
    name: str
    provider_id: str
    source: str
    category: str
    region: str
    frequency: str
    units: str
    seasonal_adjustment: str | None
    representation: str
    original_transformation: str
    source_url: str
    allowed_transformations: list[str]
    provider: str = "fred"
    definition: str = ""
    source_type: str = ""
    observation_type: str = ""
    recommended_headline_transformation: str = "level"
    headline_name: str = ""
    primary_source_url: str = ""
    freshness_expectation: str = ""
    known_limitations: list[str] = []
    headline: dict = {}
    verification: dict = {}
    quality_warnings: list[str] = []
    release_metadata: dict = {}
    provider_metadata: dict = {}
    revision_count: int = 0
    market_movement: dict = {}
    stored_provenance: dict | None = None
    status: Literal["ok", "stale", "unavailable"]
    latest_observation_date: str | None = None
    coverage_start: str | None = None
    coverage_end: str | None = None
    retrieved_at: str | None = None
    publication_date: str | None = None
    message: str
    observations: list[Observation] = []
    latest_value: float | None = None
    change: float | None = None
    change_units: str | None = None
    previous_observation_date: str | None = None


class LeadLag(BaseModel):
    dataset_id: str
    periods: int = Field(default=0, ge=-12, le=12)
    unit: Literal["months", "quarters", "calendar_days", "weeks"]


class ComparisonRequest(BaseModel):
    datasets: list[str] = Field(min_length=1, max_length=4)
    transformations: dict[str, Transform] = {}
    start: date
    end: date
    alignment: Literal["native", "period_end"] = "native"
    rolling_window: int = Field(default=12, ge=3, le=252)
    lead_lag: LeadLag | None = None
    horizons: dict[str, int] = Field(default_factory=dict)
    observation_basis: Literal["native", "trading_sessions"] = "native"


class ChartSeries(BaseModel):
    native_frequency: str = ""
    horizon_observations: int = 1
    observation_basis: str = "native"
    calendar_quality: dict = Field(default_factory=dict)
    source_dates: dict[str, str | None] = Field(default_factory=dict)
    shift_periods: int = 0
    shift_unit: str | None = None
    id: str
    name: str
    units: str
    transformation: str
    observations: list[Observation]


class ComparisonResponse(BaseModel):
    scatter: list[dict] = Field(default_factory=list)
    lead_lag: dict | None = None
    series: list[ChartSeries]
    datasets: list[Dataset]
    statistics: list[dict]
    alignment: str
    warnings: list[str]
    raw_observations: dict[str, list[Observation]]


class V2PublicProvider(PublicTimeSeriesProvider):
    def __init__(self, timeout_seconds=8, now_fn=None):
        super().__init__(timeout_seconds)
        self.now_fn = now_fn or (lambda: datetime.now(UTC))
        self._metadata = {}

    def metadata(self, key):
        return self._metadata.get(key, {})

    def _get(self, url):
        if url.startswith("https://fred.stlouisfed.org/graph/fredgraph.csv?"):
            response = requests.get(
                url.split("&cosd=")[0], timeout=self.timeout_seconds
            )
            response.raise_for_status()
            return response.content
        return super()._get(url)

    def fred_series(self, series_id, start, end):
        raw = self._get(
            f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={quote(series_id)}"
        ).decode("utf-8-sig")
        reader = csv.DictReader(StringIO(raw))
        if not reader.fieldnames or series_id not in reader.fieldnames:
            raise ValueError("FRED response series identity mismatch")
        rows = []
        for row in reader:
            label = row.get("observation_date") or row.get("DATE")
            if not label:
                raise ValueError("Missing FRED reference date")
            day = date.fromisoformat(label)
            value = row.get(series_id)
            if start <= day <= end:
                rows.append(
                    (day, None if value in ("", ". ", ".", None) else float(value))
                )
        return rows

    def market_series(self, spec, start, end):
        p1 = int(datetime.combine(start, datetime.min.time(), tzinfo=UTC).timestamp())
        p2 = int(
            datetime.combine(
                end + timedelta(days=1), datetime.min.time(), tzinfo=UTC
            ).timestamp()
        )
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{quote(spec.provider_id, safe='')}?period1={p1}&period2={p2}&interval=1d&events=history"
        raw = json.loads(self._get(url))
        chart = raw.get("chart", {})
        result = (chart.get("result") or [None])[0]
        if chart.get("error") or not result:
            raise ValueError(
                "Yahoo returned no requested instrument; no substitution allowed"
            )
        meta = result.get("meta", {})
        expected_type = "FUTURE" if spec.key in ("gold", "wti") else "INDEX"
        if (
            meta.get("symbol") != spec.provider_id
            or meta.get("instrumentType") != expected_type
            or meta.get("currency") != "USD"
        ):
            raise ValueError(
                "Yahoo symbol, instrument type or currency does not match registered definition"
            )
        try:
            tz = ZoneInfo(meta["exchangeTimezoneName"])
        except (KeyError, ValueError) as exc:
            raise ValueError("Provider-local time zone unavailable") from exc
        stamps = result.get("timestamp") or []
        closes = ((result.get("indicators") or {}).get("quote") or [{}])[0].get(
            "close"
        ) or []
        if len(stamps) != len(closes):
            raise ValueError("Yahoo timestamp/close length mismatch")
        now = self.now_fn()
        rows = []
        kept = []
        for stamp, close in zip(stamps, closes):
            instant = datetime.fromtimestamp(stamp, tz=UTC)
            day = instant.astimezone(tz).date()
            if (
                start <= day <= end
                and day < now.astimezone(tz).date()
                and instant.date() < now.date()
            ):
                rows.append((day, None if close is None else float(close)))
                kept.append(instant.isoformat())
        self._metadata[spec.key] = {
            "symbol": meta.get("symbol"),
            "exchange": meta.get("fullExchangeName"),
            "instrument_type": meta.get("instrumentType"),
            "currency": meta.get("currency"),
            "timezone": meta.get("exchangeTimezoneName"),
            "contract_label": meta.get("shortName"),
            "regular_quote_timestamp": datetime.fromtimestamp(
                meta["regularMarketTime"], tz=UTC
            ).isoformat()
            if meta.get("regularMarketTime")
            else None,
            "regular_quote_value": meta.get("regularMarketPrice"),
            "last_completed_bar_timestamp": kept[-1] if kept else None,
            "close_field": "indicators.quote.close (unadjusted); no adjclose or settlement substitution",
            "date_convention": "Provider-local daily bar label, not an exchange settlement timestamp",
        }
        return rows


class DataService:
    def __init__(self, provider=None, today_fn=None, ttl=900):
        self.provider = provider or V2PublicProvider(timeout_seconds=8)
        self.today_fn = today_fn or (lambda: datetime.now(UTC).date())
        self.ttl = ttl
        self.cache = {}
        self.lock = Lock()

    def get(self, key):
        if key not in SPECS:
            raise ValueError("Unknown dataset ID")
        with self.lock:
            cached = self.cache.get(key)
            if cached and monotonic() - cached[0] < (
                self.ttl if cached[1].status == "ok" else min(self.ttl, 60)
            ):
                return cached[1]
        spec = SPECS[key]
        end = self.today_fn() - timedelta(days=1)
        try:
            # Requested window is reported as retrieved coverage, never full provider history.
            start = date(1990, 1, 1)
            rows = (
                self.provider.fred_series(spec.provider_id, start, end)
                if spec.source.startswith("FRED")
                else self.provider.market_series(MarketRegistry().get(key), start, end)
            )
            frame, quality_warnings = validate_frame(rows, spec)
            frame = frame[
                (frame.date >= pd.Timestamp(start)) & (frame.date <= pd.Timestamp(end))
            ]
            valid = frame.dropna(subset=["value"])
            if valid.empty:
                raise RuntimeError("No usable observations")
            latest = valid.iloc[-1]
            stale, freshness_reason, release = assess_freshness(
                spec, latest.date.date(), self.today_fn()
            )
            change, change_units, previous_date, movement = market_change(frame, spec)
            headline = make_headline(frame, spec, str(latest.date.date()))
            verification = evaluate_evidence(
                spec, str(latest.date.date()), float(latest.value), headline
            )
            previous_frame = (
                {o.date: o.value for o in cached[1].observations} if cached else {}
            )
            revisions = sum(
                1
                for r in valid.itertuples()
                if str(r.date.date()) in previous_frame
                and previous_frame[str(r.date.date())] is not None
                and abs(float(r.value) - previous_frame[str(r.date.date())]) > 1e-9
            )
            if revisions:
                quality_warnings.append(
                    f"{revisions} previously retrieved observations changed; revised history, not an immutable vintage."
                )
            if verification.get("status") == "Discrepancy":
                quality_warnings.append(
                    "Latest value differs from the dated audit reference; inspect revision/source reconciliation."
                )
            payload = Dataset(
                **asdict(spec),
                status="stale" if stale else "ok",
                latest_observation_date=str(latest.date.date()),
                quality_warnings=quality_warnings,
                headline=headline,
                market_movement=movement,
                verification=verification,
                release_metadata={**release, "freshness_assessment": freshness_reason},
                provider_metadata=self.provider.metadata(spec.id)
                if hasattr(self.provider, "metadata")
                else {},
                revision_count=revisions,
                publication_date=release.get("release_date"),
                coverage_start=str(valid.date.min().date()),
                coverage_end=str(valid.date.max().date()),
                retrieved_at=datetime.now(UTC).isoformat(),
                message="Historical daily close; delayed, not a live quote or independently verified settlement."
                if spec.frequency == "daily"
                else "Dates are economic reference periods, not publication dates; latest revised values.",
                observations=[
                    Observation(
                        date=str(r.date.date()),
                        value=None if pd.isna(r.value) else float(r.value),
                    )
                    for r in frame.itertuples()
                ],
                latest_value=float(latest.value),
                change=change,
                change_units=change_units,
                previous_observation_date=previous_date,
            )
            with self.lock:
                self.cache[key] = (monotonic(), payload)
            return payload
        except (
            requests.RequestException,
            ValueError,
            RuntimeError,
            KeyError,
            TypeError,
        ) as exc:
            reason = (
                str(exc)
                if isinstance(exc, ValueError)
                else "Provider unavailable; no substitute instrument used."
            )
            if cached and cached[1].observations:
                stale = cached[1].model_copy(
                    update={
                        "status": "stale",
                        "quality_warnings": [reason],
                        "message": "Provider unavailable; showing previously retrieved observations. Check retrieval timestamp.",
                    }
                )
                with self.lock:
                    self.cache[key] = (monotonic(), stale)
                return stale
            unavailable = Dataset(
                **asdict(spec),
                status="unavailable",
                quality_warnings=[reason],
                verification={
                    "status": "Unavailable",
                    "audit_checked_at": "2026-10-24",
                },
                message="Provider unavailable or returned invalid observations. Retry later; no synthetic replacement.",
            )
            with self.lock:
                self.cache[key] = (monotonic(), unavailable)
            return unavailable

    def catalogue(self):
        with ThreadPoolExecutor(max_workers=5) as pool:
            return [
                d.model_copy(update={"observations": d.observations[-40:]})
                for d in pool.map(self.get, SPECS)
            ]


def transform(frame, spec: Spec, mode, start):
    if mode not in spec.allowed_transformations:
        raise ValueError(f"{mode} is incompatible with {spec.name}")
    units = {
        "percent": "Percent per observation",
        "mom": "Percent MoM",
        "yoy": "Percent YoY",
        "jobs": "Jobs per month",
        "pp": "Percentage points per observation",
        "indexed": "Index: first selected observation = 100",
        "standardized": "Sample standard deviations (selected period)",
    }.get(mode, spec.units)
    if frame.empty:
        return pd.Series(dtype=float, index=pd.DatetimeIndex([])), units
    s = frame.set_index("date").value
    weekly_sources = {}
    if spec.frequency == "weekly":
        periods = s.index.to_period("W-SUN")
        if periods.duplicated().any():
            raise ValueError(
                "Duplicate weekly periods require explicit vintage selection"
            )
        weekly_sources = dict(zip(periods, s.index))
        s.index = periods
        s = s.reindex(pd.period_range(periods.min(), periods.max(), freq="W-SUN"))
    if spec.frequency in ("monthly", "quarterly"):
        alias = "M" if spec.frequency == "monthly" else "Q"
        periods = s.index.to_period(alias)
        if periods.duplicated().any():
            raise ValueError(
                "Duplicate reference periods require explicit vintage selection"
            )
        s.index = periods
        s = s.reindex(pd.period_range(s.index.min(), s.index.max(), freq=alias))
    if mode in ("percent", "mom", "yoy"):
        if (s.dropna() <= 0).any():
            raise ValueError(
                "Percentage transformations require strictly positive observations"
            )
        lag = 12 if mode == "yoy" else 1
        s = s.pct_change(lag, fill_method=None) * 100
    elif mode == "jobs":
        s = s.diff() * 1000
    elif mode == "pp":
        s = s.diff()
    if isinstance(s.index, pd.PeriodIndex):
        s.index = (
            pd.DatetimeIndex(
                [weekly_sources.get(p, p.end_time.normalize()) for p in s.index]
            )
            if spec.frequency == "weekly"
            else s.index.to_timestamp()
        )
    s = s[s.index >= pd.Timestamp(start)]
    if s.dropna().empty:
        return s, units
    if mode == "indexed":
        first = s.dropna()
        if first.iloc[0] <= 0:
            raise ValueError("Positive base observation required")
        s = s / first.iloc[0] * 100
    elif mode == "standardized":
        std = s.std()
        if pd.isna(std) or std == 0:
            raise ValueError("Standardization requires nonconstant observations")
        s = (s - s.mean()) / std
    return s, units


def make_headline(frame, spec, reference):
    mode = spec.recommended_headline_transformation
    values, units = transform(frame, spec, mode, date(1990, 1, 1))
    at = pd.Timestamp(reference)
    value = values.get(at)
    return {
        "name": spec.headline_name,
        "transformation": mode,
        "value": None if value is None or pd.isna(value) else float(value),
        "units": units,
        "reference_period": reference,
        "seasonal_adjustment": spec.seasonal_adjustment,
        "source_dataset_id": spec.id,
        "calculation_status": "Calculation verified"
        if value is not None and pd.notna(value)
        else "Unavailable",
    }


def records(s):
    return [
        Observation(
            date=str(d.date()),
            value=None if pd.isna(v) or not np.isfinite(v) else float(v),
        )
        for d, v in s.items()
    ]


def compare(service, req):
    if any(k not in req.datasets for k in req.horizons):
        raise ValueError("Horizon must refer to a selected dataset")
    if len(set(req.datasets)) != len(req.datasets):
        raise ValueError("Choose distinct datasets")
    if (
        req.end < req.start
        or req.start < date(1990, 1, 1)
        or req.end >= service.today_fn()
    ):
        raise ValueError("Choose a completed date range from 1990 through yesterday")
    if hasattr(service, "resolve_spec"):
        specs = [service.resolve_spec(k) for k in req.datasets]
    else:
        if any(k not in SPECS for k in req.datasets):
            raise ValueError("Unknown dataset ID")
        specs = [SPECS[k] for k in req.datasets]
    if len({s.frequency for s in specs}) > 1 and req.alignment == "native":
        raise ValueError("Mixed frequencies require explicit period-end alignment")
    with ThreadPoolExecutor(max_workers=4) as pool:
        data = list(pool.map(service.get, req.datasets))
    if any(d.status == "unavailable" for d in data):
        raise RuntimeError("One or more selected providers are unavailable")
    frames = {}
    chart = []
    raw = {}
    for d, spec in zip(data, specs):
        frame = clean(pd.DataFrame([o.model_dump() for o in d.observations]))
        frame = frame[frame.date <= pd.Timestamp(req.end)]
        raw[spec.id] = [
            o for o in d.observations if str(req.start) <= o.date <= str(req.end)
        ]
        mode = req.transformations.get(spec.id, "level")
        values, units, quality, _ = movement(
            frame,
            spec,
            mode,
            req.start,
            transform,
            req.horizons.get(spec.id, 1),
            req.observation_basis,
        )
        frames[spec.id] = values
        chart.append(
            ChartSeries(
                id=spec.id,
                native_frequency=spec.frequency,
                horizon_observations=req.horizons.get(spec.id, 1),
                observation_basis=req.observation_basis,
                calendar_quality={
                    k: v for k, v in quality.items() if k != "session_dates"
                },
                name=spec.name,
                units=units,
                transformation=mode,
                observations=records(values),
            )
        )
    common_frequency = max(
        (s.frequency for s in specs),
        key=["daily", "weekly", "monthly", "quarterly"].index,
    )
    shift = req.lead_lag
    if shift and shift.periods:
        if len(specs) < 2 or shift.dataset_id not in req.datasets:
            raise ValueError(
                "Lead-lag requires at least two datasets and a selected shifted series"
            )
        expected_unit = {
            "weekly": "weeks",
            "monthly": "months",
            "quarterly": "quarters",
            "daily": "calendar_days",
        }[common_frequency]
        if shift.unit != expected_unit:
            raise ValueError(
                "Lead-lag units must match the common comparison frequency"
            )
    for c in chart:
        values, sources = prepare_series(
            frames[c.id],
            common_frequency,
            req.alignment,
            req.start,
            req.end,
            shift.periods if shift and c.id == shift.dataset_id else 0,
            source_labels=[
                pd.Timestamp(o.date)
                for o in data[req.datasets.index(c.id)].observations
            ],
        )
        frames[c.id] = values
        c.observations = records(values)
        c.source_dates = sources
        if shift and shift.periods and c.id == shift.dataset_id:
            c.shift_periods, c.shift_unit = shift.periods, shift.unit
    scatter = []
    statistics = []
    for i in range(len(specs)):
        for j in range(i + 1, len(specs)):
            a, b = specs[i], specs[j]

            def input_(key):
                return frames[key].rename("value").rename_axis("date").reset_index()

            if frames[a.id].empty or frames[b.id].empty:
                pair = pd.DataFrame(
                    columns=["left", "right"], index=pd.DatetimeIndex([]), dtype=float
                )
                details = {
                    "frequency": common_frequency,
                    "alignment": "No overlapping coverage; no filling",
                    "missing_periods": 0,
                }
            elif common_frequency == "weekly":
                pair = pd.concat(
                    [frames[a.id].rename("left"), frames[b.id].rename("right")], axis=1
                ).sort_index()
                pair = pair.loc[
                    max(frames[a.id].index.min(), frames[b.id].index.min()) : min(
                        frames[a.id].index.max(), frames[b.id].index.max()
                    )
                ]
                details = {
                    "frequency": "weekly",
                    "alignment": "Exact native source dates; use explicit period-end for matching calendar weeks"
                    if req.alignment == "native"
                    else "Explicit common Sunday-ending week; actual source labels retained",
                    "missing_periods": int(pair.isna().any(axis=1).sum()),
                }
            else:
                pair, details = align(
                    input_(a.id),
                    input_(b.id),
                    SeriesMetadata(
                        frequency=common_frequency
                        if req.alignment == "period_end"
                        else a.frequency
                    ),
                    SeriesMetadata(
                        frequency=common_frequency
                        if req.alignment == "period_end"
                        else b.frequency
                    ),
                )
            if req.alignment == "native" and common_frequency in (
                "monthly",
                "quarterly",
            ):
                alias = "M" if common_frequency == "monthly" else "Q"
                pair.index = pair.index.to_period(alias).to_timestamp()
                details["alignment"] = "native reference-period labels; no filling"
            pair = pair.loc[
                (pair.index >= pd.Timestamp(req.start))
                & (pair.index <= pd.Timestamp(req.end))
            ]
            evidence = relationship(
                pair, lags=[0], window=req.rolling_window, minimum=3
            )
            if len(specs) == 2:
                for label, row in pair.dropna().iterrows():
                    scatter.append(
                        {
                            "date": str(label.date()),
                            "x": float(row.left),
                            "y": float(row.right),
                            "x_source_date": source_at(
                                chart[i].source_dates, label, common_frequency
                            ),
                            "y_source_date": source_at(
                                chart[j].source_dates, label, common_frequency
                            ),
                        }
                    )
            statistics.append(
                {
                    "lead_lag": shift.model_dump() if shift and shift.periods else None,
                    "left": a.id,
                    "right": b.id,
                    "transformations": [
                        req.transformations.get(a.id, "level"),
                        req.transformations.get(b.id, "level"),
                    ],
                    "frequency": details["frequency"],
                    "alignment": details["alignment"],
                    "missing_periods": details["missing_periods"],
                    "rolling_window": req.rolling_window,
                    "rolling": records(evidence["rolling"]),
                    **evidence["full_sample"],
                }
            )
    warnings = [
        "Latest revised observations; full historical publication dates and vintage archives are unavailable. Reference periods are not release dates.",
        "Correlation describes the selected transformations, not causation. Level correlations may reflect shared trends.",
        "Coverage is retrieved history since 1990, not asserted full provider coverage. Missing cells are never filled.",
        "Market dates are provider daily labels; current UTC date excluded. Futures have roll effects.",
    ]
    if req.alignment == "period_end":
        warnings.append(
            "Transformations are calculated at native frequency first, then sampled at the last observation of each common lower-frequency period for charts AND statistics. No filling; final period may be incomplete."
        )
    if shift and shift.periods:
        warnings.append(
            f"Analytical comparison: {shift.dataset_id} labels shifted {shift.periods:+d} {shift.unit}. "
            "Positive shifts compare that series with other series later; negative shifts compare it with earlier observations. "
            "Original source dates are retained; both source and comparison labels are restricted to the selected window. "
            "Exploratory retrospective correlation is not predictive evidence or a publication-time backtest."
        )
    if any(d.status == "stale" for d in data):
        warnings.append(
            "One or more series are stale; inspect source and retrieval timestamps."
        )
    return ComparisonResponse(
        scatter=scatter,
        lead_lag=shift.model_dump() if shift and shift.periods else None,
        series=chart,
        datasets=[d.model_copy(update={"observations": []}) for d in data],
        statistics=statistics,
        alignment=req.alignment,
        warnings=warnings,
        raw_observations=raw,
    )


state_store = Store()
legacy_service = scheduled_service_class(DataService, Dataset)(state_store)
service = PermissionedDataService(
    legacy_service,
    StoredDatasetReader(state_store.path, Dataset, today_fn=legacy_service.today_fn),
    lambda: SPECS,
)
context_service = RecessionContext(service.provider, service.today_fn)
public_catalog = PublicCatalog(
    legacy_service, service.reader, NativeReader(state_store.path)
)
# Short bounded reads do not queue behind a full Discovery refresh/comparison.
# Heavy analysis keeps its existing one-worker cap; HTTP requests remain bounded.
catalog_reads = WorkloadLimit(2)


@asynccontextmanager
async def lifespan(app):
    try:
        state_store.probe()
    except (sqlite3.Error, OSError) as exc:
        logging.getLogger(__name__).warning(
            "V2 database readiness failed (%s); existing state was not reset.",
            type(exc).__name__,
        )
    ingestion_worker.start()
    refresh_scheduler.start()
    try:
        yield
    finally:
        refresh_scheduler.stop()
        ingestion_worker.stop()


app = FastAPI(title="MacroLens V2 Research API", version="3.2.0", lifespan=lifespan)
app.add_middleware(RequestBounds)


@app.exception_handler(WorkloadBusy)
async def research_busy(request, exc):
    return JSONResponse(
        {"detail": "Research worker is busy; retry shortly."},
        status_code=503,
        headers={"Retry-After": "2", "Cache-Control": "no-store"},
    )


@app.get("/ready")
def readiness():
    try:
        state_store.probe()
        database_ok = True
    except (sqlite3.Error, OSError):
        database_ok = False
    status = refresh_scheduler.status()
    ok = database_ok and status["ready"]
    return JSONResponse(
        {
            "status": "ready" if ok else "not_ready",
            "database": database_ok,
            "scheduler": status,
        },
        status_code=200 if ok else 503,
        headers={"Cache-Control": "no-store"},
    )


@app.get("/api/v2/context/recessions")
def recession_context(start: date, end: date):
    try:
        with analytical_workload.enter():
            return context_service.get(start, end)
    except WorkloadBusy:
        raise
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from exc


@app.get("/api/v2/datasets", response_model=list[Dataset])
def catalogue():
    with analytical_workload.enter():
        return service.catalogue()


class CatalogSearch(BaseModel):
    query: str = Field(default="", max_length=200)
    region: str = Field(default="", max_length=100)
    category: str = Field(default="", max_length=100)
    provider: str = Field(default="", max_length=100)
    frequency: str = Field(default="", max_length=40)
    offset: int = Field(default=0, ge=0, le=100000)
    limit: int = Field(default=20, ge=1, le=100)
    ids: list[str] | None = Field(default=None, max_length=400)


@app.post("/api/v2/catalog/search")
def catalog_search(req: CatalogSearch):
    with catalog_reads.enter():
        return public_catalog.page(**req.model_dump())


@app.get("/api/v2/catalog")
def catalog_page(
    query: str = Query("", max_length=200),
    region: str = Query("", max_length=100),
    category: str = Query("", max_length=100),
    provider: str = Query("", max_length=100),
    frequency: str = Query("", max_length=40),
    offset: int = Query(0, ge=0, le=100000),
    limit: int = Query(20, ge=1, le=100),
):
    with catalog_reads.enter():
        return public_catalog.page(
            query=query,
            region=region,
            category=category,
            provider=provider,
            frequency=frequency,
            offset=offset,
            limit=limit,
        )


@app.get("/api/v2/catalog/{key}")
def catalog_metadata(key: str = ApiPath(max_length=128)):
    try:
        with catalog_reads.enter():
            return public_catalog.metadata(key)
    except ValueError as exc:
        raise HTTPException(404, "Dataset unavailable") from exc


@app.get("/api/v2/observations/{key}")
def observation_range(
    key: str = ApiPath(max_length=128),
    start: date | None = None,
    end: date | None = None,
    limit: int = Query(1000, ge=1, le=1000),
    offset: int = Query(0, ge=0, le=100000),
    preview: bool = False,
):
    try:
        with catalog_reads.enter():
            public_catalog.metadata(key)
            return public_catalog.observations(
                key,
                start
                or (
                    date.min
                    if key in public_catalog.native.publications
                    else date(1990, 1, 1)
                ),
                end or (public_catalog.legacy.today_fn() - timedelta(days=1)),
                limit=min(limit, 40) if preview else limit,
                offset=offset,
                preview=preview,
            )
    except ValueError as exc:
        if str(exc) == "Unknown dataset ID":
            raise HTTPException(404, "Dataset unavailable") from exc
        raise HTTPException(422, str(exc)) from exc
    except WorkloadBusy:
        raise
    except RuntimeError as exc:
        raise HTTPException(
            503, "Source unavailable; retry shortly", headers={"Retry-After": "2"}
        ) from exc


@app.post("/api/v2/compare", response_model=ComparisonResponse)
def comparison(req: ComparisonRequest):
    try:
        with analytical_workload.enter():
            if any(k in public_catalog.native.publications for k in req.datasets):
                return JSONResponse(
                    compare_native(
                        public_catalog, req, lambda single: compare(service, single)
                    )
                )
            return compare(service, req)
    except WorkloadBusy:
        raise
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from exc


@app.get("/health")
def health():
    return {"status": "ok", "mode": "v2-real-observations"}


# Additive V2 Discovery endpoint; older comparison requests retain native defaults.
discovery_service = DynamicDiscovery(service, transform, state_store)
ai_guard = AIGuard(state_store)
# Disabled by default, independently of AI. Only the three internal pilot datasets.
ingestion_worker = IngestionWorker(
    state_store, enabled=os.getenv("MACROLENS_INGESTION_ENABLED", "0") == "1"
)


def background_refresh():
    # Dispatch before a potentially slow cold Discovery scan. Failure of the
    # optional worker must never prevent the established research refresh.
    try:
        ingestion_worker.tick()
    except Exception as exc:  # noqa: BLE001 -- optional worker admission boundary
        logging.getLogger(__name__).warning(
            "Ingestion dispatch failed (%s); Discovery continues.", type(exc).__name__
        )
    return discovery_service.get(force_check=True)


refresh_scheduler = RefreshScheduler(background_refresh)


@app.get("/api/v2/discovery")
def discovery_radar():
    try:
        return discovery_service.get()
    except WorkloadBusy:
        raise
    except (sqlite3.Error, OSError, RuntimeError) as exc:
        raise HTTPException(
            503,
            "Discovery state or source scan unavailable. Persisted records were not reset; inspect backend logs.",
        ) from exc


@app.post("/api/v2/discovery/refresh")
def refresh_discoveries():
    try:
        return discovery_service.manual()
    except WorkloadBusy:
        raise
    except (sqlite3.Error, OSError, RuntimeError) as exc:
        raise HTTPException(
            503, "Discovery refresh unavailable; persisted records retained."
        ) from exc


def require_admin(authorization):
    token = os.getenv("MACROLENS_ADMIN_TOKEN", "")
    if (
        not token
        or not authorization
        or not secrets.compare_digest(authorization, "Bearer " + token)
    ):
        raise HTTPException(403, "Admin access required.")


@app.get("/api/v2/discovery/admin/usage")
def ai_usage(authorization: str | None = Header(default=None)):
    require_admin(authorization)
    return ai_guard.usage()


@app.post("/api/v2/discovery/admin/generate")
def ai_generate(authorization: str | None = Header(default=None)):
    require_admin(authorization)
    try:
        return ai_guard.generate(discovery_service.get()["findings"])
    except BudgetBlocked as exc:
        raise HTTPException(409, str(exc)) from exc


def discovery_read(operation, *args, **kwargs):
    try:
        return operation(*args, **kwargs)
    except WorkloadBusy:
        raise
    except (sqlite3.Error, OSError, RuntimeError) as exc:
        raise HTTPException(
            503, "Discovery state temporarily unavailable; evidence retained."
        ) from exc


@app.get("/api/v2/discovery/stories")
def discovery_stories(
    state: Literal["archived", "following"] = "archived",
    kind: Literal["all", "unusual", "correlation", "divergence"] = "all",
    limit: int = Query(default=20, ge=1, le=20),
    offset: int = Query(default=0, ge=0, le=100000),
):
    return discovery_read(
        discovery_service.summaries,
        archived=state == "archived",
        limit=limit,
        offset=offset,
        kind=kind,
    )


@app.get("/api/v2/discovery/stories/{story_id}")
def discovery_story(story_id: str = ApiPath(max_length=128)):
    finding = discovery_read(discovery_service.story, story_id)
    if finding is None:
        raise HTTPException(404, "Discovery not found.")
    return finding


@app.get("/api/v2/discovery/historical")
def historical_discoveries(
    limit: int = Query(default=6, ge=1, le=6),
    offset: int = Query(default=0, ge=0, le=100000),
):
    return discovery_read(discovery_service.historical_page, limit=limit, offset=offset)


@app.get("/api/v2/discovery/admin/diagnostics")
def discovery_diagnostics(authorization: str | None = Header(default=None)):
    require_admin(authorization)
    return {
        "scheduler": refresh_scheduler.status(),
        "source_checks": service.freshness_summary(),
        "ingestion": ingestion_worker.status(),
        "limits": {
            "analytical_operations_per_process": 1,
            "api_inflight_per_process": 8,
            "request_bytes": 65536,
        },
        "discovery_cache_seconds": discovery_service.cache_seconds,
    }
