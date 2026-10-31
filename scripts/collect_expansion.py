"""Development-only real-source validation; never reads production configuration.

python -m scripts.collect_expansion --workspace /new/disposable/directory
Outputs immutable local snapshots and per-selection results, never permissions.
"""

import argparse
import json
import time
from collections import Counter
from dataclasses import asdict
from pathlib import Path

from backend.app.ingestion.expansion_sources import PARSERS, parse_ons_construction
from backend.app.ingestion.federal_reserve_bulk import parse_selected
from backend.app.ingestion.official_snapshots import download, freeze
from backend.app.v2.definitions import SPECS

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--providers", default="eurostat,ons,oecd,ecb")
    parser.add_argument("--only-ids", nargs="*")
    parser.add_argument("--full-bls-history", action="store_true")
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Capture a new immutable revision; existing snapshots are retained",
    )
    parser.add_argument(
        "--reuse-local-workbooks",
        action="store_true",
        help="Reuse already downloaded workbook files in this disposable directory",
    )
    parser.add_argument(
        "--overrides",
        action="store_true",
        help="Use reviewed original-producer source overrides",
    )
    args = parser.parse_args()
    workspace = args.workspace.resolve()
    if str(workspace).startswith(("/var/", "/mnt/")) or workspace == ROOT:
        parser.error("Use a dedicated disposable development directory")
    workspace.mkdir(parents=True, exist_ok=True)
    marker = workspace / "DISPOSABLE_EXPANSION_ONLY"
    if not marker.exists() and any(workspace.iterdir()):
        parser.error("Refusing an existing unmarked directory")
    marker.touch()
    selected = set(args.providers.split(","))
    manifest = json.loads((ROOT / "catalog/datasets.json").read_text(encoding="utf-8"))[
        "datasets"
    ]
    if args.overrides:
        manifest = json.loads(
            (ROOT / "catalog/source_overrides.json").read_text(encoding="utf-8")
        )["datasets"]
    parsers = dict(PARSERS, federal_reserve=parse_selected)
    results = {}
    output = workspace / "source-results.json"
    if output.exists():
        results = json.loads(output.read_text(encoding="utf-8"))
        if args.refresh:
            from datetime import UTC, datetime

            stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
            (workspace / f"source-results-{stamp}.json").write_bytes(
                output.read_bytes()
            )
    stopped = set()
    downloads = {}
    for entry in manifest:
        key, provider = entry["id"], entry["source"]["provider"]
        if args.only_ids and key not in args.only_ids:
            continue
        if key in SPECS or key.startswith("wb_") or provider not in selected:
            continue
        if (
            not args.refresh
            and key in results
            and results[key].get("state") == "captured"
        ):
            continue
        start = time.perf_counter()
        try:
            if provider in stopped:
                raise ValueError(
                    "Provider rate limit reached; retry after its cooldown in a later run"
                )
            if entry["kind"] != "series" or provider not in parsers:
                raise ValueError("Exact atomic parser/selector not yet resolved")
            # Do not treat an XLSX URL as an ONS CDID JSON feed.
            workbook = provider == "ons" and ".xlsx" in entry["source"]["endpoint"]
            parse = parse_ons_construction if workbook else parsers[provider]
            endpoint = entry["source"]["endpoint"]
            if provider == "eia":
                code = entry["source"]["selector"].split(".")
                if code[0] not in {"PET", "NG"}:
                    raise ValueError(
                        "Electricity source needs a free EIA API credential or reviewed download"
                    )
                section = "ng" if code[0] == "NG" else "pet"
                endpoint = f"https://www.eia.gov/dnav/{section}/hist_xls/{code[1]}{code[2].lower()}.xls"
            cached = workspace / (key + ".xlsx")
            if workbook:
                cached = workspace / "ons-construction.xlsx"
            payload = None
            if provider == "federal_reserve":
                cached = workspace / (
                    entry["source"]["selector"].split("/")[0] + ".zip"
                )
            if provider == "bea":
                cached = workspace / (
                    "bea-section" + ("2" if "Section2" in endpoint else "1") + ".xlsx"
                )
            if provider == "bls":
                cached = workspace / ("bls-selected-full.json" if args.full_bls_history else "bls-selected.json")
                payload = json.dumps(
                    {
                        "seriesid": [
                            e["source"]["selector"]
                            for e in manifest
                            if e["source"]["provider"] == "bls"
                        ],
                        "startyear": "2017",
                        "endyear": "2026",
                    }
                ).encode()
            if (
                args.reuse_local_workbooks
                and (
                    provider
                    in {
                        "desnz",
                        "uk_building_materials",
                        "usgs",
                        "federal_reserve",
                        "bls",
                        "bea",
                    }
                    or workbook
                )
                and cached.exists()
            ):
                body, response = (
                    cached.read_bytes(),
                    {"url": endpoint, "development_cached_download": True},
                )
            else:
                if endpoint not in downloads:
                    downloads.clear()  # At most one complete official response resident.
                    if provider == "bls" and args.full_bls_history:
                        from backend.app.ingestion.bls_history import capture
                        downloads[endpoint] = capture(json.loads(payload)["seriesid"])
                        cached.write_bytes(downloads[endpoint][0])
                    else:
                        downloads[endpoint] = download(endpoint, payload=payload)
                body, response = downloads[endpoint]
            definition, points, metadata = parse(entry, body)
            target, snapshot = freeze(
                workspace / "snapshots",
                definition,
                points,
                body,
                endpoint,
                metadata | response,
            )
            valid = [p for p in points if p.value is not None]
            results[key] = {
                "state": "captured",
                "definition": asdict(definition),
                "snapshot_path": str(target),
                "snapshot_hash": snapshot,
                "observations": len(points),
                "nonnull": len(valid),
                "first": min(p.period for p in points),
                "last": max(p.period for p in points),
                "source_bytes": len(body),
                "metadata": metadata,
                "source_url": endpoint,
                "public_display": False,
                "ai_allowed": False,
                "discovery_allowed": False,
            }
        except Exception as exc:  # noqa: BLE001 -- independent datasets must continue; every failure is recorded
            if str(exc) == "http_429":
                stopped.add(provider)
            results[key] = {
                "state": "blocked",
                "reason": str(exc)[:180],
                "error_type": type(exc).__name__,
            }
        results[key]["seconds"] = round(time.perf_counter() - start, 3)
        output.write_text(
            json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        print(
            key,
            results[key]["state"],
            results[key].get("observations", results[key].get("reason")),
            flush=True,
        )
        time.sleep(0.15)  # Sequential, courteous official-source requests.
    print(dict(Counter(r["state"] for r in results.values())))


if __name__ == "__main__":
    main()
