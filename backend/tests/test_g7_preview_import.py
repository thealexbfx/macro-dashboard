from datetime import date

from backend.app.catalog.releases import migrate as migrate_releases
from backend.app.ingestion.g7_cpi import configuration
from backend.app.ingestion.native import Observation
from backend.app.ingestion.official_snapshots import SnapshotAdapter, freeze
from backend.app.ingestion.partition_contracts import Window
from backend.app.ingestion.partition_schema import migrate
from backend.app.ingestion.partitioned import PartitionedIngestion
from backend.app.v2.state import Store
from scripts.serve_g7_core_preview import PreviewReader, import_cpi


def test_cpi_preview_retains_proofs_for_unchanged_observations_after_revision(tmp_path):
    source = Store(tmp_path / "source.sqlite3")
    with source.connection(True) as db:
        migrate(db)
        migrate_releases(db)
    key = "ca_cpi_all_items_nsa"
    definitions = configuration()[1]

    def ingest(publication, values, generation):
        definition = publication.definition
        points = tuple(
            Observation(f"2020-{month:02d}", f"2020-{month:02d}", value)
            for month, value in enumerate(values, start=1)
        )
        path, checksum = freeze(
            tmp_path / "snapshots", definition, points, b"SYNTHETIC CPI PROOF FIXTURE",
            publication.source_url,
        )
        engine = PartitionedIngestion(
            source, [definition],
            {definition.provider: SnapshotAdapter(path, checksum)},
            preserve_unchanged_rows=True, compact_completed_staging=True,
        )
        engine.create_generation(
            definition.id, [Window(date(2020, 1, 1), date(2020, 3, 31))],
            generation_id=generation,
        )
        for _ in range(10):
            result = engine.run_once()
            assert result["state"] != "failed", result
            if result["state"] == "idle":
                break
        else:
            raise AssertionError("Fixture failed to converge")

    for dataset, publication in definitions.items():
        ingest(publication, (100.0, 101.0, 102.0), dataset + "_initial")
    ingest(definitions[key], (100.0, 101.0, 103.0), key + "_revised")
    with source.connection() as db:
        assert db.execute(
            "SELECT count(DISTINCT generation_id) FROM norm_observations WHERE dataset_id=?",
            (key,),
        ).fetchone()[0] == 2

    target = Store(tmp_path / "preview.sqlite3")
    with target.connection(True) as db:
        migrate(db)
        migrate_releases(db)
    publications = import_cpi(target, source.path)
    reader = PreviewReader(target.path, publications)
    result = reader.observations(key, date(2020, 1, 1), date(2020, 3, 31))
    assert [point["value"] for point in result["dataset"]["observations"]] == [
        100.0, 101.0, 103.0,
    ]
    assert result["dataset"]["stored_provenance"]["generation_reference_count"] == 2
    with target.connection() as db:
        assert db.execute("SELECT count(*) FROM catalog_release_grants").fetchone()[0] == 0
        assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
