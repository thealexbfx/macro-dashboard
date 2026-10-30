"""Record live and two predeclared retrospective examples via the running V2 API.

Historical outputs use today's revised data, NOT the information available at
that historical date. No historical release-availability/freshness claim.
Run from repo root: python -m backend.tools.discovery_examples --output outputs
"""

from __future__ import annotations

import argparse
import json
from datetime import date, timedelta
from pathlib import Path

import requests

from backend.app.v2.discovery import MODES, scan
from backend.app.v2.main import Dataset, transform


def record(origin: str, output: Path):
    response = requests.get(f"{origin}/api/v2/discovery", timeout=90)
    response.raise_for_status()
    current = response.json()
    output.mkdir(parents=True, exist_ok=True)
    (output / "phase-3-1-real-discoveries.json").write_text(
        json.dumps(current, indent=2), encoding="utf-8"
    )
    datasets = []
    ids = list(MODES)
    end = date.fromisoformat(current["as_of"]) - timedelta(days=1)
    for offset in range(0, len(ids), 4):
        response = requests.post(
            f"{origin}/api/v2/compare",
            json={
                "datasets": ids[offset : offset + 4],
                "start": "1990-01-01",
                "end": str(end),
                "alignment": "period_end",
                "rolling_window": 12,
            },
            timeout=60,
        )
        response.raise_for_status()
        payload = response.json()
        datasets.extend(
            Dataset(**{**meta, "observations": payload["raw_observations"][meta["id"]]})
            for meta in payload["datasets"]
        )
    historical = {}
    for cutoff in [date(2020, 7, 1), date(2022, 7, 1)]:
        historical[str(cutoff)] = {
            "context": "Retrospective replay using today's revised observations, not evidence available at the historical date. Source metadata reflect current retrieval, not past release availability or freshness. These two windows were preselected as pandemic/inflation examples before execution; selection and multiple-look bias remain. Not displayed as current findings.",
            "report": scan(datasets, transform, cutoff),
        }
    (output / "phase-3-1-historical-examples.json").write_text(
        json.dumps(historical, indent=2), encoding="utf-8"
    )
    return current, historical


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--origin", default="http://127.0.0.1:8031")
    parser.add_argument("--output", type=Path, default=Path("outputs"))
    args = parser.parse_args()
    current, historical = record(args.origin.rstrip("/"), args.output)
    print(f"Current scan: {len(current['findings'])} findings")
    for cutoff, payload in historical.items():
        print(
            cutoff, [(f["type"], f["datasets"]) for f in payload["report"]["findings"]]
        )
