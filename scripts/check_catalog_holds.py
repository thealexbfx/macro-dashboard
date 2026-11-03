"""Read-only checks of moving-source contracts. No ingestion or rights writes."""

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from backend.app.catalog.releases import candidates
from backend.app.ingestion.catalog_refresh import source_entries
from backend.app.ingestion.expansion_sources import PARSERS
from backend.app.ingestion.official_snapshots import download
from backend.app.ingestion.release_discovery import discover


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    pubs = candidates()
    cache = {}
    rows = []

    def fetch(url, **kw):
        if url not in cache:
            cache.clear()
            cache[url] = download(url, **kw)
        return cache[url]

    for key, entry in source_entries().items():
        if key not in pubs or entry["source"]["provider"] not in {
            "desnz",
            "uk_building_materials",
            "dol",
        }:
            continue
        provider = entry["source"]["provider"]
        row = {
            "id": key,
            "provider": provider,
            "publication_approved": False,
            "refresh_enabled": False,
        }
        try:
            if provider == "dol":
                from urllib.parse import urlencode

                params = dict(
                    entry["query_parameters"],
                    enddate=str(datetime.now(UTC).year),
                    final_yr=str(datetime.now(UTC).year + 1),
                )
                url = entry["source"]["endpoint"]
                body, _ = download(url, payload=urlencode(params).encode("ascii"))
            else:
                url, metadata = discover(entry, fetch=fetch)
                body, _ = fetch(url)
                row.update(metadata)
            definition, points, metadata = PARSERS[provider](entry, body)
            if definition.fingerprint != pubs[key].definition.fingerprint:
                raise ValueError("definition_drift")
            valid = [p for p in points if p.value is not None]
            row.update(
                state="candidate_contract_passed",
                source_url=url,
                rows=len(points),
                first=min(p.period for p in valid),
                last=max(p.period for p in valid),
                source_metadata=metadata,
                remaining="Moving artifact lineage, complete archive/revision reconciliation and persistent scheduler integration are not release-approved",
            )
        except Exception as exc:
            row.update(state="held", error=getattr(exc, "code", type(exc).__name__))
        rows.append(row)
        print(json.dumps(row), flush=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(
            {
                "checked_at": datetime.now(UTC).isoformat(),
                "production_access": False,
                "datasets": rows,
            },
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    main()
