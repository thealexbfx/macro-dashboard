"""Synthetic offline native partitions for tests/resource probes, never production.

24 fixture IDs, six native frequencies, 120 source-labelled observations each.
No real catalog IDs, network, credentials, live adapters or permission writes.
"""

from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from math import ceil

from backend.app.ingestion.native import (
    Definition,
    Observation,
    SourceCalendar,
    digest,
    native_period,
)
from backend.app.ingestion.partition_contracts import Bounds, Page, windows
from backend.app.ingestion.partition_schema import migrate
from backend.app.ingestion.partitioned import PartitionedIngestion


def fixture_definitions():
    return tuple(
        Definition(
            f"fixture_native_{frequency}_{i}",
            "fixture_native",
            f"SYNTHETIC/{frequency}/{i}",
            "Synthetic units",
            frequency,
            "Native fixture adjustment; no resampling",
            SourceCalendar(
                f"fixture_{frequency}", week_ending=5 if frequency == "weekly" else None
            ),
        )
        for frequency in ("daily", "weekly", "monthly", "quarterly", "annual", "event")
        for i in range(4)
    )


def source_points(definition):
    result = []
    for n in range(120):
        frequency = definition.frequency
        if frequency == "monthly":
            key = f"{2000 + n // 12}-{n % 12 + 1:02d}"
        elif frequency == "quarterly":
            key = f"{1970 + n // 4}-Q{n % 4 + 1}"
        elif frequency == "annual":
            key = str(1800 + n)
        elif frequency == "event":
            key = (datetime(2000, 1, 1, tzinfo=UTC) + timedelta(days=n * 2)).isoformat()
        else:
            key = (
                date(2000, 1, 1)
                + timedelta(days=n * (7 if frequency == "weekly" else 2))
            ).isoformat()
        value = (
            None if n % 13 == 0 else 0 if n % 7 == 0 else (-1 if n % 2 else 1) * n / 10
        )
        result.append(
            Observation(
                key, key, value, ("SYNTHETIC_ONLY",), source_revision="fixture_v1"
            )
        )
    return tuple(result)


class FixtureAdapter:
    def __init__(self, points=None):
        self.points = points
        self.calls = 0
        self.fail = None
        self.snapshot = "a" * 64

    def fetch(self, definition, window, cursor, bounds):
        self.calls += 1
        if self.fail:
            raise self.fail
        points = source_points(definition) if self.points is None else self.points
        points = [
            p
            for p in points
            if window.start
            <= native_period(p.period, definition, p.event_id).start
            <= window.end
        ]
        offset = int(cursor or 0)
        selected = tuple(points[offset : offset + bounds.records])
        next_cursor = (
            str(offset + bounds.records)
            if offset + bounds.records < len(points)
            else None
        )
        return Page(
            selected,
            digest([(p.period, p.value, p.flags, p.source_revision) for p in selected]),
            self.snapshot,
            "https://example.invalid/SYNTHETIC_ONLY",
            datetime(2026, 1, 1, tzinfo=UTC),
            next_cursor,
        )


def exercise(store):
    """Already-disposable caller only. Re-running resumes checkpointed generations."""
    with store.connection(True) as db:
        migrate(db)
    definitions = fixture_definitions()
    adapter = FixtureAdapter()
    engine = PartitionedIngestion(
        store, definitions, {"fixture_native": adapter}, bounds=Bounds(records=32)
    )
    for definition in definitions:
        points = source_points(definition)
        start = native_period(points[0].period, definition).start
        end = native_period(points[-1].period, definition).start
        plans = windows(
            start, end, span_days=min(3660, max(1, ceil(((end - start).days + 1) / 3)))
        )
        engine.create_generation(
            definition.id, plans, generation_id="resource_" + definition.id
        )
    for _ in range(400):
        result = engine.run_once()
        if result["state"] == "failed":
            raise AssertionError(result)
        if result["state"] == "idle":
            break
    else:
        raise AssertionError("Bounded fixture did not finish")
    # Exercise a historical correction through a separate complete generation.
    definition = definitions[0]
    revised = list(source_points(definition))
    revised[1] = replace(revised[1], value=-42, source_revision="fixture_v2")
    adapter.points, adapter.snapshot = tuple(revised), "b" * 64
    engine.create_generation(
        definition.id,
        [windows(date(2000, 1, 1), date(2001, 1, 1))[0]],
        generation_id="resource_revision",
    )
    for _ in range(20):
        result = engine.run_once()
        if result["state"] == "failed":
            raise AssertionError(result)
        if result["state"] == "idle":
            break
    with store.connection() as db:
        counts = dict(
            db.execute(
                "SELECT frequency,count(*) FROM (SELECT json_extract(payload,'$.frequency') AS frequency FROM norm_observations) GROUP BY frequency"
            ).fetchall()
        )
        assert sum(counts.values()) == 2880 and len(counts) == 6
        assert db.execute("SELECT count(*) FROM norm_revisions").fetchone()[0] == 1
        assert db.execute(
            "SELECT DISTINCT public_display,ai_allowed,discovery_allowed,rights_state FROM norm_datasets"
        ).fetchall()[0][:] == (0, 0, 0, "unreviewed")
        assert (
            db.execute("SELECT count(*) FROM catalog_scope_reviews").fetchone()[0] == 0
        )
        return {
            "synthetic_only": True,
            "datasets": 24,
            "observations": 2880,
            "frequencies": counts,
            "revisions": 1,
            "adapter_calls": adapter.calls,
            "private_ai_discovery_denied": True,
        }
