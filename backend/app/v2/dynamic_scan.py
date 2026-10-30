"""Multi-horizon candidates and plain-language views; no persistence or AI calls."""

from __future__ import annotations

from copy import deepcopy
from datetime import date, timedelta
from hashlib import sha256

import numpy as np
import pandas as pd

from backend.app.v2 import discovery as old
from backend.app.v2.definitions import SPECS
from backend.app.v2.movements import movement, session_frame
from backend.app.v2.state import dumps

VERSION = "3.2.2"
MODES = {
    **old.MODES,
    "initial_claims": "percent",
    "job_openings": "mom",
    "participation": "pp",
    "hourly_earnings": "mom",
    "breakeven_5y": "pp",
    "retail_sales": "mom",
    "real_consumption": "mom",
    "consumer_sentiment": "percent",
    "housing_starts": "mom",
    "building_permits": "mom",
    "mortgage_30y": "pp",
    "industrial_production": "mom",
    "yield_curve": "pp",
    "high_yield_spread": "pp",
    "investment_grade_spread": "pp",
    "cpi_nsa": "yoy",
    "core_cpi_nsa": "yoy",
}
HORIZONS = {
    "daily": [1, 5, 21, 63, 252],
    "weekly": [1, 4, 13, 52],
    "monthly": [1, 3, 12],
    "quarterly": [1, 4],
}
PAIRS = [
    *old.PAIRS,
    (
        "cpi",
        "hourly_earnings",
        "Monthly consumer-price and nominal-wage growth; wages are not inflation-adjusted or composition-fixed.",
    ),
    (
        "job_openings",
        "payrolls",
        "Vacancy changes and payroll job creation describe different labour-market surveys and concepts.",
    ),
    (
        "participation",
        "unemployment",
        "Household labour-force participation and unemployment changes; accounting and composition links may contribute.",
    ),
    (
        "retail_sales",
        "real_consumption",
        "Nominal retail sales versus real broad consumption; price adjustment and services coverage differ.",
    ),
    (
        "housing_starts",
        "building_permits",
        "Housing starts and permits describe related construction stages, not a guaranteed pipeline forecast.",
    ),
    (
        "industrial_production",
        "payrolls",
        "Industrial output and total payroll job changes; payrolls include services beyond industry.",
    ),
    (
        "high_yield_spread",
        "sp500",
        "Credit-risk spreads and equity price returns offer market-risk context, not default or trading predictions.",
    ),
    (
        "high_yield_spread",
        "investment_grade_spread",
        "High-yield and investment-grade credit spread changes; overlapping credit drivers are not independent evidence.",
    ),
]
SHORT = {
    **{k: v.name for k, v in SPECS.items()},
    "participation": "Labour participation",
    "industrial_production": "Industrial output",
    "housing_starts": "Housing starts",
    "building_permits": "Building permits",
    "hourly_earnings": "Hourly earnings",
    "us10y": "US 10-year Treasury yield",
    "sp500": "S&P 500",
    "gold": "Gold futures",
    "dxy": "US dollar index",
    "cpi": "Consumer prices (SA)",
    "core_cpi": "Core consumer prices (SA)",
    "cpi_nsa": "Annual consumer inflation (NSA)",
    "core_cpi_nsa": "Annual core inflation (NSA)",
    "unemployment": "US unemployment",
    "payrolls": "US payroll employment",
    "fed_funds": "Monthly-average fed funds rate",
}
RELATED = {
    "us10y": ["sp500", "gold", "dxy"],
    "gold": ["dxy", "us10y"],
    "sp500": ["us10y", "high_yield_spread"],
    "dxy": ["gold", "breakeven_5y"],
    "yield_curve": ["us10y", "high_yield_spread"],
    "high_yield_spread": ["sp500", "investment_grade_spread"],
    "investment_grade_spread": ["high_yield_spread", "us10y"],
    "breakeven_5y": ["us10y", "gold"],
    "unemployment": ["payrolls", "participation"],
    "payrolls": ["unemployment", "job_openings"],
    "cpi": ["core_cpi", "hourly_earnings"],
    "core_cpi": ["cpi", "hourly_earnings"],
    "pce": ["core_pce", "real_consumption"],
    "core_pce": ["pce", "hourly_earnings"],
    "initial_claims": ["mortgage_30y"],
    "mortgage_30y": ["initial_claims"],
    "housing_starts": ["building_permits", "industrial_production"],
    "building_permits": ["housing_starts", "retail_sales"],
    "job_openings": ["payrolls", "unemployment"],
    "participation": ["unemployment", "payrolls"],
    "hourly_earnings": ["cpi", "core_cpi"],
    "retail_sales": ["real_consumption", "consumer_sentiment"],
    "real_consumption": ["retail_sales", "pce"],
    "consumer_sentiment": ["retail_sales", "unemployment"],
    "industrial_production": ["payrolls", "housing_starts"],
    "cpi_nsa": ["core_cpi_nsa", "unemployment"],
    "core_cpi_nsa": ["cpi_nsa", "hourly_earnings"],
}


def definition_hash(ids):
    return sha256(
        dumps(
            [
                {
                    k: getattr(SPECS[i], k)
                    for k in [
                        "id",
                        "provider_id",
                        "definition",
                        "units",
                        "frequency",
                        "seasonal_adjustment",
                    ]
                }
                for i in ids
            ]
        ).encode()
    ).hexdigest()


def eligible(d):
    return (
        d.status == "ok"
        and bool(d.observations)
        and d.latest_observation_date
        and not any(
            d.verification.get(k) == "Discrepancy"
            for k in ["status", "raw_status", "headline_status"]
        )
    )


def frame_for(d, cutoff):
    frame = pd.DataFrame([o.model_dump() for o in d.observations])
    frame["date"] = pd.to_datetime(frame.date)
    return frame.loc[
        frame.date <= min(pd.Timestamp(cutoff), pd.Timestamp(d.latest_observation_date))
    ].sort_values("date")


def horizon_label(spec, horizon, mode=None):
    if mode == "yoy":
        return (
            "12 months (NSA)"
            if spec.seasonal_adjustment == "Not seasonally adjusted"
            else "12 months (SA)"
        )
    return (
        ("one trading session" if horizon == 1 else f"{horizon} trading sessions")
        if spec.frequency == "daily"
        else ("one week" if horizon == 1 else f"{horizon} weeks")
        if spec.frequency == "weekly"
        else ("one month" if horizon == 1 else f"{horizon} months")
        if spec.frequency == "monthly"
        else ("one quarter" if horizon == 1 else f"{horizon} quarters")
    )


def raw_preview(d, frame, cutoff):
    quality = {}
    if d.frequency == "daily":
        frame, quality = session_frame(frame, SPECS[d.id])
    tail = frame.loc[frame.date <= pd.Timestamp(cutoff)].tail(
        36 if d.frequency == "daily" else 24
    )
    # Compact view connects only actual known values. Missing slots are explicitly counted.
    return {
        "id": d.id,
        "name": SHORT[d.id],
        "units": d.units,
        "observations": [
            {"date": str(r.date.date()), "value": float(r.value)}
            for r in tail.itertuples()
            if pd.notna(r.value)
        ],
        "missing_in_preview": int(tail.value.isna().sum()),
        "basis": "Consecutive valid source observations; gaps are not fabricated or filled in analysis.",
        "calendar_quality": {k: v for k, v in quality.items() if k != "session_dates"},
    }


def pattern_values(d, transform_fn, horizon, cutoff):
    spec = SPECS[d.id]
    start = date(max(1990, cutoff.year - 20), 1, 1)
    frame = frame_for(d, cutoff)
    if frame.empty:
        return pd.Series(dtype=float), {}, frame
    values, units, quality, grid = movement(
        frame,
        spec,
        MODES[d.id],
        start,
        transform_fn,
        horizon,
        "trading_sessions" if spec.frequency == "daily" else "native",
    )
    return (
        values,
        {
            "units": units,
            "quality": {k: v for k, v in quality.items() if k != "session_dates"},
        },
        grid,
    )


def detect_change(d, transform_fn, horizon, cutoff):
    if not eligible(d):
        return None
    spec = SPECS[d.id]
    mode = MODES[d.id]
    values, meta, grid = pattern_values(d, transform_fn, horizon, cutoff)
    nominal = (
        1260
        if spec.frequency == "daily"
        else 260
        if spec.frequency == "weekly"
        else 120
        if spec.frequency == "monthly"
        else 40
    )
    n = max(nominal, horizon * 12)
    minimum = max(
        252
        if spec.frequency == "daily"
        else 104
        if spec.frequency == "weekly"
        else 60
        if spec.frequency == "monthly"
        else 20,
        horizon * 8,
    )
    if len(values) < minimum + 1 or pd.isna(values.iloc[-1]):
        return None
    reference = values.iloc[-n - 1 : -1]
    valid = reference.dropna()
    if len(valid) < minimum or len(valid) / len(reference) < 0.9 or valid.std() < 1e-12:
        return None
    value = float(values.iloc[-1])
    z = float((value - valid.mean()) / valid.std())
    rarity = old.percentile(abs(valid), abs(value))
    alternate = valid.iloc[len(valid) // 2 :]
    if (
        rarity < 0.99
        or abs(z) < 2.5
        or old.percentile(abs(alternate), abs(value)) < 0.97
    ):
        return None
    end = str(values.index[-1].date())
    scale = (
        100
        if d.id
        in {
            "us10y",
            "breakeven_5y",
            "yield_curve",
            "high_yield_spread",
            "investment_grade_spread",
            "mortgage_30y",
        }
        else 1
    )
    unit = (
        "basis points"
        if scale == 100
        else "percentage points"
        if mode == "pp"
        else "net jobs"
        if mode == "jobs"
        else "%"
    )
    verb = "rose" if value > 0 else "fell"
    amount = abs(value) * scale
    label = horizon_label(spec, horizon, mode)
    headline = f"{SHORT[d.id]} {verb} {amount:,.2f}{'%' if unit == '%' else ' ' + unit} over {label}."
    if mode == "yoy":
        headline = f"{SHORT[d.id]} reached {value:.2f}% over 12 months."
    e = {
        "observation_date": end,
        "movement": value,
        "units": meta["units"],
        "display_movement": value * scale,
        "display_units": unit,
        "standardized_magnitude": z,
        "absolute_movement_percentile": rarity,
        "baseline": old.window_info(reference),
        "reference_mean": float(valid.mean()),
        "reference_std": float(valid.std()),
        "reference_movements": old.rows(reference),
        "alternate_absolute_percentile": old.percentile(abs(alternate), abs(value)),
        "horizon_observations": horizon,
        "horizon_label": label,
        "calendar_quality": meta["quality"],
        "method": "Same-horizon native changes vs preceding same-horizon distribution. At least 99th absolute empirical midrank, |z|≥2.5, 90% coverage and shorter-reference 97th percentile. Overlapping horizons are not independent samples or p-values.",
    }
    f = old.base_finding(
        "unusual",
        [d.id],
        {d.id: (values, meta["units"])},
        [d],
        e,
        abs(z) / 4,
        rarity,
        len(valid) / n,
        len(valid) / len(reference),
        headline,
        "A large change relative to its own same-horizon history.",
        transforms={d.id: mode},
    )
    f.update(
        methodology_version=VERSION,
        definition_hash=definition_hash([d.id]),
        horizon_observations=horizon,
        horizon_label=label,
        summary=f"Bigger in absolute terms than about {rarity * 100:.0f}% of comparable historical moves.",
        key_number=f"{value * scale:+,.2f}{'%' if unit == '%' else ' ' + unit}",
        primary_preview=raw_preview(d, grid, end),
    )
    f["configuration"].update(
        horizons={d.id: horizon},
        observation_basis="trading_sessions" if spec.frequency == "daily" else "native",
        rolling_window=60
        if spec.frequency == "daily"
        else 26
        if spec.frequency == "weekly"
        else 12,
    )
    if spec.frequency == "weekly":
        f["configuration"]["workspace"]["lead_lag"]["unit"] = "weeks"
    return f


def simple_relationship(f):
    f = deepcopy(f)
    a, b = f["datasets"]
    e = f["evidence"]
    f["headline"] = (
        f"{SHORT[a]} and {SHORT[b]} are moving differently."
        if f["type"] == "divergence"
        else f"The link between {SHORT[a]} and {SHORT[b]} has shifted."
    )
    f["summary"] = (
        "Recent changes have separated more than usual for this pair."
        if f["type"] == "divergence"
        else (
            "Their recent moves are less closely related than before."
            if abs(e["recent_correlation"]) < abs(e["baseline_correlation"])
            else "Their recent moves are more closely related than before."
        )
    )
    f.update(
        key_number="A widening gap"
        if f["type"] == "divergence"
        else (
            "A weaker link"
            if abs(e["recent_correlation"]) < abs(e["baseline_correlation"])
            else "A stronger link"
        ),
        methodology_version=VERSION,
        definition_hash=definition_hash(f["datasets"]),
        horizon_observations=1,
        horizon_label="Recent comparison window",
    )
    f["configuration"].update(
        horizons={a: 1, b: 1},
        observation_basis="trading_sessions" if f["frequency"] == "daily" else "native",
    )
    # One primary visual, with the second dataset and statistics available in evidence.
    return f


def grouped(candidates):
    groups = {}
    for f in candidates:
        direction = (
            1
            if (
                f["evidence"].get(
                    "movement", f["evidence"].get("recent_correlation", 0)
                )
                or 0
            )
            >= 0
            else -1
        )
        channel = "movement" if f["type"] == "unusual" else f["type"]
        key = (
            channel,
            tuple(sorted(f["datasets"])),
            direction if channel == "movement" else 0,
            f["definition_hash"],
        )
        groups.setdefault(key, []).append(f)
    result = []
    for key, items in groups.items():
        items.sort(key=lambda f: (-f["ranking"]["score"], f["horizon_observations"]))
        f = deepcopy(items[0])
        f["alternative_timeframes"] = [
            {
                "label": i["horizon_label"],
                "horizon_observations": i["horizon_observations"],
                "evidence": i["evidence"],
                "configuration": i["configuration"],
                "headline": i["headline"],
                "summary": i["summary"],
                "key_number": i["key_number"],
            }
            for i in items
        ]
        f["event_key"] = sha256(dumps(key).encode()).hexdigest()
        f["direction"] = key[2]
        result.append(f)
    for f in result:
        f["related_signals"] = sorted(
            r["event_key"]
            for r in result
            if r["type"] != "unusual"
            and r["event_key"] != f["event_key"]
            and set(r["datasets"]) & set(f["datasets"])
        )
    return result


def scan(data, transform_fn, as_of):
    end = as_of - timedelta(days=1)
    sources = {d.id: d for d in data}
    candidates = []
    prepared = {}
    excluded = []
    horizon_results = []
    for d in data:
        if d.id not in MODES or not eligible(d):
            excluded.append(
                {
                    "id": d.id,
                    "reason": "Unsupported change definition, stale/unavailable data or verification discrepancy.",
                }
            )
            continue
        horizons = [1] if MODES[d.id] == "yoy" else HORIZONS[d.frequency]
        for h in horizons:
            try:
                f = detect_change(d, transform_fn, h, end)
                values, meta, _ = pattern_values(d, transform_fn, h, end)
                horizon_results.append(
                    {
                        "dataset": d.id,
                        "horizon": h,
                        "label": horizon_label(SPECS[d.id], h, MODES[d.id]),
                        "date": str(values.index[-1].date()) if len(values) else None,
                        "change": float(values.iloc[-1])
                        if len(values) and pd.notna(values.iloc[-1])
                        else None,
                        "units": meta.get("units"),
                        "qualifies": bool(f),
                    }
                )
                if f:
                    candidates.append(f)
            except (ValueError, KeyError, TypeError):
                excluded.append(
                    {
                        "id": d.id,
                        "reason": "Incompatible change or insufficient calendar coverage.",
                    }
                )
                break
        try:
            values, meta, _grid = pattern_values(d, transform_fn, 1, end)
            prepared[d.id] = (values, meta["units"])
        except (ValueError, KeyError, TypeError):
            pass
    for a, b, why in PAIRS:
        if a not in prepared or b not in prepared:
            continue
        found = old.relationships(
            [a, b], prepared, [sources[a], sources[b]], why, transforms=MODES
        )
        for f in found:
            f = simple_relationship(f)
            f["primary_preview"] = raw_preview(
                sources[a], frame_for(sources[a], end), f["observation_date"]
            )
            if f["type"] == "correlation":
                paired = pd.DataFrame(f["evidence"]["paired_observations"]).set_index(
                    "date"
                )
                window = f["evidence"]["recent"]["expected"]
                rolling = (
                    paired.left.rolling(window, min_periods=int(np.ceil(window * 0.9)))
                    .corr(paired.right)
                    .tail(180 if f["frequency"] == "daily" else 72)
                )
                f["primary_preview"] = {
                    "id": a,
                    "name": "How recent changes move together",
                    "units": "Correlation (−1 to +1)",
                    "observations": [
                        {"date": str(t), "value": float(v) if pd.notna(v) else None}
                        for t, v in rolling.items()
                    ],
                    "basis": "Rolling Pearson correlation on exact paired changes, not raw levels. Null windows remain gaps.",
                }
            candidates.append(f)
    return {
        "findings": grouped(candidates),
        "horizon_results": horizon_results,
        "as_of": str(as_of),
        "generated_at": pd.Timestamp.now(tz="UTC").isoformat(),
        "methodology_version": VERSION,
        "universe": {
            "single_series": len(MODES),
            "curated_pairs": len(PAIRS),
            "exploratory_pairs": 0,
            "pairs": [{"datasets": [a, b], "rationale": why} for a, b, why in PAIRS],
            "transformations": MODES,
            "horizons": HORIZONS,
        },
        "excluded": excluded,
        "limitations": old.LIMITATIONS,
        "methodology": {
            "movements": "99th absolute same-horizon empirical midrank, |z|≥2.5, ≥90% completeness; recent-half 97th percentile. Daily 1/5/21/63/252 declared trading-session positions; weekly 1/4/13/52 weeks; monthly 1/3/12 months; quarterly 1/4 quarters. No inferential p-values.",
            "relationships": "Five original and eight additional predefined pairs; native changes, disjoint windows, coverage, influence and AR(1) screens from Phase 3.1.",
            "ranking": "Magnitude, rarity, sample, completeness, stability, quality, freshness, predeclared relevance and meaningful novelty. Priority is not confidence or economic importance.",
            "calendar": "Known closures are excluded only in the explicit trading-session basis. Actual provider observations override calendar assumptions; unknown gaps retain positions. Compact previews connect known values and disclose missing slots.",
        },
    }
