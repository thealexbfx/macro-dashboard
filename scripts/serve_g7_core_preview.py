"""Serve captured G7 histories through the research APIs on loopback only."""
import argparse
import json
import os
from pathlib import Path

from backend.app.ingestion.native import Definition, Observation, SourceCalendar, native_period
from backend.app.ingestion.official_snapshots import SnapshotAdapter, freeze
from backend.app.ingestion.partition_contracts import Window
from backend.app.ingestion.partitioned import PartitionedIngestion
from backend.app.ingestion.partition_schema import migrate
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
    "JP-01": ("Japan real GDP", "esri", "quarterly", "Billions of chained 2020 yen, annual rate", "gaku-jk2622"),
    "JP-11": ("Japan unemployment", "estat", "monthly", "Percent", "1-a-1/both-sexes"),
    "JP-23": ("Japan 10-year government constant-maturity yield", "mof_jp", "daily", "Percent", "10Y"),
}


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


def stage(receipts, workspace):
    workspace.mkdir()
    store = Store(workspace / "private-g7.sqlite3")
    with store.connection(True) as db:
        migrate(db)
    publications = {}
    for suffix, (name, provider, frequency, units, selector) in SERIES.items():
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
        adjustment = "Seasonally adjusted" if suffix.endswith(("-01", "-11")) else "Not seasonally adjusted"
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
    parser.add_argument("--port", type=int, default=8140)
    args = parser.parse_args()
    store, reader = stage(args.receipts, args.new_workspace)
    os.environ.update(MACROLENS_V2_STATE_DB=str(store.path), MACROLENS_AI_ENABLED="false",
                      MACROLENS_INGESTION_ENABLED="0", MACROLENS_CATALOG_REFRESH_ENABLED="0")
    import uvicorn
    from starlette.middleware.trustedhost import TrustedHostMiddleware

    from backend.app.v2 import main as v
    from backend.app.v2.catalog_api import PublicCatalog

    def unavailable(*_args, **_kwargs):
        raise ValueError("Legacy observations are outside this private preview")

    v.legacy_service.provider.fred_series = unavailable
    v.legacy_service.provider.market_series = unavailable
    v.refresh_scheduler.start = lambda: None
    v.public_catalog = PublicCatalog(v.legacy_service, v.service.reader, reader)
    v.app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost"])
    uvicorn.run(v.app, host="127.0.0.1", port=args.port)


if __name__ == "__main__":
    main()
