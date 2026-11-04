"""Synthetic provider/cache regressions; never production or paid API calls."""

import csv
import io
import json
from dataclasses import asdict
from datetime import UTC, date, datetime, timedelta
from types import SimpleNamespace

import pandas as pd
import pytest

from backend.app.catalog import operations
from backend.app.v2.definitions import SPECS
from backend.app.v2.legacy_history import reconcile_rolling_prefix
from backend.app.v2.main import DataService, Dataset, Observation
from backend.app.v2.refresh import scheduled_service_class
from backend.app.v2.state import Store, dumps
from scripts.readiness_refresh_diagnostics import compare_coverage, diagnostics


def old_rows():
    return [
        (d.date(), 3.0 + i / 10000)
        for i, d in enumerate(pd.bdate_range("2023-11-03", "2026-10-30"))
    ]


class Provider:
    def __init__(self):
        self.rows = old_rows()
        self.calls = 0
        self.fail = False

    def fred_series(self, *args):
        self.calls += 1
        if self.fail:
            raise RuntimeError("synthetic transport failure")
        return self.rows


def service(tmp_path, key):
    clock = [datetime(2026, 11, 3, 14, tzinfo=UTC)]
    provider = Provider()
    store = Store(tmp_path / "state.sqlite3")
    cls = scheduled_service_class(DataService, Dataset)
    svc = cls(
        store,
        provider=provider,
        today_fn=lambda: clock[0].date(),
        now_fn=lambda: clock[0],
    )
    first = svc.get(key)
    clock[0] += timedelta(days=1)
    # Source rollover plus one new observation and one valid overlapping revision.
    provider.rows = [
        (d, v + (0.25 if d == date(2026, 10, 29) else 0))
        for d, v in old_rows()
        if d >= date(2023, 11, 6)
    ] + [(date(2026, 11, 2), 3.5)]
    return clock, provider, store, svc, first


@pytest.mark.parametrize("key", ["high_yield_spread", "investment_grade_spread"])
def test_documented_rollover_is_lossless_and_revises_overlap_with_restart(
    tmp_path, key
):
    clock, provider, store, svc, first = service(tmp_path, key)
    refreshed = svc.get(key)
    values = {o.date: o.value for o in refreshed.observations}
    original = {o.date: o.value for o in first.observations}
    assert set(original) <= set(values)
    assert values["2023-11-03"] == original["2023-11-03"]
    assert values["2026-10-29"] == original["2026-10-29"] + 0.25
    assert refreshed.latest_observation_date == "2026-11-02"
    assert refreshed.revision_count == 1
    meta = refreshed.release_metadata
    assert meta["source_check_succeeded"]
    assert meta["last_source_success_at"] == clock[0].isoformat()
    assert meta["source_available_start"] == "2023-11-06"
    assert meta["retained_before_source_start_count"] == 1
    assert "not reverified" in meta["retained_before_source_start_note"]
    assert refreshed.coverage_start == first.coverage_start
    with store.connection() as db:
        assert (
            db.execute(
                "SELECT failures FROM source_cache WHERE id=?", (key,)
            ).fetchone()[0]
            == 0
        )
    restarted = scheduled_service_class(DataService, Dataset)(
        Store(store.path),
        provider=provider,
        today_fn=lambda: clock[0].date(),
        now_fn=lambda: clock[0] + timedelta(minutes=1),
    )
    again = restarted.get(key)
    assert provider.calls == 2
    assert again.observations == refreshed.observations
    assert (
        again.release_metadata["last_source_success_at"]
        == meta["last_source_success_at"]
    )


@pytest.mark.parametrize("key", ["high_yield_spread", "investment_grade_spread"])
@pytest.mark.parametrize(
    "damage",
    [
        "missing_interior",
        "null_interior",
        "missing_tail",
        "null_left_boundary",
        "shortened_window",
        "transport",
    ],
)
def test_guard_still_rejects_losses_and_retains_last_good(tmp_path, key, damage):
    _clock, provider, store, svc, first = service(tmp_path, key)
    if damage == "missing_interior":
        provider.rows = [(d, v) for d, v in provider.rows if d != date(2025, 6, 3)]
    elif damage == "null_interior":
        provider.rows = [
            (d, None if d == date(2025, 6, 3) else v) for d, v in provider.rows
        ]
    elif damage == "missing_tail":
        provider.rows = [(d, v) for d, v in provider.rows if d <= date(2026, 10, 29)]
    elif damage == "null_left_boundary":
        provider.rows.insert(0, (date(2023, 11, 3), None))
    elif damage == "shortened_window":
        provider.rows = [(d, v) for d, v in provider.rows if d >= date(2024, 1, 1)]
    else:
        provider.fail = True
    failed = svc.get(key)
    assert failed.status == "stale"
    assert failed.observations == first.observations
    assert failed.retrieved_at == first.retrieved_at
    assert failed.release_metadata["source_check_succeeded"] is False
    assert (
        failed.release_metadata["last_source_success_at"]
        == first.release_metadata["last_source_success_at"]
    )
    with store.connection() as db:
        assert (
            db.execute(
                "SELECT failures FROM source_cache WHERE id=?", (key,)
            ).fetchone()[0]
            == 1
        )
    svc.get(key)  # Existing backoff cannot trigger an extra source request.
    assert provider.calls == 2


def test_other_daily_series_does_not_get_a_prefix_exception(tmp_path):
    _, _, _, svc, first = service(tmp_path, "breakeven_5y")
    failed = svc.get("breakeven_5y")
    assert failed.observations == first.observations
    assert failed.release_metadata["source_check_succeeded"] is False


def test_calendar_anniversary_handles_leap_day_without_history_loss():
    frame = pd.DataFrame(
        {"date": pd.to_datetime(["2021-03-01", "2024-02-28"]), "value": [3.0, 3.1]}
    )
    old = [Observation(date="2021-02-26", value=2.9)]
    combined, meta = reconcile_rolling_prefix(
        frame, old, SPECS["high_yield_spread"], date(2024, 2, 29)
    )
    assert len(combined) == 3 and meta["retained_before_source_start_count"] == 1


def csv_response(rows):
    stream = io.StringIO()
    writer = csv.writer(stream)
    writer.writerow(["observation_date", "BAMLH0A0HYM2"])
    writer.writerows((d.isoformat(), "." if v is None else v) for d, v in rows)
    return stream.getvalue().encode()


def test_optional_coverage_diagnostic_proves_prefix_vs_internal_loss(tmp_path):
    _clock, provider, store, _svc, first = service(tmp_path, "high_yield_spread")
    before = store.path.read_bytes()
    calls = []

    def fetch(series):
        calls.append(series)
        return csv_response(provider.rows)

    report = diagnostics(store.path, compare_public_csv=True, fetch_csv=fetch)
    result = next(
        r["coverage_comparison"]
        for r in report["datasets"]
        if r["id"] == "high_yield_spread"
    )
    assert calls == ["BAMLH0A0HYM2"]
    assert result["missing_before_source_start"] == 1
    assert result["missing_within_or_after_source_range"] == 0
    assert result["overlap_revision_count"] == 1
    assert store.path.read_bytes() == before
    assert "observations" not in json.dumps(report)
    damaged = [(d, v) for d, v in provider.rows if d != date(2025, 6, 3)]
    result = compare_coverage(first.model_dump(), csv_response(damaged), "BAMLH0A0HYM2")
    assert result["missing_within_or_after_source_range"] == 1


def test_coverage_diagnostic_rejects_identity_and_size():
    with pytest.raises(ValueError):
        compare_coverage(
            {"provider_id": "wrong"}, csv_response(old_rows()), "BAMLH0A0HYM2"
        )
    with pytest.raises(ValueError):
        compare_coverage({"provider_id": "BAMLH0A0HYM2"}, b"x" * 131073, "BAMLH0A0HYM2")


@pytest.mark.parametrize(
    "key", ["consumer_sentiment", "fed_funds", "industrial_production", "retail_sales"]
)
def test_old_ok_cache_is_unverified_until_a_real_successful_check(
    tmp_path, monkeypatch, key
):
    now = [datetime(2026, 11, 3, 18, tzinfo=UTC)]
    provider = Provider()
    provider.rows = [
        (date(2026, 8, 1), 100.0),
        (date(2026, 9, 1), 101.0),
        (date(2026, 10, 1), 102.0),
    ]
    store = Store(tmp_path / "old-cache.sqlite3")
    old = Dataset(
        **asdict(SPECS[key]),
        status="ok",
        message="Synthetic old-release cache",
        observations=[
            Observation(date=d.isoformat(), value=v) for d, v in provider.rows
        ],
        latest_observation_date="2026-10-01",
        retrieved_at=(now[0] - timedelta(hours=1)).isoformat(),
    )
    next_due = now[0] + timedelta(hours=12)
    with store.connection(True) as db:
        db.execute(
            "INSERT INTO source_cache VALUES(?,?,?,?,0)",
            (key, dumps(old.model_dump()), now[0].isoformat(), next_due.isoformat()),
        )
    cls = scheduled_service_class(DataService, Dataset)
    svc = cls(
        store, provider=provider, today_fn=lambda: now[0].date(), now_fn=lambda: now[0]
    )
    with store.connection() as db:
        before = list(db.iterdump())
    read = svc.get(key)
    assert provider.calls == 0
    assert read.release_metadata["source_check_telemetry"] == "legacy_unverified"
    assert read.release_metadata["last_source_success_at"] is None
    with store.connection() as db:
        assert list(db.iterdump()) == before
    # Data Health must not turn an old retrieval date into recorded success.
    monkeypatch.setattr(
        operations, "NativeReader", lambda path: SimpleNamespace(publications={})
    )
    health = operations.health(store.path, scheduler={"ready": True}, now=now[0])
    assert next(r for r in health["items"] if r["id"] == key)["last_success"] is None
    now[0] = next_due + timedelta(minutes=1)
    provider.fail = True
    failure = svc.get(key)
    assert failure.release_metadata["last_source_success_at"] is None
    assert failure.release_metadata["source_check_telemetry"] == "recorded_failure"
    now[0] += timedelta(hours=2)
    provider.fail = False
    success = svc.get(key)
    assert success.release_metadata["last_source_success_at"] == now[0].isoformat()
    assert success.release_metadata["source_check_telemetry"] == "recorded_success"
    assert provider.calls == 2
    with store.connection() as db:
        cached = json.loads(
            db.execute(
                "SELECT payload FROM source_cache WHERE id=?", (key,)
            ).fetchone()[0]
        )
    assert cached["release_metadata"]["last_source_success_at"] == now[0].isoformat()
