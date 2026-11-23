"""Serve captured G7 histories through the research APIs on loopback only."""
import argparse
import json
import os
import sqlite3
from contextlib import closing
from pathlib import Path

from backend.app.catalog.releases import migrate as migrate_releases
from backend.app.ingestion.g7_cpi import configuration
from backend.app.ingestion.native import Definition, Observation, SourceCalendar, native_period
from backend.app.ingestion.official_snapshots import SnapshotAdapter, freeze
from backend.app.ingestion.partition_contracts import Window
from backend.app.ingestion.partitioned import PartitionedIngestion
from backend.app.ingestion.partition_schema import migrate
from backend.app.v2.catalog_api import PublicCatalog
from backend.app.v2.native_reader import NativePublication, NativeReader
from backend.app.v2.state import Store

SERIES = {
    "CA-01": ("Canada real GDP", "statcan", "quarterly", "Million chained 2017 CAD, annual rate", "v62305752"),
    "CA-11": ("Canada unemployment", "statcan", "monthly", "Percent", "v2062815"),
    "CA-22": ("Canada overnight policy-rate target", "boc", "daily", "Percent", "V39079"),
    "CA-23": ("Canada 10-year benchmark yield", "boc", "daily", "Percent", "BD.CDN.10YR.DQ.YLD"),
    "GB-23": ("UK 10-year nominal gilt par yield", "boe", "daily", "Percent per annum", "IUDMNPY"),
    **{
        f"{area}-23": (f"{name} 10-year government convergence yield", "ecb", "monthly", "Percent", f"IRS.M.{area}.L.L40.CI.0000.EUR.N.Z")
        for area, name in (("DE", "Germany"), ("FR", "France"), ("IT", "Italy"))
    },
    "FR-01": ("France real GDP (INSEE)", "insee", "quarterly", "Millions of chained 2020 euros", "011794860"),
    "FR-07": ("France headline CPI (INSEE)", "insee", "monthly", "2025=100", "011814630"),
    "FR-11": ("France unemployment excluding Mayotte (INSEE)", "insee", "quarterly", "Percent", "001688527"),
    "US-07": ("US headline CPI, all urban consumers (BLS)", "bls", "monthly", "1982-1984=100", "CUUR0000SA0"),
    "US-11": ("US unemployment, U-3 (BLS)", "bls", "monthly", "Percent", "LNS14000000"),
    "JP-01": ("Japan real GDP", "esri", "quarterly", "Billions of chained 2020 yen, annual rate", "gaku-jk2622"),
    "JP-11": ("Japan unemployment", "estat", "monthly", "Percent", "1-a-1/both-sexes"),
    "JP-23": ("Japan 10-year government constant-maturity yield", "mof_jp", "daily", "Percent", "10Y"),
}


def preview_series():
    """The hosted profile excludes BLS, whose metadata server denies runner access."""
    profile = os.getenv("MACROLENS_G7_CAPTURE_PROFILE", "full")
    if profile == "full":
        return SERIES
    if profile == "hosted":
        return {suffix: series for suffix, series in SERIES.items() if series[1] != "bls"}
    raise ValueError(f"Unknown G7 capture profile: {profile}")


class PreviewCatalog(PublicCatalog):
    def page(self, **filters):
        return super().page(**filters) | {"scope": "private_preview"}


class PreviewReader(NativeReader):
    def _permission(self, db, key):
        publication = self.publications[key]
        active = db.execute(
            """SELECT g.* FROM norm_dataset_state s
               JOIN norm_generations g ON g.id=s.active_generation AND g.dataset_id=s.dataset_id
               JOIN norm_datasets d ON d.id=s.dataset_id
               WHERE s.dataset_id=? AND d.public_display=0 AND d.rights_state='unreviewed'
               AND d.ai_allowed=0 AND d.discovery_allowed=0""",
            (key,),
        ).fetchone()
        self._receipt(db, publication.definition, active, verify_hash=False)
        return publication, active

    def _metadata(self, publication, db):
        result = super()._metadata(publication, db)
        result["stored_provenance"]["license_url"] = None
        result["message"] = "Private development preview. Source rights review pending."
        return result


def period_key(suffix, period):
    if suffix == "CA-01":
        year, month = period.split("-")
        return f"{year}-Q{(int(month) - 1) // 3 + 1}"
    return period


def import_cpi(store, source_path):
    """Copy only the CPI native histories and their ingestion proof records."""
    _, configs, entries = configuration()
    publications = {
        key: NativePublication(
            config.definition, f"{'Canada' if key.startswith('ca_') else 'Japan'} CPI: {entries[key]['label']}",
            "G7 core", "CA" if key.startswith("ca_") else "JP",
            config.source_url, entries[key]["licence"],
            (f"Official source: {config.source_url}",), "PRIVATE_PREVIEW_RIGHTS_PENDING",
            ("Publisher history captured for private development. Release rights pending.",),
        )
        for key, config in configs.items()
    }
    with closing(sqlite3.connect(source_path.resolve().as_uri() + "?mode=ro", uri=True)) as source:
        source.execute("PRAGMA query_only=ON")
        source.execute("BEGIN")
        rows = source.execute(
            "SELECT id, definition_hash, public_display, rights_state, ai_allowed, discovery_allowed FROM norm_datasets"
        ).fetchall()
        expected = {
            (key, config.definition.fingerprint, 0, "unreviewed", 0, 0)
            for key, config in configs.items()
        }
        if set(rows) != expected or source.execute("SELECT 1 FROM catalog_release_grants LIMIT 1").fetchone():
            raise ValueError("Expected a private six-series CPI audit database")
        # Refreshes can retain unchanged observations with their original proofs.
        generations = (
            "SELECT active_generation FROM norm_dataset_state "
            "UNION SELECT generation_id FROM norm_observations"
        )
        tables = {
            "norm_datasets": "",
            "norm_generations": f" WHERE id IN ({generations})",
            "norm_partitions": f" WHERE generation_id IN ({generations})",
            "norm_pages": f""" WHERE partition_id IN (
                SELECT id FROM norm_partitions WHERE generation_id IN ({generations}))""",
            "norm_dataset_state": "",
            "norm_staged": f" WHERE generation_id IN ({generations})",
            "catalog_staging_receipts": f" WHERE generation_id IN ({generations})",
            "catalog_staging_digests": f" WHERE generation_id IN ({generations})",
            "norm_observations": f" WHERE generation_id IN ({generations})",
            "catalog_dataset_completeness": f" WHERE batch_id IN ({generations})",
        }
        with store.connection(True) as target:
            for table, condition in tables.items():
                names = [row[1] for row in target.execute(f"PRAGMA table_info({table})")]
                columns = ", ".join(names)
                result = source.execute(f"SELECT {columns} FROM {table}{condition}")
                placeholders = ", ".join("?" for _ in names)
                target.executemany(f"INSERT INTO {table} ({columns}) VALUES ({placeholders})", result)
    reader = PreviewReader(store.path, publications)
    with reader.connection() as db:
        for key, publication in publications.items():
            _, generation = reader._permission(db, key)
            reader._receipt(db, publication.definition, generation)
    return publications


def stage(receipts, workspace, *, cpi_database=None, include_destatis_cpi=False, include_destatis_gdp=False):
    workspace.mkdir()
    store = Store(workspace / "private-g7.sqlite3")
    with store.connection(True) as db:
        migrate(db)
        migrate_releases(db)
    publications = import_cpi(store, cpi_database) if cpi_database else {}
    series = preview_series()
    if include_destatis_cpi:
        series = series | {"DE-07": ("Germany headline CPI (Destatis)", "destatis",
                                      "monthly", "2020=100", "61111-0002/PREIS1/DG")}
    if include_destatis_gdp:
        series = series | {"DE-01": ("Germany real GDP (Destatis)", "destatis",
                                      "quarterly", "Volume index, 2020=100", "2180130/1.1/I")}
    for suffix, (name, provider, frequency, units, selector) in series.items():
        mapping = "G7-" + suffix
        path = receipts / f"{mapping}.json"
        with path.open("rb") as source:
            raw = source.read(8 * 1024**2 + 1)
        if len(raw) > 8 * 1024**2:
            raise ValueError(f"Receipt exceeds budget: {mapping}")
        payload = json.loads(raw)
        if (payload.get("mapping", payload.get("mapping_id")) != mapping
            or payload.get("rights_status") != "PENDING"
            or payload.get("production_approval") != "NOT_APPROVED"):
            raise ValueError(f"Unexpected receipt identity or rights status: {mapping}")
        source_url = payload.get("source_url") or payload["sources"]["history"]["url"]
        adjustment = (
            "Seasonally and working-day adjusted" if suffix in {"FR-01", "DE-01"}
            else "Seasonally adjusted" if suffix.endswith(("-01", "-11"))
            else "Not seasonally adjusted"
        )
        dataset = Definition(mapping.lower().replace("-", "_"), provider, selector, units, frequency,
                             adjustment, SourceCalendar(f"{provider}_{frequency}"))
        points = tuple(
            Observation(period_key(suffix, row["period"]), row["period"], None if row["value"] is None else float(row["value"]),
                        (str(flag),) if (flag := row.get("publisher_flag") or row.get("publisher_status") or row.get("status")) else ())
            for row in payload["observations"]
        )
        snapshot, checksum = freeze(workspace / "snapshots", dataset, points, raw, source_url)
        adapter = SnapshotAdapter(snapshot, checksum, cache_parsed=True)
        engine = PartitionedIngestion(store, [dataset], {provider: adapter}, max_generation_rows=20000)
        dates = [native_period(point.period, dataset).start for point in points]
        engine.create_generation(dataset.id, [Window(min(dates), max(dates))])
        for _ in range(250):
            status = engine.run_once()
            if status["state"] == "idle":
                break
            if status["state"] == "failed":
                raise RuntimeError(status)
        else:
            raise RuntimeError(f"Capture exceeded staging budget: {mapping}")
        publications[dataset.id] = NativePublication(
            dataset, name, "G7 core", suffix[:2], source_url, source_url,
            (f"Official source: {source_url}",), "PRIVATE_PREVIEW_RIGHTS_PENDING",
            ("Publisher history captured for private development. Release rights pending.",),
        )
    return store, PreviewReader(store.path, publications)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("receipts", type=Path)
    parser.add_argument("new_workspace", type=Path)
    parser.add_argument("--cpi-database", type=Path, help="Private six-series CPI audit SQLite database")
    parser.add_argument("--include-destatis-cpi", action="store_true",
                        help="Load the separately exported G7-DE-07 receipt")
    parser.add_argument("--include-destatis-gdp", action="store_true",
                        help="Load the separately captured G7-DE-01 receipt")
    parser.add_argument("--port", type=int, default=8140)
    args = parser.parse_args()
    store, reader = stage(args.receipts, args.new_workspace, cpi_database=args.cpi_database,
                          include_destatis_cpi=args.include_destatis_cpi,
                          include_destatis_gdp=args.include_destatis_gdp)
    os.environ.update(MACROLENS_V2_STATE_DB=str(store.path), MACROLENS_AI_ENABLED="false",
                      MACROLENS_INGESTION_ENABLED="0", MACROLENS_CATALOG_REFRESH_ENABLED="0")
    import uvicorn
    from starlette.middleware.trustedhost import TrustedHostMiddleware

    from backend.app.v2 import main as v

    def unavailable(*_args, **_kwargs):
        raise ValueError("Legacy observations are outside this private preview")

    v.legacy_service.provider.fred_series = unavailable
    v.legacy_service.provider.market_series = unavailable
    v.refresh_scheduler.start = lambda: None
    v.public_catalog = PreviewCatalog(v.legacy_service, v.service.reader, reader)
    v.app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost"])
    uvicorn.run(v.app, host="127.0.0.1", port=args.port)


if __name__ == "__main__":
    main()
