"""Native formats/calendars and recoverable private partitions, entirely offline."""

import json
import sqlite3
from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from backend.app.ingestion.contracts import ProviderError
from backend.app.ingestion.formats import PROFILES, parse_payload
from backend.app.ingestion.native import (
    Definition,
    Observation,
    SourceCalendar,
    instant,
    native_period,
)
from backend.app.ingestion.partition_contracts import (
    Bounds,
    Window,
    parsed_page,
    windows,
)
from backend.app.ingestion.partition_schema import migrate
from backend.app.ingestion.partitioned import PartitionedIngestion
from backend.app.v2.state import Store
from scripts.batch0_partition_fixture import FixtureAdapter, exercise
from scripts.validate_batch0_foundation import seed, snapshot

NOW = datetime(2026, 2, 1, tzinfo=UTC)


def definition(frequency="monthly", provider="fixture_native", **kwargs):
    return Definition(
        "fixture_test",
        provider,
        "FIXTURE",
        "Native units",
        frequency,
        "NSA",
        SourceCalendar(
            "fixture_calendar", week_ending=5 if frequency == "weekly" else None
        ),
        **kwargs,
    )


@pytest.mark.parametrize(
    "frequency,key,calendar,expected",
    [
        (
            "monthly",
            "2020-02",
            SourceCalendar("gregorian"),
            ("2020-02-01", "2020-02-29"),
        ),
        (
            "quarterly",
            "2020-Q1",
            SourceCalendar("gregorian"),
            ("2020-01-01", "2020-03-31"),
        ),
        (
            "annual",
            "2024",
            SourceCalendar("jp_fiscal", year_start_month=4, year_label="end"),
            ("2023-04-01", "2024-03-31"),
        ),
        (
            "quarterly",
            "2024-Q4",
            SourceCalendar("jp_fiscal", year_start_month=4, year_label="end"),
            ("2024-01-01", "2024-03-31"),
        ),
        (
            "weekly",
            "2021-01-02",
            SourceCalendar("claims", week_ending=5),
            ("2020-12-27", "2021-01-02"),
        ),
        (
            "weekly",
            "2020-W53",
            SourceCalendar("iso", weekly_labels="iso_week", week_ending=6),
            ("2020-12-28", "2021-01-03"),
        ),
        (
            "daily",
            "2020-12-25",
            SourceCalendar("source_days", holidays=("2020-12-25",)),
            ("2020-12-25", "2020-12-25"),
        ),
    ],
)
def test_native_boundaries_and_holidays_are_not_resampled(
    frequency, key, calendar, expected
):
    d = replace(definition(frequency), calendar=calendar)
    p = native_period(key, d)
    assert (str(p.start), str(p.end)) == expected
    assert p.key == key


@pytest.mark.parametrize(
    "frequency,key",
    [
        ("monthly", "2020-2"),
        ("monthly", "2020-13"),
        ("quarterly", "2020-Q5"),
        ("annual", "20"),
        ("daily", "2021-02-29"),
        ("weekly", "2021-01-03"),
    ],
)
def test_invalid_periods_rejected(frequency, key):
    with pytest.raises(ValueError):
        native_period(key, definition(frequency))


def test_source_release_calendar_dst_and_event_identity():
    ny = ZoneInfo("America/New_York")
    with pytest.raises(ValueError):
        instant(datetime(2020, 3, 8, 2, 30, tzinfo=ny))
    with pytest.raises(ValueError):
        instant(datetime(2020, 1, 1))
    first = datetime(2020, 11, 1, 1, 30, tzinfo=ny, fold=0)
    second = first.replace(fold=1)
    cal = SourceCalendar(
        "release",
        timezone="America/New_York",
        releases=(first, second),
        evidence="https://example.invalid/sourced-calendar",
    )
    assert cal.next_release(first) == instant(second)
    assert cal.next_release(second) is None  # No guessed next recurrence.
    d = replace(definition("event"), calendar=cal)
    a = native_period(first.isoformat(), d, "release_a")
    b = native_period(first.isoformat(), d, "release_b")
    assert a.key != b.key
    assert a.event_at == "2020-11-01T05:30:00+00:00"


def test_partial_reference_period_needs_source_flag_and_value_limits():
    d = definition()
    for value in (-1, 0, None):
        Observation("2020-01", "2020 JAN", value).validated(d, NOW)
    for value in (float("nan"), float("inf"), True):
        with pytest.raises(ValueError):
            Observation("2020-01", "2020 JAN", value).validated(d, NOW)
    with pytest.raises(ValueError, match="Incomplete"):
        Observation("2026-02", "2026 FEB", 1).validated(d, NOW)
    Observation("2026-02", "2026 FEB", 1, ("partial_period",)).validated(d, NOW)


def test_provider_formats_retain_native_labels_units_flags_and_missing_cells():
    fred = replace(definition(provider="fred"), selector="FIXTURE")
    body = json.dumps(
        {
            "observations": [
                {"date": "2020-01-01", "value": "0"},
                {"date": "2020-03-01", "value": "-2", "realtime_start": "2021-01-01"},
                {"date": "2020-04-01", "value": "."},
            ]
        }
    ).encode()
    rows = parse_payload(fred, body)
    assert [(r.period, r.value) for r in rows] == [
        ("2020-01", 0),
        ("2020-03", -2),
        ("2020-04", None),
    ]
    assert (
        rows[1].label == "2020-03-01" and "realtime_start=2021-01-01" in rows[1].flags
    )
    ons = replace(definition(provider="ons"), selector="FIXTURE/MM23")
    body = json.dumps(
        {
            "description": {"cdid": "FIXTURE"},
            "months": [{"date": "2020 FEB", "value": "-1"}],
            "quarters": [{"date": "2020 Q1", "value": "100"}],
        }
    ).encode()
    assert parse_payload(ons, body)[0].period == "2020-02"
    assert parse_payload(replace(ons, frequency="quarterly"), body)[0].value == 100
    eia = replace(definition(provider="eia"), dimensions=(("series", "FIXTURE"),))
    body = json.dumps(
        {
            "response": {
                "frequency": "monthly",
                "data": [
                    {
                        "period": "2020-01",
                        "value": "-1",
                        "value-units": "Native units",
                        "series": "FIXTURE",
                    }
                ],
            }
        }
    ).encode()
    assert parse_payload(eia, body)[0].value == -1
    with pytest.raises(ValueError, match="units"):
        parse_payload(replace(eia, units="Different"), body)
    oecd = replace(
        definition("quarterly", provider="oecd"),
        dimensions=(("REF_AREA", "JPN"),),
        unit_multiplier=3,
    )
    rows = parse_payload(
        oecd,
        b"TIME_PERIOD,OBS_VALUE,OBS_STATUS,UNIT_MULT,REF_AREA\n2020-Q1,-2,P,3,JPN\n",
    )
    assert rows[0].value == -2  # Keep native multiplier, never multiply silently.
    assert "UNIT_MULT=3" in rows[0].flags
    with pytest.raises(ValueError, match="multiplier"):
        parse_payload(
            replace(oecd, unit_multiplier=0),
            b"TIME_PERIOD,OBS_VALUE,UNIT_MULT,REF_AREA\n2020-Q1,1,3,JPN\n",
        )


def test_jsonstat_pins_entire_cube_and_does_not_invent_a_time_grid():
    d = replace(
        definition(provider="eurostat"), dimensions=(("geo", "DE"), ("unit", "I21"))
    )
    source = {
        "id": ["geo", "unit", "time"],
        "size": [1, 1, 3],
        "dimension": {
            "geo": {"category": {"index": {"DE": 0}}},
            "unit": {"category": {"index": {"I21": 0}}},
            "time": {"category": {"index": {"2020-01": 0, "2020-03": 1, "2020-04": 2}}},
        },
        "value": {"0": -2, "1": 0},
        "status": {"0": "p"},
    }
    points = parse_payload(d, json.dumps(source).encode())
    assert [p.period for p in points] == ["2020-01", "2020-03", "2020-04"]
    assert [p.value for p in points] == [-2, 0, None]
    source["size"][0] = 2
    with pytest.raises(ValueError, match="cube"):
        parse_payload(d, json.dumps(source).encode())


def test_format_and_transport_bounds_and_access_restrictions():
    assert {"fred", "eurostat", "ons", "eia", "oecd", "ecb"} <= set(PROFILES)
    assert (
        "caching" in PROFILES["fred"].restrictions
        and "key" in PROFILES["eia"].credentials
    )
    with pytest.raises(ValueError):
        parse_payload(definition(provider="fred"), b" " * 524289)
    with pytest.raises(ValueError):
        parse_payload(
            definition(provider="fred"), b'{"observations":[{},{}]}', max_rows=1
        )
    with pytest.raises(ValueError):
        parsed_page(
            definition(provider="fred"),
            b'{"observations":[]}',
            snapshot_hash="a" * 64,
            source_url="https://example.invalid/?api_key=SECRET",
            checked_at=NOW,
        )
    with pytest.raises(ValueError):
        Bounds(records=1001)


@pytest.fixture
def env(tmp_path):
    store = Store(tmp_path / "disposable.sqlite3")
    with store.connection(True) as db:
        migrate(db)
    clock = [NOW]
    adapter = FixtureAdapter(
        (
            Observation("2020-01", "2020 JAN", 0),
            Observation("2020-02", "2020 FEB", -2),
            Observation("2020-04", "2020 APR", None),
        )
    )
    d = definition()
    engine = PartitionedIngestion(
        store,
        [d],
        {d.provider: adapter},
        bounds=Bounds(records=1),
        now_fn=lambda: clock[0],
    )
    return store, d, adapter, engine, clock


def rows(store, table):
    with store.connection() as db:
        return [dict(r) for r in db.execute("SELECT * FROM " + table)]


def complete(engine, attempts=20):
    for _ in range(attempts):
        result = engine.run_once()
        assert result["state"] != "failed", result
        if result["state"] == "idle":
            return
    raise AssertionError("Did not reach bounded completion")


def test_checkpoint_restart_atomic_promotion_and_idempotency(env):
    store, d, adapter, engine, clock = env
    plans = windows(date(2020, 1, 1), date(2020, 12, 31))
    gen = engine.create_generation(d.id, plans, generation_id="fixture_initial")
    assert engine.create_generation(d.id, plans, generation_id=gen) == gen
    assert engine.run_once()["state"] == "pending"
    assert rows(store, "norm_observations") == []
    restarted = PartitionedIngestion(
        store,
        [d],
        {d.provider: adapter},
        bounds=Bounds(records=1),
        now_fn=lambda: clock[0],
    )
    complete(restarted)
    current = rows(store, "norm_observations")
    assert [(r["period_key"], r["value"]) for r in current] == [
        ("2020-01", 0),
        ("2020-02", -2),
        ("2020-04", None),
    ]
    assert len(rows(store, "norm_pages")) == 3
    assert rows(store, "catalog_dataset_completeness")[0]["state"] == "complete"
    engine.create_generation(d.id, plans, generation_id="fixture_repeat")
    complete(engine)
    assert not rows(store, "norm_revisions")
    assert len(rows(store, "norm_observations")) == 3


def test_old_revisions_withdrawal_and_omitted_history(env):
    store, d, adapter, engine, _clock = env
    plans = [Window(date(2020, 1, 1), date(2020, 12, 31))]
    engine.create_generation(d.id, plans)
    complete(engine)
    adapter.points = (
        replace(adapter.points[0], value=-3, source_revision="revised"),
        *adapter.points[1:],
    )
    adapter.snapshot = "b" * 64
    engine.create_generation(d.id, plans)
    complete(engine)
    assert rows(store, "norm_revisions")[0]["old_payload"]
    assert rows(store, "norm_observations")[0]["revision"] == 2
    previous = rows(store, "norm_observations")
    adapter.points = adapter.points[1:]
    engine.create_generation(d.id, plans)
    result = None
    for _ in range(3):
        result = engine.run_once()
        if result["state"] == "failed":
            break
    assert result["error_code"] == "history_omitted"
    assert rows(store, "norm_observations") == previous


def test_snapshot_change_requires_explicit_restart_and_keeps_last_good(env):
    store, d, adapter, engine, _clock = env
    gen = engine.create_generation(d.id, [Window(date(2020, 1, 1), date(2020, 12, 31))])
    engine.run_once()
    adapter.snapshot = "b" * 64
    assert engine.run_once()["error_code"] == "snapshot_changed"
    assert not rows(store, "norm_observations")
    newer = engine.restart_generation(gen)
    complete(engine)
    assert len(rows(store, "norm_observations")) == 3
    assert len(rows(store, "norm_staged")) == 4  # Superseded evidence retained.
    assert rows(store, "norm_dataset_state")[0]["active_generation"] == newer


def test_retry_after_failures_are_independently_recoverable(env):
    store, d, adapter, engine, clock = env
    other = replace(d, id="fixture_other", provider="other_fixture")
    good = FixtureAdapter(adapter.points)
    engine = PartitionedIngestion(
        store,
        [d, other],
        {d.provider: adapter, other.provider: good},
        now_fn=lambda: clock[0],
    )
    adapter.fail = ProviderError("provider_outage", retry_after=600)
    engine.create_generation(
        d.id, [Window(date(2020, 1, 1), date(2020, 12, 31))], generation_id="a_outage"
    )
    engine.create_generation(
        other.id,
        [Window(date(2020, 1, 1), date(2020, 12, 31))],
        generation_id="b_healthy",
    )
    assert engine.run_once()["state"] == "failed"
    assert engine.run_once()["state"] == "complete"
    assert engine.run_once()["state"] == "idle"
    adapter.fail = None
    clock[0] += timedelta(seconds=601)
    complete(engine)
    assert len(rows(store, "norm_observations")) == 6


def test_duplicate_values_fencing_and_expired_worker_recovery(env):
    store, d, adapter, engine, clock = env
    engine.create_generation(d.id, [Window(date(2020, 1, 1), date(2020, 12, 31))])
    with store.connection(True) as db:
        db.execute(
            "INSERT INTO norm_worker_lease VALUES(1,'dead_worker',?)",
            (clock[0].timestamp() + 120,),
        )
    assert engine.run_once()["state"] == "busy"
    clock[0] += timedelta(seconds=121)
    original = adapter.fetch

    def steal(*args):
        page = original(*args)
        with store.connection(True) as db:
            db.execute(
                "UPDATE norm_worker_lease SET owner='new_owner',expires_at=?",
                (clock[0].timestamp() + 120,),
            )
        return page

    adapter.fetch = steal
    assert engine.run_once()["error_code"] == "lease_lost"
    assert not rows(store, "norm_staged")
    clock[0] += timedelta(seconds=121)
    adapter.fetch = original
    complete(engine)
    assert any(r["state"] == "abandoned" for r in rows(store, "norm_runs"))


def test_private_schema_and_old_research_preservation(tmp_path):
    store = Store(tmp_path / "restored-disposable.sqlite3")
    with store.connection(True) as db:
        seed(db)
        before = snapshot(db)
        migrate(db)
        migrate(db)
    result = exercise(store)
    assert result["observations"] == 2880
    with store.connection() as db:
        assert snapshot(db) == before
        assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert (
            db.execute("SELECT count(*) FROM catalog_scope_reviews").fetchone()[0] == 0
        )
    for scope in ("public_display", "ai_allowed", "discovery_allowed"):
        with store.connection(True) as db, pytest.raises(sqlite3.IntegrityError):
            db.execute("UPDATE norm_datasets SET " + scope + "=1")


@pytest.mark.parametrize(
    "key", ["cpi", "wb_brent_monthly", "wb_copper_monthly", "wb_iron_ore_monthly"]
)
def test_protected_dataset_ids_cannot_be_shadowed(env, key):
    store, d, adapter, _engine, _clock = env
    with pytest.raises(ValueError, match="shadowed"):
        PartitionedIngestion(store, [replace(d, id=key)], {d.provider: adapter})


@pytest.mark.parametrize(
    "mode,expected",
    [
        ("within_page", "duplicate_or_outside_partition"),
        ("across_pages", "duplicate_observation"),
        ("cursor_cycle", "checkpoint_cycle"),
        ("nan", "invalid_source"),
        ("oversize", "invalid_page"),
    ],
)
def test_bad_pages_cannot_commit_or_advance_checkpoint(env, mode, expected):
    store, d, adapter, engine, clock = env
    if mode == "within_page":
        engine = PartitionedIngestion(
            store,
            [d],
            {d.provider: adapter},
            bounds=Bounds(records=10),
            now_fn=lambda: clock[0],
        )
        adapter.points = (adapter.points[0], adapter.points[0])
    elif mode == "nan":
        adapter.points = (replace(adapter.points[0], value=float("nan")),)
    original = adapter.fetch

    def bad(*args):
        page = original(*args)
        cursor = args[2]
        if mode == "across_pages" and cursor is not None:
            return replace(page, points=(adapter.points[0],), next_cursor=None)
        if mode == "cursor_cycle" and cursor == "2":
            return replace(page, next_cursor="1")
        if mode == "oversize":
            return replace(page, points=adapter.points)
        return page

    adapter.fetch = bad
    engine.create_generation(d.id, [Window(date(2020, 1, 1), date(2020, 12, 31))])
    for _ in range(4):
        result = engine.run_once()
        if result["state"] == "failed":
            break
    assert result["error_code"] == expected
    assert not rows(store, "norm_observations")
    assert rows(store, "norm_partitions")[0]["state"] == "failed"


def test_promotion_failure_rolls_back_then_recovers_without_duplicates(env):
    store, d, _adapter, engine, clock = env
    engine.create_generation(d.id, [Window(date(2020, 1, 1), date(2020, 12, 31))])
    engine.run_once()
    engine.run_once()
    with store.connection(True) as db:
        db.execute(
            "CREATE TRIGGER fixture_abort BEFORE INSERT ON norm_observations BEGIN SELECT RAISE(ABORT,'synthetic write failure'); END"
        )
    assert engine.run_once()["state"] == "failed"
    assert len(rows(store, "norm_staged")) == 2
    assert not rows(store, "norm_observations")
    assert not rows(store, "norm_revisions")
    with store.connection(True) as db:
        db.execute("DROP TRIGGER fixture_abort")
    clock[0] += timedelta(seconds=121)
    complete(engine)
    assert len(rows(store, "norm_observations")) == 3
    assert len(rows(store, "norm_pages")) == 3


def test_lease_is_rechecked_after_promotion_before_commit(env):
    store, d, adapter, engine, clock = env
    engine = PartitionedIngestion(
        store, [d], {d.provider: adapter}, now_fn=lambda: clock[0]
    )
    original = engine._promote

    def expire(*args):
        original(*args)
        clock[0] += timedelta(seconds=121)

    engine._promote = expire
    engine.create_generation(d.id, [Window(date(2020, 1, 1), date(2020, 12, 31))])
    assert engine.run_once()["error_code"] == "lease_lost"
    assert not rows(store, "norm_observations")
    assert not rows(store, "catalog_dataset_completeness")


def test_two_native_events_at_same_instant_remain_distinct(env):
    store, _d, _adapter, _engine, clock = env
    d = definition("event")
    adapter = FixtureAdapter(
        (
            Observation("2020-01-01T00:00:00Z", "native release A", 0, event_id="a"),
            Observation("2020-01-01T00:00:00Z", "native release B", -1, event_id="b"),
        )
    )
    engine = PartitionedIngestion(
        store,
        [replace(d, id="fixture_events")],
        {d.provider: adapter},
        now_fn=lambda: clock[0],
    )
    engine.create_generation(
        "fixture_events", [Window(date(2020, 1, 1), date(2020, 1, 1))]
    )
    complete(engine)
    assert len(rows(store, "norm_observations")) == 2
    assert {
        json.loads(r["payload"])["event_id"] for r in rows(store, "norm_observations")
    } == {"a", "b"}


def test_unit_review_is_retained_but_never_marked_publishable(env):
    store, d, adapter, engine, _clock = env
    adapter.points = tuple(replace(p, flags=("unit_review",)) for p in adapter.points)
    engine.create_generation(d.id, [Window(date(2020, 1, 1), date(2020, 12, 31))])
    complete(engine)
    assert len(rows(store, "norm_observations")) == 3
    assert rows(store, "catalog_dataset_completeness")[0]["quality_passed"] == 0
    assert rows(store, "catalog_dataset_completeness")[0]["state"] == "partial"


def test_v2_migration_restore_and_rollback_preserve_all_old_tables(tmp_path):
    from contextlib import closing

    original, restored = tmp_path / "old.sqlite3", tmp_path / "restored.sqlite3"
    with closing(sqlite3.connect(original)) as db:
        seed(db)
        before = snapshot(db)
    with (
        closing(sqlite3.connect(original)) as source,
        closing(sqlite3.connect(restored)) as target,
    ):
        source.backup(target)
    with closing(sqlite3.connect(restored)) as db:
        db.execute("BEGIN")
        migrate(db)
        db.rollback()
        assert not db.execute(
            "SELECT name FROM sqlite_master WHERE name LIKE 'norm_%'"
        ).fetchall()
        migrate(db)
        migrate(db)
        assert snapshot(db) == before
        assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    # Existing deployed code ignores all new tables; no reverse migration needed.
    with Store(restored).connection() as db:
        assert snapshot(db) == before


def test_unknown_failure_diagnostics_never_persist_exception_text(env):
    store, d, adapter, engine, _clock = env
    adapter.fail = RuntimeError("SYNTHETIC_TOKEN_MUST_NOT_BE_STORED")
    engine.create_generation(d.id, [Window(date(2020, 1, 1), date(2020, 12, 31))])
    assert engine.run_once()["error_code"] == "internal_error"
    assert "SYNTHETIC_TOKEN" not in json.dumps(rows(store, "norm_runs"))
    status = engine.status()
    assert (
        status["public_display"]
        is status["ai_allowed"]
        is status["discovery_allowed"]
        is False
    )
    assert all(
        "cursor" not in item and "source_url" not in item
        for item in status["partitions"]
    )


def test_window_budget_and_definition_change_require_review(env):
    store, d, adapter, _engine, _clock = env
    with pytest.raises(ValueError, match="exceeds"):
        windows(date(2000, 1, 1), date(2020, 1, 1), span_days=1)
    with pytest.raises(ValueError, match="Definition"):
        PartitionedIngestion(
            store, [replace(d, units="New benchmark unit")], {d.provider: adapter}
        )


def test_api_pagination_totals_cannot_be_ignored():
    d = definition(provider="fred")
    body = b'{"count":2,"offset":0,"observations":[{"date":"2020-01-01","value":"0"}]}'
    args = {
        "snapshot_hash": "a" * 64,
        "source_url": "https://example.invalid/fixture",
        "checked_at": NOW,
    }
    with pytest.raises(ValueError, match="pagination"):
        parsed_page(d, body, **args)
    assert parsed_page(d, body, next_cursor="1", **args).points[0].value == 0
    with pytest.raises(ValueError, match="value field"):
        parse_payload(d, b'{"observations":[{"date":"2020-01-01"}]}')


def test_database_outage_releases_worker_and_recovers_checkpoint(env):
    store, d, adapter, engine, clock = env
    engine.create_generation(d.id, [Window(date(2020, 1, 1), date(2020, 12, 31))])
    original_connection, original_fetch = store.connection, adapter.fetch

    def unavailable(*_args, **_kwargs):
        raise sqlite3.OperationalError("synthetic unavailable database")

    def interrupt(*args):
        page = original_fetch(*args)
        store.connection = unavailable
        return page

    adapter.fetch = interrupt
    assert engine.run_once()["error_code"] == "database_unavailable"
    assert not engine.lock.locked()
    store.connection, adapter.fetch = original_connection, original_fetch
    clock[0] += timedelta(seconds=121)
    complete(engine)
    assert len(rows(store, "norm_observations")) == 3


def test_irregular_contract_and_source_release_schedule(env):
    _store, d, _adapter, engine, _clock = env
    event = native_period(
        "2020-01-01T09:00:00+09:00", definition("irregular"), "revision"
    )
    assert event.event_at == "2020-01-01T00:00:00+00:00"
    assert engine.next_source_release(d.id) is None
    release = datetime(2026, 3, 1, 9, tzinfo=ZoneInfo("Asia/Tokyo"))
    engine.definitions[d.id] = replace(
        d,
        calendar=replace(
            d.calendar,
            releases=(release,),
            evidence="https://example.invalid/official-release-fixture",
        ),
    )
    assert engine.next_source_release(d.id) == release.astimezone(UTC)


def test_canonical_source_cannot_be_aliased_and_calendar_updates_persist(env):
    store, d, adapter, _engine, _clock = env
    with pytest.raises(ValueError, match="already registered"):
        PartitionedIngestion(
            store, [replace(d, id="fixture_alias")], {d.provider: adapter}
        )
    changed = replace(
        d,
        calendar=replace(
            d.calendar,
            releases=(datetime(2027, 1, 1, tzinfo=UTC),),
            evidence="https://example.invalid/official-calendar",
        ),
    )
    assert changed.fingerprint == d.fingerprint
    PartitionedIngestion(store, [changed], {d.provider: adapter})
    metadata = json.loads(rows(store, "norm_datasets")[0]["definition"])
    assert metadata["calendar"]["releases"] == ["2027-01-01T00:00:00+00:00"]


def test_constructor_never_initializes_a_missing_or_unmigrated_database(tmp_path):
    missing = tmp_path / "missing.sqlite3"
    d, adapter = definition(), FixtureAdapter()
    with pytest.raises(ValueError, match="migration"):
        PartitionedIngestion(Store(missing), [d], {d.provider: adapter})
    assert not missing.exists()
    old = Store(tmp_path / "old.sqlite3")
    with old.connection() as db:
        before = snapshot(db)
    with pytest.raises(ValueError, match="migration"):
        PartitionedIngestion(old, [d], {d.provider: adapter})
    with old.connection() as db:
        assert snapshot(db) == before
        assert not db.execute(
            "SELECT name FROM sqlite_master WHERE name LIKE 'norm_%'"
        ).fetchall()
