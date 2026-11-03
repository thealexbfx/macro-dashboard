"""A small immutable retrospective library, with conservative descriptive matching."""

from __future__ import annotations

import json
from datetime import date

import numpy as np
import pandas as pd

from backend.app.v2.definitions import SPECS
from backend.app.v2.discovery import effective_sample
from backend.app.v2.dynamic_scan import (
    MODES,
    definition_hash,
    detect_change,
    frame_for,
    pattern_values,
)
from backend.app.v2.movements import session_frame
from backend.app.v2.state import dumps

CURATED = [
    ("unemployment", 1, "2020-05-01", "The 2020 labour-market shock"),
    ("retail_sales", 1, "2020-05-01", "The 2020 consumer-spending disruption"),
    ("cpi", 12, "2022-07-01", "Consumer-price growth in 2022"),
    (
        "housing_starts",
        3,
        "2009-01-01",
        "Housing construction during the financial crisis",
    ),
    ("us10y", 5, "2020-03-21", "Treasury yields during March 2020"),
    ("sp500", 21, "2008-11-01", "Equities during the financial crisis"),
]
NOTE = "Curated retrospectively using latest revised observations at first capture, not historical publication vintages. Selection bias is substantial; this is a descriptive library, not a backtest or prediction."


def pattern(d, transform_fn, horizon, cutoff):
    values, meta, _ = pattern_values(d, transform_fn, horizon, cutoff)
    size = {"daily": 60, "weekly": 26, "monthly": 24, "quarterly": 16}[d.frequency]
    tail = values.tail(size)
    return {
        "observations": [
            {"date": str(t.date()), "value": None if pd.isna(v) else float(v)}
            for t, v in tail.items()
        ],
        "units": meta.get("units", ""),
        "required": size,
    }


def evidence_start(dataset, horizon, mode, first_date):
    lookback = 12 if mode == "yoy" else horizon
    first = pd.Timestamp(first_date)
    if dataset.frequency == "daily":
        # Actual declared session positions, not a guessed business-day offset.
        frame = frame_for(dataset, date.fromisoformat(dataset.latest_observation_date))
        grid, _ = session_frame(frame, SPECS[dataset.id])
        dates = pd.DatetimeIndex(grid.date)
        position = dates.searchsorted(first)
        return str(dates[max(0, position - lookback)].date())
    if dataset.frequency == "weekly":
        anchor = first.to_period("W-SUN") - lookback
        labels = {
            pd.Timestamp(o.date).to_period("W-SUN"): o.date
            for o in dataset.observations
        }
        return labels.get(anchor, str(anchor.start_time.date()))
    delta = pd.DateOffset(
        months=lookback * (3 if dataset.frequency == "quarterly" else 1)
    )
    return str((first - delta).date())


def similarity(then, now, compatible=True):
    result = {
        "matches": False,
        "compatible": compatible,
        "reason": "No sufficiently close, stable match under the declared screens.",
    }
    if not compatible:
        return {
            **result,
            "reason": "Definitions, transformation, frequency, horizon or session basis differ.",
        }
    a, b = then["observations"], now["observations"]
    n = then["required"]
    if (
        len(a) != n
        or len(b) != n
        or now["required"] != n
        or any(r["value"] is None for r in a + b)
    ):
        return {
            **result,
            "reason": "A complete equal-length window is required; missing values are not filled.",
        }
    if (
        abs(
            (date.fromisoformat(b[-1]["date"]) - date.fromisoformat(a[-1]["date"])).days
        )
        < 365
    ):
        return {**result, "reason": "Windows must be separated by at least one year."}
    # Require disjoint source evidence, including transformation lookback when supplied.
    a_start = then.get("evidence_start", a[0]["date"])
    b_start = now.get("evidence_start", b[0]["date"])
    if max(a_start, b_start) <= min(a[-1]["date"], b[-1]["date"]):
        return {**result, "reason": "Historical and current evidence windows overlap."}
    x = np.array([r["value"] for r in a])
    y = np.array([r["value"] for r in b])
    if min(x.std(), y.std()) < 1e-10:
        return {
            **result,
            "reason": "Constant or near-constant evidence cannot establish shape similarity.",
        }
    zx = (x - x.mean()) / x.std()
    zy = (y - y.mean()) / y.std()
    corr = float(np.corrcoef(x, y)[0, 1])
    rmse = float(np.sqrt(np.mean((zx - zy) ** 2)))
    ratio = float(y.std() / x.std())
    if any(
        min(x[s].std(), y[s].std()) < 1e-10
        for s in [slice(0, n // 2), slice(n // 2, n)]
    ):
        return {**result, "reason": "Each half-window must contain varying evidence."}
    halves = [
        float(np.corrcoef(x[s], y[s])[0, 1])
        for s in [slice(0, n // 2), slice(n // 2, n)]
    ]
    effective = effective_sample(pd.DataFrame({"left": x, "right": y}))
    matches = (
        corr >= 0.90
        and rmse <= 0.45
        and 0.5 <= ratio <= 2
        and x[-1] * y[-1] > 0
        and min(halves) >= 0.8
        and effective >= 8
    )
    return {
        **result,
        "matches": bool(matches),
        "shape_correlation": corr,
        "standardized_rmse": rmse,
        "amplitude_ratio": ratio,
        "half_correlations": halves,
        "effective_observations": effective,
        "then_last_change": float(x[-1]),
        "now_last_change": float(y[-1]),
        "reason": "Similar shape and magnitude passed the declared descriptive screens; this does not predict what happens next."
        if matches
        else result["reason"],
    }


class HistoricalLibrary:
    def __init__(self, store, transform_fn):
        self.store, self.transform_fn = store, transform_fn

    def seed(self, data, now):
        sources = {d.id: d for d in data}
        for key, h, cutoff, label in CURATED:
            identity = f"{key}:{h}:{cutoff}:v1"
            with self.store.connection() as db:
                if db.execute(
                    "SELECT 1 FROM library WHERE id=?", (identity,)
                ).fetchone():
                    continue
            d = sources.get(key)
            if d is None or not d.observations:
                continue
            # Historical eligibility is based on historical coverage, not today's freshness.
            observations = [o for o in d.observations if o.date <= cutoff]
            valid = [o for o in observations if o.value is not None]
            if not valid:
                continue
            historical = d.model_copy(
                update={
                    "status": "ok",
                    "observations": observations,
                    "latest_observation_date": valid[-1].date,
                    "coverage_end": valid[-1].date,
                }
            )
            finding = detect_change(
                historical, self.transform_fn, h, date.fromisoformat(cutoff)
            )
            if not finding:
                continue
            snapshot = {
                "finding": finding,
                "pattern": pattern(
                    historical, self.transform_fn, h, date.fromisoformat(cutoff)
                ),
                "definition_hash": definition_hash([key]),
                "transformation": MODES[key],
                "frequency": d.frequency,
                "horizon": h,
                "basis": finding["configuration"]["observation_basis"],
                "captured_at": now.isoformat(),
            }
            with self.store.connection(True) as db:
                db.execute(
                    "INSERT OR IGNORE INTO library VALUES (?,?,?,?,?)",
                    (identity, label, now.isoformat(), dumps(snapshot), NOTE),
                )

    def records(self, data, limit=None, offset=0):
        sources = {d.id: d for d in data}
        records = []
        with self.store.connection() as db:
            rows = db.execute(
                "SELECT * FROM library ORDER BY id"
                + (" LIMIT ? OFFSET ?" if limit is not None else ""),
                (limit, offset) if limit is not None else (),
            ).fetchall()
        for row in rows:
            snapshot = json.loads(row["snapshot"])
            f = snapshot["finding"]
            key = f["datasets"][0]
            d = sources.get(key)
            current = None
            comparison = {
                "matches": False,
                "reason": "Current compatible source data unavailable or stale.",
            }
            if d and d.status == "ok" and d.latest_observation_date:
                current = pattern(
                    d,
                    self.transform_fn,
                    snapshot["horizon"],
                    date.fromisoformat(d.latest_observation_date),
                )
                compatible = (
                    snapshot["definition_hash"] == definition_hash([key])
                    and snapshot["transformation"] == MODES[key]
                    and snapshot["frequency"] == d.frequency
                    and snapshot.get("basis")
                    == ("trading_sessions" if d.frequency == "daily" else "native")
                )
                historical_pattern = dict(snapshot["pattern"])
                for p in (historical_pattern, current):
                    if p["observations"]:
                        p["evidence_start"] = evidence_start(
                            d,
                            snapshot["horizon"],
                            snapshot["transformation"],
                            p["observations"][0]["date"],
                        )
                comparison = similarity(historical_pattern, current, compatible)
            records.append(
                {
                    "id": row["id"],
                    "label": row["label"],
                    "created_at": row["created_at"],
                    "snapshot": snapshot,
                    "notes": row["notes"],
                    "current_pattern": current,
                    "similarity": comparison,
                    "comparison_configuration": {
                        **f["configuration"],
                        "start": current["observations"][0]["date"],
                        "end": current["observations"][-1]["date"],
                    }
                    if current and current["observations"]
                    else None,
                }
            )
        return records
