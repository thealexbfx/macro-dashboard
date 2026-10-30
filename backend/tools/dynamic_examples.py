"""Regenerate dated real-source evidence and explicitly labelled no-network fixtures.
Run from repository root. No AI call, secret lookup or production write.
"""

from __future__ import annotations

import argparse
import json
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory

import requests

from backend.app.v2.ai_guard import MODEL, AIGuard, BudgetBlocked
from backend.app.v2.main import Dataset
from backend.app.v2.memory import DiscoveryMemory
from backend.app.v2.state import Store


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--origin", default="http://127.0.0.1:8032")
    parser.add_argument("--output", default="frontend-v2/phase-3-2-evidence.json")
    args = parser.parse_args()
    report = requests.get(args.origin + "/api/v2/discovery", timeout=90).json()
    source_data = requests.get(args.origin + "/api/v2/datasets", timeout=60).json()
    report_again = requests.get(args.origin + "/api/v2/discovery", timeout=90).json()
    findings = report["findings"] + report["following"]
    out = {
        "captured_at_utc": datetime.now(UTC).isoformat(),
        "kind": "Real observations except the explicitly labelled isolated lifecycle/budget fixtures below. No paid AI calls.",
        "methodology_version": report["methodology_version"],
        "calculated_at": report["generated_at"],
        "source_times": report["source_times"],
        "current_findings": [
            {
                "id": f["id"],
                "headline": f["headline"],
                "key_number": f["key_number"],
                "horizon": f["horizon_label"],
                "observation_date": f["observation_date"],
                "lifecycle": f["lifecycle"],
                "suggestions": [
                    {"label": s["label"], "configuration": s["configuration"]}
                    for s in f.get("suggestions", [])
                ],
            }
            for f in findings
        ],
        "horizon_results": report["horizon_results"],
        "catalogue": [
            {
                "id": d["id"],
                "provider_id": d["provider_id"],
                "units": d["units"],
                "frequency": d["frequency"],
                "adjustment": d["seasonal_adjustment"],
                "status": d["status"],
                "coverage_start": d["coverage_start"],
                "latest_observation_date": d["latest_observation_date"],
                "latest_value": d["latest_value"],
                "source_url": d["source_url"],
            }
            for d in source_data
        ],
        "historical": [
            {
                "id": h["id"],
                "label": h["label"],
                "historical_start": h["snapshot"]["pattern"]["observations"][0]["date"],
                "historical_end": h["snapshot"]["pattern"]["observations"][-1]["date"],
                "finding": h["snapshot"]["finding"]["headline"],
                "current_start": h["current_pattern"]["observations"][0]["date"]
                if h["current_pattern"]
                else None,
                "current_end": h["current_pattern"]["observations"][-1]["date"]
                if h["current_pattern"]
                else None,
                "similarity": h["similarity"],
                "notes": h["notes"],
            }
            for h in report["historical"]
        ],
        "unchanged_scan": {
            "same_calculation_time": report["generated_at"]
            == report_again["generated_at"],
            "same_identity_and_versions": [
                (f["id"], f["evidence_version"]) for f in findings
            ]
            == [
                (f["id"], f["evidence_version"])
                for f in report_again["findings"] + report_again["following"]
            ],
        },
    }
    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix="macrolens-proof-", dir=output.parent) as temp:
        temp = Path(temp)
        now = datetime.now(UTC)
        f = deepcopy(next(f for f in findings if f["type"] == "unusual"))
        data = [Dataset.model_validate(d) for d in source_data]
        store = Store(temp / "memory.db")
        m = DiscoveryMemory(store)
        m.apply([f], data, now)
        a = m.list({f["event_key"]}, data, now)[0]
        m = DiscoveryMemory(Store(store.path))
        m.apply([f], data, now + timedelta(days=1))
        b = m.list({f["event_key"]}, data, now + timedelta(days=1))[0]
        changed = deepcopy(f)
        changed["evidence"]["movement"] *= 2
        changed["evidence"]["standardized_magnitude"] *= 2
        m.apply([changed], data, now + timedelta(days=2))
        c = m.list({f["event_key"]}, data, now + timedelta(days=2))[0]
        out["lifecycle_fixture"] = {
            "label": "Isolated synthetic evidence update based on a real snapshot; NOT inserted into application Radar.",
            "stable_id_after_restart": a["id"] == b["id"] == c["id"],
            "statuses": [
                a["lifecycle"]["status"],
                b["lifecycle"]["status"],
                c["lifecycle"]["status"],
            ],
            "versions": [
                a["evidence_version"],
                b["evidence_version"],
                c["evidence_version"],
            ],
            "last_meaningful_unchanged_on_repeat": a["lifecycle"][
                "last_meaningful_update"
            ]
            == b["lifecycle"]["last_meaningful_update"],
            "original_material_evidence_unchanged": c["history"][0]["evidence"][
                "movement"
            ]
            == a["history"][0]["evidence"]["movement"],
        }

        class TwoDollarGuard(AIGuard):
            @property
            def limit(self):
                return 2_000_000_000

        guard = TwoDollarGuard(Store(temp / "budget.db"), now_fn=lambda: now)
        p = {"model": MODEL, "input": 0.125, "output": 0.5}

        def reserve(n):
            try:
                guard.reserve("fixture:" + str(n), p)
                return True
            except BudgetBlocked:
                return False

        with ThreadPoolExecutor(max_workers=12) as pool:
            admitted = sum(pool.map(reserve, range(500)))
        out["budget_fixture"] = {
            "label": "Mock pricing and reservation-only concurrency proof; ZERO OpenAI requests.",
            "concurrent_attempts": 500,
            "admitted_reservations": admitted,
            "blocked": 500 - admitted,
            "usage": guard.usage(),
        }
    output.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf8")
    print(str(output))
    print(
        json.dumps(
            {
                "lifecycle": out["lifecycle_fixture"],
                "budget": out["budget_fixture"],
                "real_horizons": len(out["horizon_results"]),
                "historical": len(out["historical"]),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
