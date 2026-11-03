"""Actionable questions using actual compatible comparisons, never implied causation."""

from __future__ import annotations

from copy import deepcopy
from datetime import date

import pandas as pd

from backend.app.v2.dynamic_scan import MODES, RELATED, SHORT, pattern_values


def suggestion(f, candidate, sources, transform_fn, origin="Research question"):
    a = f["datasets"][0]
    b = candidate
    if a == b or a not in sources or b not in sources or b not in MODES:
        return None
    da, db = sources[a], sources[b]
    if da.status != "ok" or db.status != "ok" or da.frequency != db.frequency:
        return None
    cutoff = date.fromisoformat(
        min(da.latest_observation_date, db.latest_observation_date)
    )
    h = f["horizon_observations"]
    if (MODES[a] == "yoy") != (MODES[b] == "yoy"):
        return None
    if h > 1 and (MODES[a] == "yoy" or MODES[b] == "yoy"):
        return None
    x, mx, _ = pattern_values(da, transform_fn, h, cutoff)
    y, my, _ = pattern_values(db, transform_fn, h, cutoff)
    if da.frequency in {"monthly", "quarterly"}:
        alias = "M" if da.frequency == "monthly" else "Q"
        x.index = x.index.to_period(alias).to_timestamp()
        y.index = y.index.to_period(alias).to_timestamp()
    pair = pd.concat([x.rename("left"), y.rename("right")], axis=1).sort_index()
    # Never quietly back up to a previous paired date.
    if pair.empty or pair.iloc[-1].isna().any() or len(pair.dropna()) < 12:
        return None
    recent = pair.tail(60 if da.frequency == "daily" else 24)
    if len(recent.dropna()) / len(recent) < 0.9:
        return None
    config = deepcopy(f["configuration"])
    config.update(
        datasets=[a, b],
        transformations={a: MODES[a], b: MODES[b]},
        horizons={a: h, b: h},
        start=str(recent.index[0].date()),
        end=str(recent.index[-1].date()),
    )
    config["workspace"].update(mode="separate", axes="shared", chart_type="line")
    return {
        "id": f"{a}:{b}:{h}",
        "label": f"How did {SHORT[b]} move alongside {SHORT[a]}?",
        "origin": origin,
        "context": f"{SHORT[b]}: {pair.right.iloc[-1]:+,.2f} {my['units']}. Observed over the same horizon; not a causal explanation or a claim of an unusual relationship.",
        "verified_comparison": {
            "date": str(pair.index[-1].date()),
            "left_change": float(pair.left.iloc[-1]),
            "right_change": float(pair.right.iloc[-1]),
            "paired_observations": len(recent.dropna()),
            "left_units": mx["units"],
            "right_units": my["units"],
        },
        "configuration": config,
    }


def suggestions(f, data, transform_fn, ai_candidates=()):
    sources = {d.id: d for d in data}
    out = []
    seen = set()
    candidates = [(i, "AI-suggested hypothesis") for i in ai_candidates] + [
        (i, "Research question") for i in RELATED.get(f["datasets"][0], [])
    ]
    for i, origin in candidates:
        if i in seen:
            continue
        seen.add(i)
        item = suggestion(f, i, sources, transform_fn, origin)
        if item:
            out.append(item)
        if len(out) == 2:
            break
    return out
