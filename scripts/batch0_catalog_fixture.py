"""Disposable-only publication simulation. Never import this from application code.

The production schema intentionally forbids publication. This fixture creates a
relaxed table BEFORE migration in a new empty temporary database, using fake IDs
and example.invalid evidence only. No real rights are granted.
"""

from dataclasses import replace
from datetime import UTC, datetime

from backend.app.ingestion.native import Definition, SourceCalendar, native_period
from backend.app.ingestion.partition_contracts import Bounds, Window
from backend.app.ingestion.partition_schema import STATEMENTS, migrate
from backend.app.ingestion.partitioned import PartitionedIngestion
from backend.app.v2.native_reader import NativePublication, NativeReader
from scripts.batch0_partition_fixture import FixtureAdapter, source_points


def seed_catalog(store, count=279):
    with store.connection(True) as db:
        # Guard against applying this test-only fixture to any populated database.
        assert not db.execute("SELECT 1 FROM source_cache LIMIT 1").fetchone()
        assert not db.execute(
            "SELECT 1 FROM sqlite_master WHERE name='norm_datasets'"
        ).fetchone()
        statement = (
            STATEMENTS[0]
            .replace("CHECK(public_display=0)", "CHECK(public_display IN (0,1))")
            .replace(
                "CHECK(rights_state='unreviewed')",
                "CHECK(rights_state IN ('unreviewed','permitted'))",
            )
        )
        db.execute(statement)
        migrate(db)
    definitions, publications = [], {}
    frequencies = (
        "daily",
        "weekly",
        "monthly",
        "quarterly",
        "annual",
        "event",
        "irregular",
    )
    providers = (
        "fixture_fred",
        "fixture_eurostat",
        "fixture_ons",
        "fixture_eia",
        "fixture_wb",
    )
    for i in range(count):
        f = frequencies[i % len(frequencies)]
        d = Definition(
            f"fixture_catalog_{i:03d}",
            providers[i % 5],
            f"SYNTHETIC/{i}",
            "Synthetic units",
            f,
            "NSA",
            SourceCalendar(
                f"fixture_{f}",
                week_ending=5 if f == "weekly" else None,
                year_start_month=4 if i % 2 and f in {"annual", "quarterly"} else 1,
                year_label="end" if i % 2 and f in {"annual", "quarterly"} else "start",
            ),
        )
        definitions.append(d)
        publications[d.id] = NativePublication(
            d,
            f"Synthetic {i:03d} {f}",
            "Synthetic macro" if i % 2 else "Synthetic commodities",
            ("US", "UK", "JP", "EU")[i % 4],
            "https://example.invalid/SYNTHETIC_ONLY",
            "https://example.invalid/license",
            ("Synthetic fixture; no actual data licence",),
            "SYNTHETIC_TEST_APPROVAL",
        )
    for offset in range(0, count, 32):
        batch = definitions[offset : offset + 32]
        adapter = FixtureAdapter()
        engine = PartitionedIngestion(
            store,
            batch,
            {d.provider: adapter for d in batch},
            bounds=Bounds(records=120),
            now_fn=lambda: datetime(2026, 2, 1, tzinfo=UTC),
        )
        for d in batch:
            points = (
                source_points(replace(d, frequency="event"))
                if d.frequency == "irregular"
                else source_points(d)
            )
            if d.frequency in {"event", "irregular"}:
                # Two genuinely distinct events at the same instant must both survive.
                points = points + (
                    replace(points[1], event_id="simultaneous_second", value=-99),
                )
            adapter.points = points
            start = min(native_period(p.period, d, p.event_id).start for p in points)
            end = max(native_period(p.period, d, p.event_id).start for p in points)
            engine.create_generation(
                d.id, [Window(start, end)], generation_id=f"catalog_{d.id}"
            )
            # Finish this selection before changing the fixture adapter's response.
            for _ in range(10):
                result = engine.run_once()
                assert result["state"] != "failed", result
                if result["state"] == "idle":
                    break
            else:
                raise AssertionError("Fixture exceeded bound")
    with store.connection(True) as db:
        for d in definitions:
            db.execute(
                "UPDATE norm_datasets SET public_display=1,rights_state='permitted' WHERE id=?",
                (d.id,),
            )
            db.execute(
                "INSERT INTO catalog_scope_reviews VALUES(?,?,?,?,?,?,?)",
                (
                    d.id,
                    "public_display",
                    "permitted",
                    1,
                    "SYNTHETIC_TEST_APPROVAL",
                    d.fingerprint,
                    "2026-02-01T00:00:00+00:00",
                ),
            )
    return NativeReader(
        store.path, publications, now_fn=lambda: datetime(2026, 2, 1, tzinfo=UTC)
    )
