"""Deterministic research candidates over the audited V2 catalogue. No provider IO here."""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import UTC, date, datetime, timedelta
from hashlib import sha256
from threading import Lock
from time import monotonic

import numpy as np
import pandas as pd

from backend.app.v2.definitions import SPECS

VERSION = "3.1.0"
# Explicit selection, not a combinatorial search. NSA duplicates deliberately excluded.
MODES = {
    "cpi": "mom",
    "core_cpi": "mom",
    "pce": "mom",
    "core_pce": "mom",
    "unemployment": "pp",
    "payrolls": "jobs",
    "fed_funds": "pp",
    "real_gdp_growth": "pp",
    "us10y": "pp",
    "sp500": "percent",
    "gold": "percent",
    "dxy": "percent",
}
PAIRS = [
    (
        "cpi",
        "core_cpi",
        "Headline and core monthly SA inflation separate food/energy exposure.",
    ),
    (
        "pce",
        "core_pce",
        "Headline and core monthly PCE inflation offer related consumption-price measures.",
    ),
    (
        "unemployment",
        "payrolls",
        "Changes in household-survey unemployment and establishment-survey employment offer distinct labour-market measures.",
    ),
    (
        "gold",
        "dxy",
        "Gold futures returns and dollar-index changes examine dollar-pricing context; rolls and other drivers remain.",
    ),
    (
        "sp500",
        "us10y",
        "Equity price returns and nominal yield changes examine cross-asset co-movement, not bond returns or causal discount-rate effects.",
    ),
]
NAMES = {
    "cpi": "Monthly CPI inflation",
    "core_cpi": "Monthly core CPI inflation",
    "pce": "Monthly PCE inflation",
    "core_pce": "Monthly core PCE inflation",
    "unemployment": "Unemployment changes",
    "payrolls": "Payroll job changes",
    "fed_funds": "Monthly average policy-rate changes",
    "real_gdp_growth": "Quarterly GDP growth changes",
    "us10y": "10Y Treasury yield changes",
    "sp500": "S&P 500 price returns",
    "gold": "Gold futures price returns",
    "dxy": "Dollar-index changes",
}
LIMITATIONS = [
    "Exploratory research candidates, not trading advice, causal evidence or an established regime change.",
    "Latest revised observations; reference dates are not publication dates. No point-in-time backtest or predictive claim.",
    "Several predefined tests are examined together. No p-values or family-wise significance claims; selection and repeated-scan bias remain.",
    "Overlapping windows, autocorrelation and extreme observations limit interpretation. Stability screens reduce noise but do not remove these risks.",
]


def finite(value):
    return value is not None and np.isfinite(value)


def percentile(history, value):
    a = np.asarray(history, dtype=float)
    return float(((a < value).sum() + 0.5 * (a == value).sum()) / len(a))


def rows(frame):
    if isinstance(frame, pd.Series):
        return [
            {"date": str(d.date()), "value": float(v) if pd.notna(v) else None}
            for d, v in frame.items()
        ]
    return [
        {
            "date": str(d.date()),
            **{k: float(v) if pd.notna(v) else None for k, v in row.items()},
        }
        for d, row in frame.iterrows()
    ]


def window_info(frame):
    valid = frame.dropna()
    return {
        "start": str(frame.index[0].date()),
        "end": str(frame.index[-1].date()),
        "expected": len(frame),
        "observations": len(valid),
        "missing": len(frame) - len(valid),
        "completeness": len(valid) / len(frame),
    }


def effective_sample(frame):
    # Conservative AR(1) diagnostic, never used as an inferential p-value.
    rho = [frame[c].autocorr(1) for c in frame]
    if not all(finite(r) for r in rho):
        return 0.0
    product = max(0.0, min(0.99, rho[0] * rho[1]))
    return float(
        max(
            3,
            min(
                len(frame.dropna()), len(frame.dropna()) * (1 - product) / (1 + product)
            ),
        )
    )


def pair_frame(a, b, frequency_a, frequency_b):
    if frequency_a != frequency_b:
        raise ValueError(
            "Discovery pairs require the same native frequency; mixed-frequency scanning is not enabled."
        )
    frame = pd.concat([a.rename("left"), b.rename("right")], axis=1).sort_index()
    if frame.empty:
        return frame
    if frequency_a in ("monthly", "quarterly"):
        alias = "MS" if frequency_a == "monthly" else "QS"
        frame = frame.reindex(
            pd.date_range(frame.index.min(), frame.index.max(), freq=alias)
        )
    # Daily observed-date union preserves supplied nulls, including explicit missing sessions.
    return frame


def rank_score(magnitude, rarity, sample, completeness, stability, freshness=1.0):
    parts = {
        "magnitude": min(1.0, magnitude) * 25,
        "historical_rarity": min(1.0, rarity) * 20,
        "sample_size": min(1.0, sample) * 15,
        "completeness": completeness * 15,
        "window_stability": stability * 15,
        "freshness": freshness * 10,
    }
    return {
        "score": round(sum(parts.values()), 2),
        "components": {k: round(v, 2) for k, v in parts.items()},
        "meaning": "Research-priority score, not confidence, significance or economic importance.",
    }


def deduplicate(findings):
    ordered = sorted(findings, key=lambda f: (-f["ranking"]["score"], f["id"]))
    seen, result = set(), []
    for f in ordered:
        key = (
            ("inflation-monthly",)
            if f["type"] == "unusual"
            and f["datasets"][0] in {"cpi", "core_cpi", "pce", "core_pce"}
            else tuple(sorted(f["datasets"]))
        )
        # One card per dataset/pair, including competing relationship categories.
        if key not in seen:
            seen.add(key)
            result.append(f)
    return result[:8]


def configuration(ids, start, end, frequency):
    return {
        "datasets": ids,
        "transformations": {i: MODES[i] for i in ids},
        "start": start,
        "end": end,
        "timeframe": "Custom",
        "alignment": "native",
        "rolling_window": 60 if frequency == "daily" else 24,
        "workspace": {
            "mode": "separate",
            "chart_type": "line",
            "layout": "stacked",
            "axes": "shared",
            "axis_assignment": {},
            "hidden": [],
            "recession": False,
            "lead_lag": {
                "dataset_id": "",
                "periods": 0,
                "unit": "calendar_days" if frequency == "daily" else "months",
            },
        },
    }


def base_finding(
    kind,
    ids,
    series,
    source,
    evidence,
    magnitude,
    rarity,
    sample,
    completeness,
    headline,
    rationale,
):
    end = evidence["observation_date"]
    start = evidence["baseline"]["start"]
    frequency = SPECS[ids[0]].frequency
    identity = f"{VERSION}:{kind}:{','.join(ids)}:{end}"
    return {
        "id": sha256(identity.encode()).hexdigest()[:20],
        "type": kind,
        "label": {
            "unusual": "Unusual movement",
            "correlation": "Relationship changing",
            "divergence": "Divergence worth exploring",
        }[kind],
        "classification": "single-series anomaly"
        if len(ids) == 1
        else "curated relationship finding",
        "headline": headline,
        "datasets": ids,
        "observation_date": end,
        "evidence": evidence,
        "rationale": rationale,
        "frequency": frequency,
        "ranking": rank_score(magnitude, rarity, sample, completeness, 1),
        "configuration": configuration(ids, start, end, frequency),
        "sources": [
            {
                "id": d.id,
                "name": d.name,
                "source": d.source,
                "provider_id": d.provider_id,
                "status": d.status,
                "frequency": d.frequency,
                "units": d.units,
                "seasonal_adjustment": d.seasonal_adjustment,
                "definition": d.definition,
                "quality_warnings": d.quality_warnings,
                "input_fingerprint": sha256(
                    json.dumps(
                        [o.model_dump() for o in d.observations], sort_keys=True
                    ).encode()
                ).hexdigest(),
                "url": d.source_url,
                "latest_observation_date": d.latest_observation_date,
                "retrieved_at": d.retrieved_at,
                "publication_date": d.publication_date,
                "revision_count": d.revision_count,
                "verification": d.verification,
                "limitations": d.known_limitations,
            }
            for d in source
        ],
        "preview": [
            {
                "id": i,
                "name": NAMES[i],
                "units": series[i][1],
                "observations": rows(series[i][0].loc[:end].tail(36)),
            }
            for i in ids
        ],
        "limitations": list(
            dict.fromkeys(
                LIMITATIONS + [note for d in source for note in d.known_limitations]
            )
        ),
        "methodology_version": VERSION,
    }


def unusual(key, series, source):
    s, units = series[key]
    frequency = SPECS[key].frequency
    n, minimum = (
        (1260, 252)
        if frequency == "daily"
        else (40, 20)
        if frequency == "quarterly"
        else (120, 60)
    )
    if len(s) < minimum + 1 or pd.isna(s.iloc[-1]):
        return None
    reference = s.iloc[-n - 1 : -1]
    valid = reference.dropna()
    if len(valid) < minimum or len(valid) / len(reference) < 0.9 or valid.std() < 1e-12:
        return None
    value = float(s.iloc[-1])
    z = float((value - valid.mean()) / valid.std())
    rarity = percentile(abs(valid), abs(value))
    alternate = valid.iloc[len(valid) // 2 :]
    stable = percentile(abs(alternate), abs(value)) >= 0.95
    if rarity < 0.975 or abs(z) < 2 or not stable:
        return None
    end = str(s.index[-1].date())
    raw = source[0].observations
    latest_raw = [o.model_dump() for o in raw if o.date <= end][-2:]
    e = {
        "observation_date": end,
        "movement": value,
        "display_movement": value * 100 if key == "us10y" else value,
        "display_units": "basis points" if key == "us10y" else units,
        "units": units,
        "standardized_magnitude": z,
        "absolute_movement_percentile": rarity,
        "baseline": window_info(reference),
        "reference_mean": float(valid.mean()),
        "reference_std": float(valid.std()),
        "alternate_absolute_percentile": percentile(abs(alternate), abs(value)),
        "raw_latest_observations": latest_raw,
        "reference_movements": rows(reference),
        "method": "Latest native change vs preceding historical changes; signed z uses sample mean/std; rarity is empirical absolute-movement midrank, not a p-value.",
    }
    return base_finding(
        "unusual",
        [key],
        series,
        source,
        e,
        abs(z) / 4,
        rarity,
        len(valid) / n,
        len(valid) / len(reference),
        f"{NAMES[key]}: an unusually large {'positive' if value > 0 else 'negative'} movement.",
        "Passes the 97.5th absolute-movement percentile, |z| ≥ 2 and shorter-reference stability screen.",
    )


def relationships(ids, series, source, rationale):
    a, b = ids
    frequency = SPECS[a].frequency
    pair = pair_frame(series[a][0], series[b][0], frequency, SPECS[b].frequency)
    # Respect the most recent shared available source period; never backdate a missing terminal value.
    cutoff = min(pd.Timestamp(d.latest_observation_date) for d in source)
    pair = pair.loc[:cutoff]
    recent_n, baseline_n, alternate_n = (
        (60, 504, 90) if frequency == "daily" else (24, 120, 36)
    )
    baseline_min = 252 if frequency == "daily" else 60
    if len(pair) < baseline_min + alternate_n:
        return []
    if pair.iloc[-1].isna().any():
        return []
    recent = pair.iloc[-recent_n:]
    baseline = pair.iloc[-recent_n - baseline_n : -recent_n]
    alt_recent = pair.iloc[-alternate_n:]
    alt_base = pair.iloc[-alternate_n - baseline_n : -alternate_n]
    if any(
        window_info(w)["completeness"] < 0.9
        for w in [recent, baseline, alt_recent, alt_base]
    ):
        return []
    if len(baseline.dropna()) < baseline_min or len(recent.dropna()) < recent_n * 0.9:
        return []
    if any((w.std() < 1e-12).any() for w in [recent, baseline, alt_recent, alt_base]):
        return []
    if any(
        effective_sample(w) < minimum
        for w, minimum in [(recent, 8), (baseline, 24), (alt_recent, 8), (alt_base, 24)]
    ):
        return []

    def corr(w):
        return float(w.left.corr(w.right))

    r, b_r, alt_r, alt_b = map(corr, [recent, baseline, alt_recent, alt_base])
    if not all(finite(v) for v in [r, b_r, alt_r, alt_b]):
        return []
    delta = r - b_r
    alt_delta = alt_r - alt_b

    def influence(w):
        standardized = (w - w.mean()) / w.std()
        largest = standardized.abs().sum(axis=1, min_count=2).idxmax()
        return corr(w.drop(index=largest))

    influence_recent, influence_baseline = influence(recent), influence(baseline)
    if not all(finite(v) for v in (influence_recent, influence_baseline)):
        return []
    influence_delta = influence_recent - influence_baseline
    end = str(pair.index[-1].date())
    common = {
        "observation_date": end,
        "recent": window_info(recent),
        "baseline": window_info(baseline),
        "recent_correlation": r,
        "baseline_correlation": b_r,
        "correlation_difference": delta,
        "alternate_recent_correlation": alt_r,
        "alternate_baseline_correlation": alt_b,
        "alternate_difference": alt_delta,
        "influence_recent_correlation": influence_recent,
        "influence_baseline_correlation": influence_baseline,
        "influence_difference": influence_delta,
        "effective_recent_n": effective_sample(recent),
        "effective_baseline_n": effective_sample(baseline),
        "pair_rationale": rationale,
        "transformations": {i: MODES[i] for i in ids},
        "paired_observations": rows(pd.concat([baseline, recent])),
        "alignment": "Same native frequency, exact reference dates; no filling. Missing periods retained.",
        "method": "Non-overlapping recent/baseline Pearson correlations on native changes. Alternate windows are predeclared. Influence check removes the single greatest combined absolute standardized change in each window for diagnosis only; reported correlations retain every observation. AR(1) effective sample is a diagnostic, not an inferential test.",
    }
    result = []
    if (
        abs(delta) >= 0.5
        and delta * alt_delta > 0
        and abs(alt_delta) >= 0.3
        and finite(influence_delta)
        and delta * influence_delta > 0
        and abs(influence_delta) >= 0.3
    ):
        result.append(
            base_finding(
                "correlation",
                ids,
                series,
                source,
                common,
                abs(delta) / 1.0,
                0,
                len(baseline.dropna()) / baseline_n,
                min(
                    window_info(recent)["completeness"],
                    window_info(baseline)["completeness"],
                ),
                f"{NAMES[a]} / {NAMES[b]}: recent correlation is {'higher' if delta > 0 else 'lower'} than its baseline.",
                "Correlation differs by at least 0.50; alternate windows and an extreme-observation influence check support the same direction (at least 0.30).",
            )
        )
    if (
        abs(b_r) < 0.4
        or not finite(influence_baseline)
        or abs(influence_baseline) < 0.3
        or b_r * influence_baseline <= 0
        or pair.tail(6).isna().any().any()
    ):
        return result
    # Compare changes normalized against the disjoint historical baseline, never trending levels.
    normalized = (pair - baseline.mean()) / baseline.std()
    residual = normalized.right - np.sign(b_r) * normalized.left
    historical = (
        residual.reindex(baseline.index).rolling(3, min_periods=3).mean().dropna()
    )
    if len(historical) < baseline_min // 2 or historical.std() < 1e-12:
        return result
    latest = float(residual.tail(3).mean())
    alt = float(residual.tail(6).mean())
    z = float((latest - historical.mean()) / historical.std())
    alt_z = float((alt - historical.mean()) / historical.std())
    rarity = percentile(abs(historical), abs(latest))
    terminal = residual.tail(6)
    trimmed = terminal.drop(index=(terminal - historical.mean()).abs().idxmax())
    influence_z = float((trimmed.mean() - historical.mean()) / historical.std())
    extreme_sensitive = z * influence_z <= 0 or abs(influence_z) < 1
    if abs(z) >= 2.5 and rarity >= 0.975 and z * alt_z > 0 and abs(alt_z) >= 1:
        e = {
            **common,
            "divergence": latest,
            "divergence_z": z,
            "alternate_divergence_z": alt_z,
            "influence_divergence_z": influence_z,
            "extreme_sensitive": extreme_sensitive,
            "absolute_divergence_percentile": rarity,
            "reference_mean": float(historical.mean()),
            "reference_std": float(historical.std()),
            "baseline_means": baseline.mean().to_dict(),
            "baseline_stds": baseline.std().to_dict(),
            "direction": int(np.sign(b_r)),
            "latest_standardized_changes": rows(normalized.tail(6)),
            "historical_divergences": rows(historical),
            "method": "Three-period mean of standardized right changes minus baseline correlation sign × standardized left changes. Baseline-only means/sample stds. Compared with baseline three-period means; six-period same-direction screen. Empirical absolute midrank, not a p-value.",
        }
        result.append(
            base_finding(
                "divergence",
                ids,
                series,
                source,
                e,
                abs(z) / 4,
                rarity,
                len(baseline.dropna()) / baseline_n,
                window_info(baseline)["completeness"],
                f"{NAMES[a]} / {NAMES[b]}: recent standardized changes have diverged from baseline co-movement.",
                "Baseline |r| ≥ 0.40; three-period divergence exceeds |z| 2.5 and 97.5th empirical percentile, with a same-direction six-period check.",
            )
        )
    if result and result[-1]["type"] == "divergence" and extreme_sensitive:
        finding = result[-1]
        finding["ranking"]["components"]["window_stability"] = 7.5
        finding["ranking"]["score"] = round(finding["ranking"]["score"] - 7.5, 2)
        finding["limitations"].append(
            "Sensitive to the largest recent standardized gap: omitting it from the six-period diagnostic changes direction or reduces |z| below 1. Reported results retain all observations; inspect whether one extreme event explains the pattern."
        )
    return result


def scan(datasets, transform_fn, as_of):
    series, sources, excluded = {}, {}, []
    start = date(max(1990, as_of.year - 15), 1, 1)
    end = as_of - timedelta(days=1)
    for d in datasets:
        if d.id not in MODES:
            excluded.append(
                {
                    "id": d.id,
                    "reason": "Not in this phase's transformation universe (NSA duplicates and signed WTI excluded).",
                }
            )
            continue
        if d.status != "ok" or d.verification.get("status") == "Discrepancy":
            excluded.append(
                {
                    "id": d.id,
                    "reason": "Stale, unavailable or source discrepancy; no current candidate emitted.",
                }
            )
            continue
        try:
            if not d.observations or not d.latest_observation_date:
                raise ValueError("No dated source observations")
            frame = pd.DataFrame([o.model_dump() for o in d.observations])
            frame["date"] = pd.to_datetime(frame.date)
            frame = frame.loc[
                frame.date
                <= min(pd.Timestamp(end), pd.Timestamp(d.latest_observation_date))
            ].sort_values("date")
            if frame.empty or frame.date.duplicated().any():
                raise ValueError("Empty or duplicate dates")
            values, units = transform_fn(frame, SPECS[d.id], MODES[d.id], start)
            values = values.replace([np.inf, -np.inf], np.nan)
            if values.empty:
                raise ValueError("No transformed observations")
            series[d.id] = (values, units)
            sources[d.id] = d
        except (ValueError, KeyError, TypeError):
            excluded.append(
                {
                    "id": d.id,
                    "reason": "Invalid or incompatible transformed observations.",
                }
            )
    findings = []
    for key in series:
        f = unusual(key, series, [sources[key]])
        if f:
            findings.append(f)
    for a, b, why in PAIRS:
        if a in series and b in series:
            findings.extend(
                relationships([a, b], series, [sources[a], sources[b]], why)
            )
    return {
        "methodology_version": VERSION,
        "as_of": str(as_of),
        "generated_at": datetime.now(UTC).isoformat(),
        "findings": deduplicate(findings),
        "qualified_before_deduplication": len(findings),
        "universe": {
            "single_series": len(MODES),
            "curated_pairs": len(PAIRS),
            "exploratory_pairs": 0,
            "pairs": [{"datasets": [a, b], "rationale": why} for a, b, why in PAIRS],
            "transformations": MODES,
        },
        "excluded": excluded,
        "limitations": LIMITATIONS,
        "methodology": {
            "unusual": "≥97.5th absolute movement percentile, |z|≥2; historical min 252 daily / 60 monthly / 20 quarterly; ≥90% coverage; shorter-reference rarity ≥95%.",
            "correlation": "Recent 60 daily / 24 monthly vs preceding 504 daily / 120 monthly; alternate recent 90 / 36; |Δr|≥0.50 and alternate and extreme-observation influence checks same-direction |Δr|≥0.30. ≥90% coverage; AR(1) effective n≥8 recent / 24 baseline.",
            "divergence": "Baseline |r|≥0.40. Baseline-standardized change gap, three-period average |z|≥2.5 and absolute empirical percentile≥97.5%; six-period same-direction |z|≥1. No nulls in terminal six periods.",
            "ranking": "25 magnitude + 20 empirical rarity (0 for correlation changes, which have no rarity claim) + 15 sample + 15 completeness + 15 window stability (7.5 for extreme-sensitive divergences) + 10 freshness. Max 100; not a probability. One finding per dataset/pair, plus one monthly-inflation anomaly across CPI/PCE variants; at most eight cards.",
            "safeguards": "No AI, p-values, all-pairs search, filling, winsorization, level-correlation scans or stale candidates. Extreme observations remain visible; stability screens and autocorrelation diagnostics are conservative heuristics, not formal inference.",
        },
    }


class DiscoveryService:
    def __init__(self, data_service, transform_fn, ttl=300):
        self.data_service = data_service
        self.transform_fn = transform_fn
        self.ttl = ttl
        self.lock = Lock()
        self.cache = None

    def get(self):
        with self.lock:
            with ThreadPoolExecutor(max_workers=5) as pool:
                data = list(pool.map(self.data_service.get, SPECS))
            fingerprint = sha256(
                json.dumps(
                    [d.model_dump() for d in data], sort_keys=True, default=str
                ).encode()
            ).hexdigest()
            as_of = self.data_service.today_fn()
            key = (str(as_of), fingerprint)
            if (
                self.cache
                and self.cache[0] == key
                and monotonic() - self.cache[1] < self.ttl
            ):
                return deepcopy(self.cache[2])
            result = scan(data, self.transform_fn, as_of)
            result["snapshot_fingerprint"] = fingerprint
            result["cache"] = {
                "ttl_seconds": self.ttl,
                "note": "Discovery cache is invalidated by source payload changes; existing dataset cache remains authoritative.",
            }
            self.cache = (key, monotonic(), result)
            return deepcopy(result)
