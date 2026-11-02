"""Bounded official network/parser checks in a newly created disposable database.

No production reads, publication, scheduling or observation-table writes.
No raw responses/observations are included in the report.
"""

import argparse
import json
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path

from backend.app.catalog.releases import candidates, migrate as releases
from backend.app.ingestion.catalog_refresh import CONFIG, CatalogRefresh, migrate
from backend.app.ingestion.partition_schema import migrate as native
from backend.app.v2.state import Store


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--all",
        action="store_true",
        help="Check all 150 current-route candidates; default one per provider plus ONS construction",
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="catalog-source-check-") as directory:
        root = Path(directory)
        store = Store(root / "disposable.sqlite3")
        with store.connection(True) as db:
            native(db)
            releases(db)
            migrate(db)
        rules = [
            r
            for r in json.loads(CONFIG.read_text())["datasets"]
            if r["automation_ready"]
        ]
        pubs = candidates()
        if not args.all:
            providers = set()
            selected = []
            for row in rules:
                provider = pubs[row["id"]].definition.provider
                if provider not in providers or row["id"] == "ons_f069edbcf1bc4e7ff9c5":
                    selected.append(row)
                    providers.add(provider)
            rules = selected
        config = root / "policy.json"
        config.write_text(
            json.dumps(
                {
                    "datasets": [
                        r | {"ingest_approved": True, "mode": "stage"} for r in rules
                    ]
                }
            )
        )
        engine = CatalogRefresh(store, config=config)
        blocked, results = set(), []
        for row in rules:
            key = row["id"]
            provider = pubs[key].definition.provider
            before = time.perf_counter()
            try:
                if provider in blocked:
                    raise ValueError("provider_cooldown")
                pending, _ = engine._download(
                    key,
                    {
                        "etag": None,
                        "last_modified": None,
                        "content_hash": None,
                        "raw_hash": None,
                    },
                )
                assert pending is not None
                frozen = json.loads(Path(pending["path"]).read_text())
                results.append(
                    {
                        "id": key,
                        "provider": provider,
                        "state": "source_validated",
                        "rows": len(frozen["points"]),
                        "source_hash": frozen["source_hash"],
                        "definition_hash": frozen["definition_hash"],
                        "source_url": frozen["source_url"],
                    }
                )
                Path(pending["path"]).unlink()
            except Exception as exc:  # noqa: BLE001 -- independent bounded checks
                code = getattr(exc, "code", "source_validation_failed")
                if code == "http_429":
                    blocked.add(provider)
                results.append(
                    {"id": key, "provider": provider, "state": "blocked", "code": code}
                )
            results[-1]["seconds"] = round(time.perf_counter() - before, 3)
            print(json.dumps(results[-1]), flush=True)
            time.sleep(0.15)
        report = {
            "checked_at": datetime.now(UTC).isoformat(),
            "validated": sum(r["state"] == "source_validated" for r in results),
            "checked": len(results),
            "production_access": False,
            "observations_ingested": 0,
            "datasets": results,
        }
        if Path("/proc/self/status").exists():
            from scripts.linux_cgroup import snapshot

            report["memory"] = {
                line.split(":")[0]: line.split(":")[1].strip()
                for line in Path("/proc/self/status").read_text().splitlines()
                if line.startswith(("VmRSS:", "VmHWM:"))
            }
            report["cgroup"] = snapshot()
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + "\n")
        if report["validated"] != report["checked"]:
            raise SystemExit(
                "Some official source checks failed; see report, do not count them as verified"
            )


if __name__ == "__main__":
    main()
