from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime, timedelta
from threading import Lock
from time import monotonic
from typing import Literal

import numpy as np
import pandas as pd
import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from backend.app.registry.economic_indicators import EconomicIndicatorRegistry
from backend.app.registry.markets import MarketRegistry
from backend.app.services.direct_answers import PublicTimeSeriesProvider
from macro_engine.research.analytics import SeriesMetadata, align, clean, relationship

Transform = Literal["level", "percent", "yoy", "mom", "pp", "indexed", "standardized"]


@dataclass(frozen=True)
class Spec:
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
    allowed_transformations: tuple[str, ...]


def registry():
    out = {}
    for s in EconomicIndicatorRegistry().specs:
        index = s.key in ("cpi", "core_cpi", "pce", "core_pce")
        rate = s.key in ("unemployment", "fed_funds", "real_gdp_growth")
        units = {
            "CPIAUCSL": "Index 1982–1984=100",
            "CPILFESL": "Index 1982–1984=100",
            "PCEPI": "Index 2017=100",
            "PCEPILFE": "Index 2017=100",
            "PAYEMS": "Thousands of persons",
            "UNRATE": "Percent",
            "FEDFUNDS": "Percent",
            "A191RL1Q225SBEA": "Percent change, quarterly annualized",
        }[s.series_id]
        allowed = (
            ("level", "pp", "standardized")
            if rate
            else ("level", "percent", "yoy", "mom", "indexed", "standardized")
        )
        out[s.key] = Spec(
            s.key,
            {
                "cpi": "US Consumer Price Index (CPI)",
                "core_cpi": "US core Consumer Price Index",
                "pce": "US PCE price index",
                "core_pce": "US core PCE price index",
            }.get(s.key, s.name),
            s.series_id,
            s.source_label,
            s.macro_pillar,
            "United States",
            s.frequency,
            units,
            "Not seasonally adjusted"
            if s.key == "fed_funds"
            else "Seasonally adjusted annual rate"
            if s.key == "real_gdp_growth"
            else "Seasonally adjusted",
            "rate" if rate else "index" if index else "level",
            "Provider-reported quarterly annualized growth"
            if s.key == "real_gdp_growth"
            else "Original provider level",
            f"https://fred.stlouisfed.org/series/{s.series_id}",
            allowed,
        )
    for key in ("sp500", "gold", "us10y", "dxy", "wti"):
        s = MarketRegistry().get(key)
        yield_ = s.kind == "yield"
        out[key] = Spec(
            key,
            s.name + (" — continuous futures" if key in ("gold", "wti") else ""),
            s.provider_id,
            "FRED / Federal Reserve" if yield_ else "Yahoo Finance",
            "Rates"
            if yield_
            else "Commodities"
            if key in ("gold", "wti")
            else "Equities"
            if key == "sp500"
            else "FX",
            "United States" if key in ("sp500", "us10y", "dxy") else "Global",
            "daily",
            "Percent" if yield_ else s.unit,
            "Not seasonally adjusted" if yield_ else None,
            "rate" if yield_ else "signed_flow" if key == "wti" else "price",
            "Daily yield"
            if yield_
            else "Unadjusted close; continuous futures roll effects"
            if key in ("gold", "wti")
            else "Unadjusted price index close",
            f"https://fred.stlouisfed.org/series/{s.provider_id}"
            if yield_
            else f"https://finance.yahoo.com/quote/{s.provider_id}/history/",
            ("level", "pp", "standardized")
            if yield_
            else ("level", "standardized")
            if key == "wti"
            else ("level", "percent", "indexed", "standardized"),
        )
    return out


SPECS = registry()


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


class ComparisonRequest(BaseModel):
    datasets: list[str] = Field(min_length=1, max_length=4)
    transformations: dict[str, Transform] = {}
    start: date
    end: date
    alignment: Literal["native", "period_end"] = "native"
    rolling_window: int = Field(default=12, ge=3, le=252)


class ChartSeries(BaseModel):
    id: str
    name: str
    units: str
    transformation: str
    observations: list[Observation]


class ComparisonResponse(BaseModel):
    series: list[ChartSeries]
    datasets: list[Dataset]
    statistics: list[dict]
    alignment: str
    warnings: list[str]
    raw_observations: dict[str, list[Observation]]


class V2PublicProvider(PublicTimeSeriesProvider):
    def _get(self, url):
        # Public FRED date-bounded exports intermittently time out; reuse the existing
        # CSV parser with the canonical full export, then apply bounds in DataService.
        if url.startswith("https://fred.stlouisfed.org/graph/fredgraph.csv?"):
            url = url.split("&cosd=")[0]
            response = requests.get(url, timeout=self.timeout_seconds)
            response.raise_for_status()
            return response.content
        return super()._get(url)


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
            frame = clean(pd.DataFrame(rows, columns=["date", "value"]))
            frame = frame[
                (frame.date >= pd.Timestamp(start)) & (frame.date <= pd.Timestamp(end))
            ]
            valid = frame.dropna(subset=["value"])
            if valid.empty:
                raise RuntimeError("No usable observations")
            latest = valid.iloc[-1]
            previous = valid.iloc[-2] if len(valid) > 1 else None
            stale = (end - latest.date.date()).days > (
                7
                if spec.frequency == "daily"
                else 95
                if spec.frequency == "monthly"
                else 200
            )
            change = None if previous is None else float(latest.value - previous.value)
            change_units = (
                "percentage points" if spec.representation == "rate" else spec.units
            )
            if (
                spec.representation == "price"
                and previous is not None
                and previous.value > 0
            ):
                change = 100 * (float(latest.value) / float(previous.value) - 1)
                change_units = "percent"
            payload = Dataset(
                **asdict(spec),
                status="stale" if stale else "ok",
                latest_observation_date=str(latest.date.date()),
                coverage_start=str(valid.date.min().date()),
                coverage_end=str(valid.date.max().date()),
                retrieved_at=datetime.now(UTC).isoformat(),
                message="Latest completed daily observation; delayed, not a live quote."
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
                previous_observation_date=None
                if previous is None
                else str(previous.date.date()),
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
        ):
            if cached and cached[1].observations:
                stale = cached[1].model_copy(
                    update={
                        "status": "stale",
                        "message": "Provider unavailable; showing previously retrieved observations. Check retrieval timestamp.",
                    }
                )
                with self.lock:
                    self.cache[key] = (monotonic(), stale)
                return stale
            unavailable = Dataset(
                **asdict(spec),
                status="unavailable",
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


def transform(frame, spec, mode, start):
    if mode not in spec.allowed_transformations:
        raise ValueError(f"{mode} is incompatible with {spec.name}")
    s = frame.set_index("date").value
    if spec.frequency in ("monthly", "quarterly"):
        alias = "M" if spec.frequency == "monthly" else "Q"
        periods = s.index.to_period(alias)
        if periods.duplicated().any():
            raise ValueError(
                "Duplicate reference periods require explicit vintage selection"
            )
        s.index = periods
        s = s.reindex(pd.period_range(s.index.min(), s.index.max(), freq=alias))
    units = spec.units
    if mode in ("percent", "mom", "yoy"):
        if (s.dropna() <= 0).any():
            raise ValueError(
                "Percentage transformations require strictly positive observations"
            )
        lag = 12 if mode == "yoy" else 1
        s = s.pct_change(lag, fill_method=None) * 100
        units = (
            "Percent YoY"
            if mode == "yoy"
            else "Percent MoM"
            if mode == "mom"
            else "Percent per observation"
        )
    elif mode == "pp":
        s = s.diff()
        units = "Percentage points per observation"
    if isinstance(s.index, pd.PeriodIndex):
        s.index = s.index.to_timestamp()
    s = s[s.index >= pd.Timestamp(start)]
    if mode == "indexed":
        first = s.dropna()
        if first.empty or first.iloc[0] <= 0:
            raise ValueError("Positive base observation required")
        s = s / first.iloc[0] * 100
        units = "Index: first selected observation = 100"
    elif mode == "standardized":
        std = s.std()
        if pd.isna(std) or std == 0:
            raise ValueError("Standardization requires nonconstant observations")
        s = (s - s.mean()) / std
        units = "Sample standard deviations (selected period)"
    return s, units


def records(s):
    return [
        Observation(
            date=str(d.date()),
            value=None if pd.isna(v) or not np.isfinite(v) else float(v),
        )
        for d, v in s.items()
    ]


def compare(service, req):
    if len(set(req.datasets)) != len(req.datasets):
        raise ValueError("Choose distinct datasets")
    if (
        req.end < req.start
        or req.start < date(1990, 1, 1)
        or req.end >= service.today_fn()
    ):
        raise ValueError("Choose a completed date range from 1990 through yesterday")
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
        values, units = transform(frame, spec, mode, req.start)
        frames[spec.id] = values
        chart.append(
            ChartSeries(
                id=spec.id,
                name=spec.name,
                units=units,
                transformation=mode,
                observations=records(values),
            )
        )
    common_frequency = max(
        (s.frequency for s in specs), key=["daily", "monthly", "quarterly"].index
    )
    if req.alignment == "period_end" and len(specs) > 1:
        freq = max(
            (s.frequency for s in specs), key=["daily", "monthly", "quarterly"].index
        )
        alias = {"daily": "D", "monthly": "M", "quarterly": "Q"}[freq]
        for c in chart:
            s = frames[c.id]
            if freq != "daily":
                periods = s.index.to_period(alias)
                s = s.groupby(periods).tail(1)
                s.index = s.index.to_period(alias).to_timestamp(how="end").normalize()
                if len(s):
                    s = s.reindex(
                        pd.period_range(s.index.min(), s.index.max(), freq=alias)
                        .to_timestamp(how="end")
                        .normalize()
                    )
            c.observations = records(s)
            frames[c.id] = s
    statistics = []
    for i in range(len(specs)):
        for j in range(i + 1, len(specs)):
            a, b = specs[i], specs[j]

            def input_(key):
                return frames[key].rename("value").rename_axis("date").reset_index()

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
            evidence = relationship(
                pair, lags=[0], window=req.rolling_window, minimum=3
            )
            statistics.append(
                {
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
        "Latest revised observations; publication dates and historical vintages are unavailable. Reference periods are not release dates.",
        "Correlation describes the selected transformations, not causation. Level correlations may reflect shared trends.",
        "Coverage is retrieved history since 1990, not asserted full provider coverage. Missing cells are never filled.",
        "Market dates are provider daily labels; current UTC date excluded. Futures have roll effects.",
    ]
    if req.alignment == "period_end":
        warnings.append(
            "Transformations are calculated at native frequency first, then sampled at the last observation of each common lower-frequency period for charts AND statistics. No filling; final period may be incomplete."
        )
    if any(d.status == "stale" for d in data):
        warnings.append(
            "One or more series are stale; inspect source and retrieval timestamps."
        )
    return ComparisonResponse(
        series=chart,
        datasets=[d.model_copy(update={"observations": []}) for d in data],
        statistics=statistics,
        alignment=req.alignment,
        warnings=warnings,
        raw_observations=raw,
    )


service = DataService()
app = FastAPI(title="MacroLens V2 Research API", version="2.0.0")


@app.get("/api/v2/datasets", response_model=list[Dataset])
def catalogue():
    return service.catalogue()


@app.post("/api/v2/compare", response_model=ComparisonResponse)
def comparison(req: ComparisonRequest):
    try:
        return compare(service, req)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from exc


@app.get("/health")
def health():
    return {"status": "ok", "mode": "v2-real-observations"}
