"""Explicit read/compare-only release checks; never publication, AI or ingestion."""

import argparse
import json
from urllib.request import Request, urlopen
from urllib.error import HTTPError

from backend.app.catalog.rollout import load_plan, PRIVATE


def checks(request):
    plan = load_plan()
    expected = set(plan["baseline_ids"]) | {r["id"] for r in plan["datasets"]}
    ids = set()
    offset = 0
    while True:
        code, data = request("GET", f"/api/v2/catalog?offset={offset}&limit=100")
        assert code == 200 and data["total"] == len(expected)
        page = {r["id"] for r in data["items"]}
        assert not page & ids
        ids |= page
        if data["next_offset"] is None:
            break
        offset = data["next_offset"]
    assert ids == expected
    denied = 0
    for key in PRIVATE:
        for path in (
            f"/api/v2/catalog/{key}",
            f"/api/v2/datasets/{key}",
            f"/api/v2/observations/{key}?start=1960-01-01&end=2020-01-01",
        ):
            assert request("GET", path)[0] in {404, 422}
            denied += 1
        assert request(
            "POST",
            "/api/v2/compare",
            {"datasets": [key, "cpi"], "start": "2020-01-01", "end": "2021-01-01"},
        )[0] in {404, 422}
        denied += 1
    for key in sorted(ids - set(v for v in plan["baseline_ids"])):
        # Every new ID gets a bounded on-demand range and metadata check.
        assert request("GET", f"/api/v2/catalog/{key}")[0] == 200
        code, data = request(
            "GET",
            f"/api/v2/observations/{key}?start=2020-01-01&end=2021-01-01&limit=40",
        )
        assert code == 200 and data["dataset"]["id"] == key
    return {
        "public": len(ids),
        "private_denials": denied,
        "new_dataset_ranges": len(plan["datasets"]),
        "production_writes": 0,
        "ai_requests": 0,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--origin", required=True)
    parser.add_argument("--approved-live-read-checks", action="store_true")
    args = parser.parse_args()
    if (
        args.origin
        not in {
            "http://127.0.0.1:8000",
            "https://macrolens-v2-backend.onrender.com",
            "https://www.macrolensresearch.com",
        }
        or not args.approved_live_read_checks
    ):
        parser.error("Explicit approved origin and read-check approval required")

    def request(method, path, body=None):
        req = Request(
            args.origin + path,
            data=json.dumps(body).encode() if body is not None else None,
            method=method,
            headers={"Content-Type": "application/json"},
        )
        try:
            with urlopen(req, timeout=60) as response:
                return response.status, json.load(response)
        except HTTPError as exc:
            return exc.code, {}

    print(json.dumps(checks(request)))


if __name__ == "__main__":
    main()
