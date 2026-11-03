"""Phase 3.2 fixtures: no live sources and no paid AI requests."""

import json
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from dataclasses import asdict
from datetime import UTC, date, datetime, timedelta

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from backend.app.v2.ai_guard import (
    INPUT_BOUND,
    MODEL,
    OUTPUT_BOUND,
    AIGuard,
    BudgetBlocked,
)
from backend.app.v2.definitions import SPECS
from backend.app.v2.dynamic_scan import detect_change, grouped, raw_preview
from backend.app.v2.followups import suggestions
from backend.app.v2.history import HistoricalLibrary, similarity
from backend.app.v2.main import (
    ComparisonRequest,
    DataService,
    Dataset,
    Observation,
    app,
    compare,
    transform,
)
from backend.app.v2.memory import DiscoveryMemory, material_change
from backend.app.v2.movements import movement, session_frame
from backend.app.v2.refresh import scheduled_service_class
from backend.app.v2.runtime import ai_cache_key
from backend.app.v2.state import Store

NOW = datetime(2026, 10, 25, 12, tzinfo=UTC)


def source(key, s):
    return Dataset(
        **asdict(SPECS[key]),
        status="ok",
        message="fixture",
        latest_observation_date=str(s.index[-1].date()),
        retrieved_at=NOW.isoformat(),
        observations=[
            Observation(date=str(t.date()), value=None if pd.isna(v) else float(v))
            for t, v in s.items()
        ],
        verification={"status": "Calculation verified"},
    )


def anomaly():
    rng = np.random.default_rng(27)
    idx = pd.date_range("2005-01-01", periods=200, freq="MS")
    change = rng.normal(0.2, 0.15, 200)
    change[-1] = 4
    d = source("cpi", pd.Series(100 * np.cumprod(1 + change / 100), index=idx))
    f = detect_change(d, transform, 1, idx[-1].date())
    assert f
    return grouped([f])[0], d


@pytest.mark.parametrize("h", [1, 5, 21, 63, 252])
def test_exact_daily_horizons_and_closures(h):
    idx = pd.bdate_range("2022-01-03", "2026-10-23")
    frame = pd.DataFrame({"date": idx, "value": np.arange(len(idx), dtype=float) + 100})
    grid, q = session_frame(frame, SPECS["sp500"])
    # Actual observations on nominal closures override the calendar assumptions.
    assert "2022-07-04" in q["session_dates"]
    s, _, _, _ = movement(
        frame,
        SPECS["sp500"],
        "percent",
        date(2022, 1, 1),
        transform,
        h,
        "trading_sessions",
    )
    assert s.iloc[-1] == pytest.approx(
        (grid.value.iloc[-1] / grid.value.iloc[-1 - h] - 1) * 100
    )


def test_holiday_weekend_and_unclassified_missing():
    dates = ["2026-07-01", "2026-07-02", "2026-07-03", "2026-07-06", "2026-07-07"]
    frame = pd.DataFrame(
        {"date": pd.to_datetime(dates), "value": [100, 101, None, 102, 103]}
    )
    grid, q = session_frame(frame, SPECS["sp500"])
    assert "2026-07-03" not in q["session_dates"]
    assert len(grid) == 4
    frame.loc[3, "value"] = None
    s, _, q, _ = movement(
        frame,
        SPECS["sp500"],
        "percent",
        date(2026, 7, 1),
        transform,
        1,
        "trading_sessions",
    )
    assert pd.isna(s.iloc[-1]) and q["unexpected_missing"] == 1
    compact = raw_preview(
        source("sp500", frame.set_index("date").value), frame, "2026-07-07"
    )
    assert (
        all(o["value"] is not None for o in compact["observations"])
        and compact["missing_in_preview"] == 1
    )


def test_bonds_good_friday_not_assumed_full_closure():
    f = pd.DataFrame(
        {
            "date": pd.to_datetime(["2026-04-02", "2026-04-03", "2026-04-06"]),
            "value": [4, None, 3.9],
        }
    )
    _, q = session_frame(f, SPECS["us10y"])
    assert "2026-04-03" in q["session_dates"] and q["unexpected_missing"] == 1


@pytest.mark.parametrize(
    "key,h,mode,expected",
    [
        ("unemployment", 3, "pp", 3),
        ("payrolls", 3, "jobs", 3000),
        ("housing_starts", 3, "mom", 30),
    ],
)
def test_economic_units_and_period_horizons(key, h, mode, expected):
    s = pd.Series(
        [10.0, 11, 12, 13], index=pd.date_range("2025-01-01", periods=4, freq="MS")
    )
    values, _, _, _ = movement(
        s.rename("value").rename_axis("date").reset_index(),
        SPECS[key],
        mode,
        date(2025, 1, 1),
        transform,
        h,
    )
    assert values.iloc[-1] == pytest.approx(expected)


def test_weekly_real_labels_missing_week_no_fill():
    s = pd.Series(
        [100.0, 110, 130],
        index=pd.to_datetime(["2026-01-01", "2026-01-08", "2026-01-22"]),
    )
    frame = s.rename("value").rename_axis("date").reset_index()
    v, _ = transform(frame, SPECS["mortgage_30y"], "pp", date(2026, 1, 1))
    assert (
        v.index[-1] == pd.Timestamp("2026-01-22")
        and pd.isna(v.iloc[-1])
        and len(v) == 4
    )
    v, _, _, _ = movement(
        frame, SPECS["mortgage_30y"], "pp", date(2026, 1, 1), transform, 3
    )
    assert v.iloc[-1] == 30


def test_memory_restart_unchanged_and_material_anchor(tmp_path):
    f, d = anomaly()
    store = Store(tmp_path / "state.db")
    mem = DiscoveryMemory(store)
    mem.apply([f], [d], NOW)
    first = mem.list({f["event_key"]}, [d], NOW)[0]
    mem = DiscoveryMemory(Store(store.path))
    mem.apply([f], [d], NOW + timedelta(days=1))
    second = mem.list({f["event_key"]}, [d], NOW + timedelta(days=1))[0]
    assert (
        first["id"] == second["id"]
        and second["lifecycle"]["status"] == "Ongoing"
        and len(second["history"]) == 1
    )
    for step in range(1, 6):
        updated = deepcopy(f)
        updated["evidence"]["movement"] += step * 0.25
        mem.apply([updated], [d], NOW + timedelta(days=step + 1))
    latest = mem.list({f["event_key"]}, [d], NOW + timedelta(days=6))[0]
    assert (
        latest["evidence_version"] == 2
        and latest["id"] == first["id"]
        and latest["history"][0]["evidence"]["movement"] == f["evidence"]["movement"]
    )


def test_ai_cache_key_ignores_nonmaterial_observations(tmp_path):
    f, d = anomaly()
    m = DiscoveryMemory(Store(tmp_path / "s.db"))
    m.apply([f], [d], NOW)
    a = m.list({f["event_key"]}, [d], NOW)[0]
    small = deepcopy(f)
    small["evidence"]["movement"] += 0.001
    m.apply([small], [d], NOW)
    b = m.list({f["event_key"]}, [d], NOW)[0]
    assert ai_cache_key(a) == ai_cache_key(b)


def test_stale_does_not_archive_but_new_healthy_data_does(tmp_path):
    f, d = anomaly()
    m = DiscoveryMemory(Store(tmp_path / "s.db"))
    m.apply([f], [d], NOW)
    future = d.model_copy(
        update={
            "latest_observation_date": str(
                date.fromisoformat(f["observation_date"]) + timedelta(days=400)
            ),
            "status": "stale",
        }
    )
    m.apply([], [future], NOW)
    assert m.list([], [future], NOW)[0]["lifecycle"]["status"] != "Archived"
    future = future.model_copy(update={"status": "ok"})
    m.apply([], [future], NOW)
    assert m.list([], [future], NOW)[0]["lifecycle"]["status"] == "Archived"
    returned = deepcopy(f)
    returned["observation_date"] = future.latest_observation_date
    m.apply([returned], [future], NOW + timedelta(days=401))
    rows = m.list({f["event_key"]}, [future], NOW + timedelta(days=401))
    assert len(rows) == 2 and rows[0]["lifecycle"]["related_discoveries"]


def test_duplicate_horizons_distinct_directions_and_types():
    f, _ = anomaly()
    five = deepcopy(f)
    five["horizon_observations"] = 3
    five["horizon_label"] = "3 months"
    negative = deepcopy(f)
    negative["evidence"]["movement"] = -4
    rows = grouped([f, five, negative])
    assert len(rows) == 2 and max(len(r["alternative_timeframes"]) for r in rows) == 2


def test_relationship_sign_reversal_material():
    f, _ = anomaly()
    f["type"] = "correlation"
    f["evidence"] = {"recent_correlation": 0.5, "correlation_difference": 0.5}
    b = deepcopy(f)
    b["evidence"]["recent_correlation"] = -0.3
    assert "reversed" in material_change(f, b)


def patterns(seed=8):
    rng = np.random.default_rng(seed)
    x = rng.normal(size=60)

    def p(values, year):
        return {
            "required": 60,
            "units": "Percent",
            "observations": [
                {"date": str(t.date()), "value": float(v)}
                for t, v in zip(pd.bdate_range(f"{year}-01-01", periods=60), values)
            ],
        }

    return x, p(x, 2008), p(x * 1.05, 2026), p


def test_history_match_and_false_positive_screens():
    x, a, b, p = patterns()
    assert similarity(a, b)["matches"]
    assert not similarity(a, b, False)["matches"]
    assert not similarity(a, p(x * 8, 2026))["matches"]
    assert not similarity(a, p(-x, 2026))["matches"]
    assert not similarity(a, p(x, 2008))["matches"]
    b["observations"][3]["value"] = None
    assert not similarity(a, b)["matches"]
    assert not similarity(p(np.ones(60), 2008), p(np.ones(60), 2026))["matches"]


@pytest.mark.parametrize("seed", range(10))
def test_unrelated_historical_shapes_not_matches(seed):
    _, a, _, p = patterns()
    assert not similarity(
        a, p(np.random.default_rng(seed + 300).normal(size=60), 2026)
    )["matches"]


def test_library_snapshot_immutable(tmp_path):
    f, d = anomaly()
    store = Store(tmp_path / "s.db")
    h = HistoricalLibrary(store, transform)
    with store.connection(True) as db:
        db.execute(
            "INSERT INTO library VALUES (?,?,?,?,?)",
            (
                "fixed",
                "Historical finding",
                NOW.isoformat(),
                json.dumps(
                    {
                        "finding": f,
                        "pattern": {"observations": [], "required": 24},
                        "definition_hash": "old",
                        "transformation": "mom",
                        "frequency": "monthly",
                        "horizon": 1,
                    }
                ),
                "fixture",
            ),
        )
    h.seed([d], NOW)
    record = next(r for r in h.records([d]) if r["id"] == "fixed")
    assert (
        not record["similarity"]["matches"]
        and record["snapshot"]["finding"]["evidence"] == f["evidence"]
    )


def pricing():
    return {"model": MODEL, "input": 0.125, "output": 0.5}


@pytest.fixture
def guard(tmp_path, monkeypatch):
    monkeypatch.setenv("MACROLENS_AI_ENABLED", "true")
    monkeypatch.setenv("OPENAI_API_KEY", "fixture-never-sent")
    monkeypatch.setenv("MACROLENS_AI_MONTHLY_BUDGET_USD", "2")
    return AIGuard(Store(tmp_path / "ai.db"), pricing_fn=pricing, now_fn=lambda: NOW)


def test_budget_maximum_reservation_and_concurrent_limit(guard, monkeypatch):
    reservation = guard.cost(pricing(), INPUT_BOUND, OUTPUT_BOUND)
    monkeypatch.setenv("MACROLENS_AI_MONTHLY_BUDGET_USD", str(reservation / 1e9 * 2))

    def reserve(n):
        try:
            return guard.reserve(str(n), pricing())[0]
        except BudgetBlocked:
            return None

    with ThreadPoolExecutor(max_workers=12) as pool:
        result = list(pool.map(reserve, range(20)))
    assert sum(x is not None for x in result) == 2
    assert guard.usage()["remaining_usd"] == 0 and guard.usage()["request_count"] == 2


def test_month_rollover_utc(guard, monkeypatch):
    monkeypatch.setenv("MACROLENS_AI_MONTHLY_BUDGET_USD", "0.007")
    guard.reserve("oct", pricing())
    guard.now_fn = lambda: datetime(2026, 11, 1, tzinfo=UTC)
    guard.reserve("nov", pricing())
    assert (
        guard.usage()["month_utc"] == "2026-11" and guard.usage()["request_count"] == 1
    )


def ai_finding():
    f, _ = anomaly()
    f["lifecycle"] = {"status": "New"}
    f["evidence_version"] = 1
    f["evidence_fingerprint"] = "abc"
    return f


def test_ai_reconciles_caches_and_never_repeats_unchanged(guard):
    f = ai_finding()
    calls = []

    def send(body, key):
        calls.append(body)
        assert key == "fixture-never-sent" and body["max_output_tokens"] == OUTPUT_BOUND
        return {
            "usage": {"input_tokens": 100, "output_tokens": 50},
            "output": [
                {
                    "content": [
                        {
                            "type": "output_text",
                            "text": json.dumps(
                                {
                                    "suggestions": [
                                        {"story_id": f["id"], "dataset_id": "core_cpi"}
                                    ]
                                }
                            ),
                        }
                    ]
                }
            ],
        }

    guard.send_fn = send
    assert guard.generate([f])["generated"] == 1
    guard.generate([f])
    assert len(calls) == 1 and guard.usage()["cache_hits_lifetime"] == 1
    assert guard.usage()["accounted_spend_usd"] == guard.cost(pricing(), 100, 50) / 1e9


def test_missing_usage_retains_full_reservation_and_pauses(guard):
    guard.send_fn = lambda *_: {"usage": None}
    with pytest.raises(BudgetBlocked, match="paused"):
        guard.generate([ai_finding()])
    assert guard.usage()["paused_for_uncertain_usage"]
    with pytest.raises(BudgetBlocked):
        guard.reserve("other", pricing())


def test_pricing_unverified_no_request(guard):
    def bad():
        raise RuntimeError("offline")

    guard.pricing_fn = bad
    with pytest.raises(BudgetBlocked, match="pricing"):
        guard.generate([ai_finding()])
    assert guard.usage()["request_count"] == 0


def test_disabled_ai_deterministic_fallback(guard, monkeypatch):
    monkeypatch.setenv("MACROLENS_AI_ENABLED", "false")
    assert (
        guard.generate([ai_finding()])["fallback"]
        and guard.usage()["request_count"] == 0
    )


def test_admin_denies_unconfigured_or_wrong_tokens(monkeypatch):
    monkeypatch.delenv("MACROLENS_ADMIN_TOKEN", raising=False)
    client = TestClient(app)
    assert client.get("/api/v2/discovery/admin/usage").status_code == 403
    monkeypatch.setenv("MACROLENS_ADMIN_TOKEN", "fixture-admin")
    assert (
        client.post(
            "/api/v2/discovery/admin/generate",
            headers={"Authorization": "Bearer wrong"},
        ).status_code
        == 403
    )


def test_persistent_source_cache_restart_preserves_retrieval(tmp_path):
    class Provider:
        calls = 0

        def fred_series(self, *_):
            self.calls += 1
            return [{"date": "2026-09-01", "value": 4.1}]

    provider = Provider()
    store = Store(tmp_path / "s.db")
    cls = scheduled_service_class(DataService, Dataset)
    a = cls(
        store, provider=provider, today_fn=lambda: NOW.date(), now_fn=lambda: NOW
    ).get("unemployment")
    b = cls(
        Store(store.path),
        provider=provider,
        today_fn=lambda: NOW.date(),
        now_fn=lambda: NOW + timedelta(minutes=1),
    ).get("unemployment")
    assert (
        provider.calls == 1
        and a.retrieved_at == b.retrieved_at
        and a.release_metadata["next_check_at"] == b.release_metadata["next_check_at"]
    )


def test_suggestions_validate_actual_pairs_and_reject_mixed_frequency():
    f, d = anomaly()
    other = source(
        "core_cpi",
        pd.Series(
            [o.value * 1.1 for o in d.observations],
            index=pd.to_datetime([o.date for o in d.observations]),
        ),
    )
    rows = suggestions(f, [d, other], transform, ["sp500", "not-real"])
    assert (
        len(rows) == 1
        and rows[0]["configuration"]["datasets"] == ["cpi", "core_cpi"]
        and rows[0]["verified_comparison"]["paired_observations"] == 24
    )


def test_provider_failure_backoff_preserves_stale_observations(tmp_path):
    class Provider:
        calls = 0

        def fred_series(self, *_):
            self.calls += 1
            if self.calls > 1:
                raise RuntimeError("offline")
            return [{"date": "2026-09-01", "value": 4.1}]

    clock = [NOW]
    provider = Provider()
    cls = scheduled_service_class(DataService, Dataset)
    service = cls(
        Store(tmp_path / "s.db"),
        provider=provider,
        today_fn=lambda: clock[0].date(),
        now_fn=lambda: clock[0],
    )
    original = service.get("unemployment")
    clock[0] += timedelta(days=2)
    failed = service.get("unemployment")
    assert (
        failed.status == "stale"
        and failed.retrieved_at == original.retrieved_at
        and failed.observations == original.observations
    )
    service.get("unemployment")
    assert provider.calls == 2


def test_duplicate_concurrent_same_batch_sends_once(guard):
    f = ai_finding()
    calls = []

    def send(*_):
        calls.append(1)
        return {
            "usage": {"input_tokens": 100, "output_tokens": 10},
            "output": [
                {"content": [{"type": "output_text", "text": '{"suggestions":[]}'}]}
            ],
        }

    guard.send_fn = send

    def generate(_):
        try:
            return guard.generate([f])
        except BudgetBlocked:
            return None

    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(generate, range(8)))
    assert len(calls) == 1 and guard.usage()["request_count"] == 1


def test_invalid_ai_output_accounts_usage_and_falls_back(guard):
    guard.send_fn = lambda *_: {
        "usage": {"input_tokens": 10, "output_tokens": 10},
        "output": [{"content": [{"type": "output_text", "text": "not json"}]}],
    }
    result = guard.generate([ai_finding()])
    assert result["fallback"] and guard.usage()["accounted_spend_usd"] > 0


def test_api_horizon_roundtrip_and_old_native_defaults():
    dates = pd.bdate_range("2026-01-01", periods=50)
    s = pd.Series(np.arange(50, dtype=float) + 100, index=dates)
    d = source("sp500", s)

    class Service:
        today_fn = staticmethod(lambda: NOW.date())

        def get(self, _):
            return d

    req = ComparisonRequest(
        datasets=["sp500"],
        transformations={"sp500": "percent"},
        horizons={"sp500": 5},
        observation_basis="trading_sessions",
        start=date(2026, 1, 1),
        end=dates[-1].date(),
    )
    response = compare(Service(), req)
    line = response.series[0]
    assert (
        line.horizon_observations == 5 and line.observation_basis == "trading_sessions"
    )
    assert line.observations[-1].value == pytest.approx((149 / 144 - 1) * 100)
    native = compare(
        Service(),
        req.model_copy(update={"horizons": {}, "observation_basis": "native"}),
    )
    assert native.series[0].horizon_observations == 1


def test_quarterly_horizons_and_invalid_modes():
    from dataclasses import replace

    spec = replace(
        SPECS["real_gdp_growth"],
        allowed_transformations=("level", "pp", "standardized"),
    )
    frame = pd.DataFrame(
        {
            "date": pd.date_range("2024-01-01", periods=8, freq="QS"),
            "value": np.arange(8, dtype=float),
        }
    )
    s, _, _, _ = movement(frame, spec, "pp", date(2024, 1, 1), transform, 4)
    assert s.iloc[-1] == 4
    with pytest.raises(ValueError):
        movement(frame, spec, "level", date(2024, 1, 1), transform, 4)


def test_long_smooth_patterns_fail_effective_sample_guard():
    _, _, _, p = patterns()
    x = np.linspace(-2, 3, 60)
    assert not similarity(p(x, 2008), p(x, 2026))["matches"]


def test_runtime_persists_report_and_does_not_recalculate_on_retrieval_only_change(
    tmp_path, monkeypatch
):
    from backend.app.v2 import runtime

    _f, d = anomaly()

    class Service:
        today_fn = staticmethod(lambda: NOW.date())

        def get(self, _):
            return d

    monkeypatch.setattr(runtime, "SPECS", {"cpi": SPECS["cpi"]})
    store = Store(tmp_path / "runtime.db")
    r = runtime.DynamicDiscovery(Service(), transform, store)
    first = r.get()
    second = runtime.DynamicDiscovery(Service(), transform, Store(store.path)).get()
    assert first["generated_at"] == second["generated_at"]
    assert first["findings"][0]["id"] == second["findings"][0]["id"]
    d.retrieved_at = (NOW + timedelta(hours=1)).isoformat()
    third = r.get()
    assert (
        third["generated_at"] == first["generated_at"]
        and third["source_times"][0]["retrieved"] == d.retrieved_at
    )


def test_relationship_primary_chart_uses_actual_bounded_rolling_pairs():
    from backend.app.v2.dynamic_scan import scan

    rng = np.random.default_rng(482)
    idx = pd.date_range("2005-01-01", periods=240, freq="MS")
    x = rng.normal(0, 0.2, 240)
    y = x * 0.8 + rng.normal(0, 0.05, 240)
    y[-24:] = -x[-24:] + rng.normal(0, 0.02, 24)
    a = source("cpi", pd.Series(100 * np.cumprod(1 + x / 100), index=idx))
    b = source("core_cpi", pd.Series(100 * np.cumprod(1 + y / 100), index=idx))
    report = scan([a, b], transform, idx[-1].date() + timedelta(days=1))
    f = next(f for f in report["findings"] if f["type"] == "correlation")
    preview = f["primary_preview"]
    assert preview["units"].startswith("Correlation")
    values = [o["value"] for o in preview["observations"] if o["value"] is not None]
    assert all(-1.0000001 <= v <= 1.0000001 for v in values)
    assert values[-1] == pytest.approx(f["evidence"]["recent_correlation"])


def test_annual_inflation_question_never_claims_same_horizon_as_one_month_change():
    from backend.app.v2.followups import suggestion

    f, d = anomaly()
    dates = pd.to_datetime([o.date for o in d.observations])
    annual = source(
        "cpi_nsa", pd.Series([o.value for o in d.observations], index=dates)
    )
    rate = source("unemployment", pd.Series(np.linspace(4, 6, len(dates)), index=dates))
    f["datasets"] = ["cpi_nsa"]
    f["horizon_observations"] = 1
    assert (
        suggestion(
            f, "unemployment", {"cpi_nsa": annual, "unemployment": rate}, transform
        )
        is None
    )


def test_cross_process_scan_lease_never_returns_raw_candidate_identities(
    tmp_path, monkeypatch
):
    from backend.app.v2 import runtime

    _f, d = anomaly()

    class Service:
        today_fn = staticmethod(lambda: NOW.date())

        def get(self, _):
            return d

    monkeypatch.setattr(runtime, "SPECS", {"cpi": SPECS["cpi"]})
    store = Store(tmp_path / "runtime.db")
    r = runtime.DynamicDiscovery(Service(), transform, store)
    initial = r.get()
    assert store.acquire("scan", "other-process", datetime.now(UTC).timestamp(), 300)
    d.observations[-1].value += 2
    with pytest.raises(RuntimeError, match="already running"):
        r.get()
    store.release("scan", "other-process")
    updated = r.get()
    assert updated["findings"][0]["id"] == initial["findings"][0]["id"]
