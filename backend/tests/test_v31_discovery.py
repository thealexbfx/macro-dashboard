from copy import deepcopy
from dataclasses import asdict
from datetime import date

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from backend.app.v2.definitions import SPECS
from backend.app.v2.discovery import (
    MODES,
    PAIRS,
    DiscoveryService,
    deduplicate,
    pair_frame,
    rank_score,
    relationships,
    scan,
    unusual,
)
from backend.app.v2.main import Dataset, Observation, app, transform


def dataset(key, observations=None, **extra):
    return Dataset(
        **asdict(SPECS[key]),
        status="ok",
        message="fixture",
        observations=observations or [],
        latest_observation_date="2026-09-01",
        verification={"status": "Calculation verified"},
        **extra,
    )


def source(key, s):
    return dataset(
        key,
        [
            Observation(date=str(d.date()), value=None if pd.isna(v) else float(v))
            for d, v in s.items()
        ],
    ).model_copy(update={"latest_observation_date": str(s.index[-1].date())})


def monthly_pair(divergent=False):
    rng = np.random.default_rng(482)
    index = pd.date_range("2005-01-01", periods=240, freq="MS")
    x = rng.normal(size=240)
    y = x * 0.8 + rng.normal(scale=0.25, size=240)
    if divergent:
        y[-6:] += 8
    else:
        y[-24:] = -x[-24:] + rng.normal(scale=0.1, size=24)
    a = pd.Series(x, index=index)
    b = pd.Series(y, index=index)
    return {"cpi": (a, "Percent MoM"), "core_cpi": (b, "Percent MoM")}, [
        source("cpi", a),
        source("core_cpi", b),
    ]


def test_unusual_movement_is_change_not_trending_level():
    rng = np.random.default_rng(42)
    idx = pd.date_range("2005-01-01", periods=160, freq="MS")
    s = pd.Series(rng.normal(0, 0.2, 160), index=idx)
    s.iloc[-1] = 3.5
    f = unusual("cpi", {"cpi": (s, "Percent MoM")}, [source("cpi", s)])
    assert f and f["type"] == "unusual"
    assert f["evidence"]["movement"] == 3.5
    assert f["evidence"]["baseline"]["observations"] == 120
    assert f["configuration"]["transformations"] == {"cpi": "mom"}
    assert (
        max(o["date"] for o in f["evidence"]["reference_movements"])
        < f["observation_date"]
    )
    assert f["evidence"]["absolute_movement_percentile"] >= 0.975
    assert "level" not in MODES.values()


@pytest.mark.parametrize("case", ["short", "constant", "missing", "terminal"])
def test_unusual_rejects_inadequate_or_missing_reference(case):
    idx = pd.date_range("2005-01-01", periods=150, freq="MS")
    s = pd.Series(np.sin(np.arange(150)), index=idx)
    s.iloc[-1] = 20
    if case == "short":
        s = s.tail(10)
    if case == "constant":
        s.iloc[:-1] = 1
    if case == "missing":
        s.iloc[-100:-10] = np.nan
    if case == "terminal":
        s.iloc[-1] = np.nan
    assert unusual("cpi", {"cpi": (s, "Percent MoM")}, [source("cpi", s)]) is None


def test_changing_correlation_disjoint_baseline_and_stability():
    series, data = monthly_pair()
    found = relationships(["cpi", "core_cpi"], series, data, "fixture")
    f = next(f for f in found if f["type"] == "correlation")
    e = f["evidence"]
    assert e["recent_correlation"] < -0.9 and e["baseline_correlation"] > 0.8
    assert e["baseline"]["end"] < e["recent"]["start"]
    assert e["correlation_difference"] == pytest.approx(
        e["recent_correlation"] - e["baseline_correlation"]
    )
    assert e["effective_recent_n"] >= 8
    assert f["ranking"]["components"]["historical_rarity"] == 0


def test_divergence_has_actual_standardized_changes_and_reproducible_arithmetic():
    series, data = monthly_pair(True)
    f = next(
        f
        for f in relationships(["cpi", "core_cpi"], series, data, "fixture")
        if f["type"] == "divergence"
    )
    e = f["evidence"]
    tail = e["latest_standardized_changes"][-3:]
    expected = np.mean([r["right"] - e["direction"] * r["left"] for r in tail])
    assert e["divergence"] == pytest.approx(expected)
    assert e["divergence_z"] == pytest.approx(
        (expected - e["reference_mean"]) / e["reference_std"]
    )
    assert e["absolute_divergence_percentile"] >= 0.975


@pytest.mark.parametrize(
    "case", ["constant", "missing", "terminal", "short", "autocorrelated", "one-point"]
)
def test_relationship_safeguards(case):
    series, data = monthly_pair()
    a, b = series["cpi"][0].copy(), series["core_cpi"][0].copy()
    if case == "constant":
        b[:] = 1
    if case == "missing":
        a.iloc[-20:-5] = np.nan
    if case == "terminal":
        b.iloc[-1] = np.nan
    if case == "short":
        a = a.tail(20)
        b = b.tail(20)
    if case == "one-point":
        a.iloc[-24:] = 1
        b.iloc[-24:] = 1
        a.iloc[-1] = 10
        b.iloc[-1] = 20
    if case == "autocorrelated":
        a[:] = np.arange(len(a))
        b[:] = np.arange(len(b)) * 2
    assert (
        relationships(
            ["cpi", "core_cpi"],
            {"cpi": (a, "x"), "core_cpi": (b, "x")},
            data,
            "fixture",
        )
        == []
    )


def test_alignment_preserves_missing_months_and_refuses_implicit_mixed_frequency():
    a = pd.Series([1, 2], index=pd.to_datetime(["2020-01-01", "2020-03-01"]))
    b = pd.Series([3, 4], index=pd.to_datetime(["2020-01-01", "2020-03-01"]))
    frame = pair_frame(a, b, "monthly", "monthly")
    assert len(frame) == 3 and frame.iloc[1].isna().all()
    with pytest.raises(ValueError, match="same native frequency"):
        pair_frame(a, b, "daily", "monthly")


def test_ranking_deduplication_and_selection_order_are_deterministic():
    score = rank_score(0.8, 0.99, 1, 0.95, 1)
    assert 0 <= score["score"] <= 100
    assert sum(score["components"].values()) == pytest.approx(score["score"], abs=0.01)
    a = {
        "id": "a",
        "type": "correlation",
        "datasets": ["cpi", "core_cpi"],
        "ranking": {"score": 90},
    }
    b = {
        "id": "b",
        "type": "correlation",
        "datasets": ["core_cpi", "cpi"],
        "ranking": {"score": 80},
    }
    assert deduplicate([b, a, a]) == [a]
    assert deduplicate([a, b]) == deduplicate([b, a])


def test_stale_sources_and_discrepancies_do_not_emit_current_findings():
    d = dataset("cpi").model_copy(update={"status": "stale"})
    report = scan([d], transform, date(2026, 10, 25))
    assert report["findings"] == [] and "Stale" in report["excluded"][0]["reason"]
    d = d.model_copy(update={"status": "ok", "verification": {"status": "Discrepancy"}})
    assert scan([d], transform, date(2026, 10, 25))["findings"] == []


def test_latest_change_reconciles_with_original_transformation():
    idx = pd.date_range("2005-01-01", periods=160, freq="MS")
    rng = np.random.default_rng(22)
    moves = rng.normal(0.2, 0.03, 160)
    moves[-1] = 4
    levels = 100 * np.cumprod(1 + moves / 100)
    s = pd.Series(levels, index=idx)
    d = source("cpi", s)
    report = scan([d], transform, date(2020, 1, 1))
    f = next(f for f in report["findings"] if f["type"] == "unusual")
    assert f["evidence"]["movement"] == pytest.approx(
        (levels[-1] / levels[-2] - 1) * 100
    )
    assert f["evidence"]["raw_latest_observations"][-1]["value"] == levels[-1]


def test_curated_universe_has_no_duplicate_pairs_and_defensible_transformations():
    assert len(PAIRS) == 5 and len({tuple(sorted([a, b])) for a, b, _ in PAIRS}) == 5
    assert all(why for _, _, why in PAIRS)
    assert all(SPECS[a].frequency == SPECS[b].frequency for a, b, _ in PAIRS)
    assert all(
        mode in SPECS[key].allowed_transformations for key, mode in MODES.items()
    )
    assert "cpi_nsa" not in MODES and "wti" not in MODES


def test_discovery_cache_invalidates_revisions_and_stale_payloads():
    idx = pd.date_range("2005-01-01", periods=160, freq="MS")
    s = pd.Series(100 + np.arange(160) * 0.1, index=idx)
    s.iloc[-1] *= 1.1
    current = source("cpi", s)

    class Service:
        def today_fn(self):
            return date(2020, 1, 1)

        def get(self, key):
            return (
                current
                if key == "cpi"
                else dataset(key).model_copy(update={"status": "unavailable"})
            )

    radar = DiscoveryService(Service(), transform)
    first = radar.get()
    second = radar.get()
    assert first == second
    second["findings"].clear()
    assert radar.get() == first
    current = current.model_copy(
        update={
            "revision_count": 1,
            "observations": [
                o.model_copy(update={"value": o.value + 1})
                for o in current.observations
            ],
        }
    )
    revised = radar.get()
    assert revised["snapshot_fingerprint"] != first["snapshot_fingerprint"]
    current = current.model_copy(update={"status": "stale"})
    assert radar.get()["findings"] == []


def test_endpoint_is_additive_and_returns_empty_report_without_substitutes(monkeypatch):
    import backend.app.v2.main as api

    empty = scan([], transform, date(2026, 10, 25))
    monkeypatch.setattr(api.discovery_service, "get", lambda: deepcopy(empty))
    r = TestClient(app).get("/api/v2/discovery")
    assert r.status_code == 200 and r.json()["findings"] == []
    assert r.json()["universe"]["exploratory_pairs"] == 0


def test_inflation_anomalies_are_deduplicated_across_similar_measures():
    findings = [
        {"id": key, "type": "unusual", "datasets": [key], "ranking": {"score": score}}
        for key, score in [("cpi", 90), ("core_cpi", 91), ("pce", 85)]
    ]
    assert [f["id"] for f in deduplicate(findings)] == ["core_cpi"]


def test_influence_check_is_reported_and_uses_untrimmed_headline_correlations():
    series, data = monthly_pair()
    f = next(
        f
        for f in relationships(["cpi", "core_cpi"], series, data, "fixture")
        if f["type"] == "correlation"
    )
    e = f["evidence"]
    raw = pd.DataFrame(e["paired_observations"])
    baseline = raw[raw.date <= e["baseline"]["end"]]
    assert e["baseline_correlation"] == pytest.approx(
        baseline.left.corr(baseline.right)
    )
    assert abs(e["influence_difference"]) >= 0.3


def test_empty_dated_source_is_excluded_without_crashing():
    report = scan([dataset("cpi")], transform, date(2026, 10, 25))
    assert report["findings"] == [] and report["excluded"][0]["id"] == "cpi"
