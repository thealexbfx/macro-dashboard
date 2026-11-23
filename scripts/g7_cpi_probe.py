"""Verify direct official CPI transport without opening a database."""

import argparse
import json
from hashlib import sha256

from backend.app.ingestion.contracts import ProviderError
from backend.app.ingestion.g7_cpi import configuration, parse_history, resolve
from backend.app.ingestion.official_snapshots import download


def probe():
    _, publications, entries = configuration()
    responses = {}
    failures = {}
    receipts = []

    def fetch(url, **kwargs):
        if url in failures:
            raise failures[url]
        if url not in responses:
            try:
                responses[url] = download(url, **kwargs)
            except ProviderError as exc:
                failures[url] = exc
                raise
        return responses[url]

    for key, entry in entries.items():
        definition = publications[key].definition
        url = entry.get("landing", publications[key].source_url)
        try:
            url, release = resolve(entry, fetch)
            maximum = 32 * 1024**2 if definition.provider == "statcan_cpi" else 8 * 1024**2
            body, response = fetch(url, maximum=maximum)
            if not body:
                raise ProviderError("empty_publisher_response")
            _, points, _ = parse_history(definition, entry, body, release)
            receipts.append({
                "id": key,
                "state": "direct_https_validated",
                "endpoint": url,
                "resolved_endpoint": response["url"],
                "discovery_endpoint": release["discovery_url"],
                "release_date": release["release_date"],
                "sha256": sha256(body).hexdigest(),
                "first_period": points[0].period,
                "last_period": points[-1].period,
                "periods": len(points),
                "values": sum(point.value is not None for point in points),
                "etag": response.get("etag"),
                "last_modified": response.get("last_modified"),
            })
        except ProviderError as exc:
            receipts.append({"id": key, "state": "blocked", "endpoint": url, "error": exc.code})
    return receipts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    receipts = probe()
    print(json.dumps(receipts, indent=2))
    return int(any(receipt["state"] != "direct_https_validated" for receipt in receipts))


if __name__ == "__main__":
    raise SystemExit(main())
