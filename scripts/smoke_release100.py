"""Read/query-only release smoke. No saves, AI, ingestion or rights mutations."""

import argparse
import json
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from backend.app.catalog.release100 import PRIVATE, load_plan
from backend.app.catalog.manifest import LEGACY_PUBLIC_SOURCES


def checks(request):
    plan = load_plan()
    expected = set(LEGACY_PUBLIC_SOURCES) | set(
        plan["existing_native_ids"] + plan["additional_ids"]
    )
    status, page = request("GET", "/api/v2/catalog?limit=100")
    assert (
        status == 200
        and page["total"] == 100
        and {r["id"] for r in page["items"]} == expected
    )
    for key in expected:
        status, meta = request("GET", "/api/v2/catalog/" + key)
        assert status == 200 and meta["id"] == key, key
        if key not in LEGACY_PUBLIC_SOURCES:
            assert meta["stored_provenance"]["ai_allowed"] is False
            assert meta["stored_provenance"]["attribution"]
            status, observations = request(
                "GET",
                f"/api/v2/observations/{key}?start=2020-01-01&end=2025-12-31&limit=40",
            )
            assert status == 200 and any(
                p["value"] is not None for p in observations["dataset"]["observations"]
            ), key
    for key in PRIVATE:
        for route in ("catalog", "observations", "datasets"):
            assert request("GET", f"/api/v2/{route}/{key}")[0] == 404
        assert request(
            "POST",
            "/api/v2/compare",
            {"datasets": [key], "start": "2020-01-01", "end": "2021-01-01"},
        )[0] in {404, 422}
    pairs = [plan["existing_native_ids"][:2], plan["additional_ids"][:2]]
    for ids in pairs:
        status, result = request(
            "POST",
            "/api/v2/compare",
            {"datasets": ids, "start": "2020-01-01", "end": "2025-12-31"},
        )
        assert status == 200 and {s["id"] for s in result["series"]} == set(ids)
    return {
        "public_ids": 100,
        "private_denials": 12,
        "comparisons": 2,
        "server_mutations": 0,
        "ai_requests": 0,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--origin", required=True)
    parser.add_argument("--approved-live-read-checks", action="store_true")
    args = parser.parse_args()
    origin = args.origin.rstrip("/")
    part = urlsplit(origin)
    if part.hostname not in {"127.0.0.1", "localhost"} and (
        origin
        not in {
            "https://macrolens-v2-backend.onrender.com",
            "https://www.macrolensresearch.com",
        }
        or not args.approved_live_read_checks
    ):
        parser.error("Explicit approved live origin required")

    def request(method, path, body=None):
        req = Request(
            origin + path,
            method=method,
            data=json.dumps(body).encode() if body is not None else None,
            headers={"Content-Type": "application/json"},
        )
        for _ in range(4):
            try:
                with urlopen(req, timeout=30) as response:
                    return response.status, json.load(response)
            except HTTPError as exc:
                if exc.code not in {429, 503}:
                    return exc.code, {}
                import time

                time.sleep(2)
        raise RuntimeError("Read smoke remained busy; stop release and inspect")

    print(json.dumps(checks(request)))


if __name__ == "__main__":
    main()
