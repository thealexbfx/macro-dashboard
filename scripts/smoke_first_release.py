"""Bounded read/query smoke checks. No ingestion, grants, AI or research writes."""

import argparse
import json
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from backend.app.v2.definitions import SPECS

SELECTION = (
    Path(__file__).resolve().parents[1] / "research/releases/first-live/selection.json"
)
PRIVATE = ("wb_brent_monthly", "wb_copper_monthly", "wb_iron_ore_monthly")


def checks(request, *, activated):
    selected = json.loads(SELECTION.read_text(encoding="utf-8"))["ids"]
    expected = set(SPECS) | (set(selected) if activated else set())
    status, page = request("GET", "/api/v2/catalog?limit=100")
    assert status == 200 and page["total"] == len(expected)
    assert {r["id"] for r in page["items"]} == expected
    for key in SPECS:
        status, metadata = request("GET", "/api/v2/catalog/" + key)
        assert status == 200 and metadata["id"] == key
    for key in selected:
        status, metadata = request("GET", "/api/v2/catalog/" + key)
        assert status == (200 if activated else 404), key
        if not activated:
            continue
        assert metadata["stored_provenance"]["ai_allowed"] is False
        assert metadata["stored_provenance"]["attribution"]
        assert metadata["stored_provenance"]["license_url"].startswith("https://")
        if metadata["provider"] == "eurostat":
            assert any(
                "Eurostat bears no responsibility" in n
                for n in metadata["known_limitations"]
            )
        status, data = request(
            "GET",
            f"/api/v2/observations/{key}?start=2019-01-01&end=2025-12-31&limit=1000",
        )
        assert status == 200 and data["dataset"]["id"] == key
        assert any(p["value"] is not None for p in data["dataset"]["observations"]), key
    denied = 0
    for key in PRIVATE:
        for route in ("catalog", "observations", "datasets"):
            status, _ = request("GET", f"/api/v2/{route}/{key}")
            assert status == 404, (key, route, status)
            denied += 1
        status, _ = request(
            "POST",
            "/api/v2/compare",
            {
                "datasets": [key],
                "start": "2020-01-01",
                "end": "2021-01-01",
            },
        )
        assert status in {404, 422}, (key, status)
        denied += 1
    comparisons = 0
    if activated:
        for ids in (selected[:2], selected[-3:-1]):
            status, result = request(
                "POST",
                "/api/v2/compare",
                {
                    "datasets": ids,
                    "start": "2019-01-01",
                    "end": "2025-12-31",
                    "transformations": {k: "indexed" for k in ids},
                },
            )
            assert status == 200 and {s["id"] for s in result["series"]} == set(ids)
            comparisons += 1
    return {
        "passed": True,
        "public_ids": len(expected),
        "private_denials": denied,
        "comparisons": comparisons,
        "server_mutations": 0,
        "ai_requests": 0,
    }


def network_request(origin):
    def request(method, path, body=None):
        req = Request(
            origin + path,
            data=json.dumps(body).encode() if body is not None else None,
            method=method,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "MacroLens-first-release-smoke",
            },
        )
        try:
            with urlopen(req, timeout=30) as response:
                if urlsplit(response.geturl()).netloc != urlsplit(origin).netloc:
                    raise ValueError("Unexpected smoke-check redirect")
                raw = response.read(2 * 1024 * 1024 + 1)
                if len(raw) > 2 * 1024 * 1024:
                    raise ValueError("Smoke response exceeds byte budget")
                return response.status, json.loads(raw)
        except HTTPError as exc:
            return exc.code, {}

    return request


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--origin", required=True)
    parser.add_argument("--activated", action="store_true")
    parser.add_argument("--approved-live-read-checks", action="store_true")
    args = parser.parse_args()
    parsed = urlsplit(args.origin)
    local = parsed.hostname in {"127.0.0.1", "localhost"} and parsed.scheme == "http"
    live = parsed.scheme == "https" and parsed.netloc in {
        "www.macrolensresearch.com",
        "macrolens-v2-backend.onrender.com",
    }
    if (
        parsed.path not in {"", "/"}
        or parsed.query
        or parsed.fragment
        or not (local or live and args.approved_live_read_checks)
    ):
        parser.error("Loopback or explicitly approved exact production origin required")
    print(
        json.dumps(
            checks(network_request(args.origin.rstrip("/")), activated=args.activated)
        )
    )
