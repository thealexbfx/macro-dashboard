"""Native charts: bounded source records, exact period arithmetic, no resampling."""

import math
from datetime import date, timedelta
from itertools import combinations
from statistics import mean, pstdev

import pandas as pd

from macro_engine.research.analytics import relationship


def ordinal(point, frequency):
    day = date.fromisoformat(point["date"][:10])
    if frequency == "monthly":
        return day.year * 12 + day.month
    if frequency == "quarterly":
        return day.year * 4 + (day.month - 1) // 3
    if frequency == "annual":
        return day.year
    return day.toordinal()


def transform_native(points, metadata, mode, horizon):
    if type(horizon) is not int or not 1 <= horizon <= 252:
        raise ValueError("Change horizon must be between 1 and 252 source periods")
    frequency, units = metadata["frequency"], metadata["units"]
    if mode not in metadata["allowed_transformations"]:
        raise ValueError("Transformation is unavailable for this native source")
    valid = [o["value"] for o in points if o["value"] is not None]
    first = next(iter(valid), None)
    center, scale = (mean(valid), pstdev(valid)) if valid else (0, 0)
    lookup = (
        {ordinal(o, frequency): o["value"] for o in points}
        if frequency not in {"event", "irregular"}
        else {}
    )
    result = []
    for point in points:
        value = point["value"]
        if value is not None:
            if mode == "indexed":
                value = value / first * 100 if first else None
            elif mode == "standardized":
                value = (value - center) / scale if scale else None
            elif mode != "level":
                position = ordinal(point, frequency)
                if mode == "yoy":
                    # Exact source reference date one year earlier, including leap-day gaps.
                    if frequency in {"daily", "weekly"}:
                        try:
                            prior_day = date.fromisoformat(point["date"][:10]).replace(
                                year=date.fromisoformat(point["date"][:10]).year - 1
                            )
                            prior = lookup.get(prior_day.toordinal())
                        except ValueError:
                            prior = None
                    else:
                        prior = lookup.get(
                            position
                            - {"monthly": 12, "quarterly": 4, "annual": 1}[frequency]
                        )
                else:
                    delta = horizon * (7 if frequency == "weekly" else 1)
                    prior = lookup.get(position - delta)
                value = (
                    value - prior
                    if mode == "pp" and prior is not None
                    else ((value / prior - 1) * 100 if prior else None)
                )
        result.append(
            {**point, "value": value if value is None or math.isfinite(value) else None}
        )
    if mode in {"percent", "mom", "yoy"}:
        units = "Percent change"
    elif mode == "pp":
        units = "Percentage points"
    elif mode == "indexed":
        units = "Index, first valid observation = 100"
    elif mode == "standardized":
        units = "Standard deviations"
    return result, units


def compare_native(catalog, req):
    if len(set(req.datasets)) != len(req.datasets) or any(
        k not in req.datasets for k in req.horizons
    ):
        raise ValueError("Choose distinct datasets and selected horizons")
    if req.end < req.start or req.end >= catalog.legacy.today_fn():
        raise ValueError("Choose a completed date range")
    metadata = [
        catalog.metadata(k) for k in req.datasets
    ]  # Authorize all before reading any data.
    if req.observation_basis != "native" or req.lead_lag and req.lead_lag.periods:
        raise ValueError(
            "Native catalog comparisons retain original source calendars; disable trading-session conversion and lead-lag shifting"
        )
    if req.alignment != "native":
        raise ValueError(
            "Native catalog charts require native alignment; no implicit frequency conversion"
        )
    series, raw, datasets, frames = [], {}, [], {}
    for d in metadata:
        key, frequency = d["id"], d["frequency"]
        mode, horizon = req.transformations.get(key, "level"), req.horizons.get(key, 1)
        # Bounded lookback for exact change baselines; never manufacture missing periods.
        extra = (
            800
            if mode == "yoy"
            else min(
                100000,
                horizon
                * {"annual": 370, "quarterly": 95, "monthly": 32, "weekly": 7}.get(
                    frequency, 1
                ),
            )
            if mode in {"percent", "mom", "pp"}
            else 0
        )
        start = max(
            date(1, 1, 1),
            req.start - timedelta(days=min(extra, (req.start - date.min).days)),
        )
        page = catalog.observations(key, start, req.end, limit=2000)
        if page["has_more"]:
            raise ValueError(
                "Range exceeds 2,000 source observations per dataset; choose a shorter range"
            )
        d = page["dataset"]
        points = d.pop("observations")
        visible = [
            o for o in points if str(req.start) <= o["date"][:10] <= str(req.end)
        ]
        # Indexed/z-score baselines use the selected range, changes may use bounded earlier evidence.
        transformed, units = transform_native(
            visible if mode in {"level", "indexed", "standardized"} else points,
            d,
            mode,
            horizon,
        )
        transformed = [
            o for o in transformed if str(req.start) <= o["date"][:10] <= str(req.end)
        ]
        raw[key] = visible
        datasets.append(d | {"observations": []})
        series.append(
            {
                "id": key,
                "name": d["name"],
                "units": units,
                "transformation": mode,
                "native_frequency": frequency,
                "observations": transformed,
                "source_dates": {o["date"]: o["date"] for o in transformed},
                "horizon_observations": horizon,
                "observation_basis": "native",
            }
        )
        if frequency not in {"event", "irregular"}:
            frames[key] = pd.Series(
                {pd.Timestamp(o["date"]): o["value"] for o in transformed}, dtype=float
            )
    statistics, scatter = [], []
    for a, b in combinations(datasets, 2):
        # Fiscal/weekly calendars and frequencies must agree before calculating statistics.
        if (
            a["frequency"] != b["frequency"]
            or a.get("native_calendar") != b.get("native_calendar")
            or a["id"] not in frames
            or b["id"] not in frames
        ):
            continue
        pair = pd.concat(
            [frames[a["id"]].rename("left"), frames[b["id"]].rename("right")], axis=1
        ).sort_index()
        evidence = relationship(pair, lags=[0], window=req.rolling_window, minimum=3)
        rolling = [
            {"date": str(k.date()), "value": None if pd.isna(v) else float(v)}
            for k, v in evidence["rolling"].items()
        ]
        statistics.append(
            {
                "left": a["id"],
                "right": b["id"],
                "transformations": [
                    req.transformations.get(a["id"], "level"),
                    req.transformations.get(b["id"], "level"),
                ],
                "frequency": a["frequency"],
                "alignment": "Exact native reference dates; no filling",
                "missing_periods": int(pair.isna().any(axis=1).sum()),
                "rolling_window": req.rolling_window,
                "rolling": rolling,
                **evidence["full_sample"],
            }
        )
        if len(datasets) == 2:
            scatter = [
                {
                    "date": str(k.date()),
                    "x": float(r.left),
                    "y": float(r.right),
                    "x_source_date": str(k.date()),
                    "y_source_date": str(k.date()),
                }
                for k, r in pair.dropna().iterrows()
            ]
    return {
        "datasets": datasets,
        "series": series,
        "raw_observations": raw,
        "statistics": statistics,
        "scatter": scatter,
        "alignment": "native",
        "lead_lag": None,
        "warnings": [
            "Native source observations; gaps remain absent or null, never interpolated or resampled. Changes require an exact prior reference period.",
            "Events are discrete instants. Statistics require matching frequency and reviewed calendar; mixed calendar charts do not imply comparable periods.",
            "Latest captured revisions, not a publication-time backtest. Correlation is not causation.",
        ],
    }
