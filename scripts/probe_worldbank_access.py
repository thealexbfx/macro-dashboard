"""One official World Bank GET; no database, ingestion job, AI, redirects or retries.

Run from the repository root: python scripts/probe_worldbank_access.py
Production execution requires explicit operator approval. Output has no raw HTTP
headers, response bodies, provider values, credentials or environment variables.
"""

import argparse
import json
import platform
import ssl
import sys
import urllib.error
import urllib.request
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.app.ingestion.contracts import ProviderError
from backend.app.ingestion.world_bank import (
    MAX_BYTES,
    URL,
    WorldBank,
    response_diagnostics,
)


def probe(provider=None):
    provider = provider or WorldBank()
    result = {"python": platform.python_version(), "database_access": False}
    try:
        batch = provider.fetch()
        result.update(
            ok=True,
            checked_at=batch.checked_at.isoformat(),
            bytes=batch.byte_count,
            sha256=batch.source_hash,
            series={
                key: {
                    name: meta[name]
                    for name in (
                        "first_period",
                        "last_period",
                        "non_missing",
                        "missing",
                    )
                }
                for key, meta in batch.metadata.items()
            },
        )
    except ProviderError as exc:
        result.update(
            ok=False, error_code=exc.code, retry_after_seconds=exc.retry_after
        )
    result["download"] = provider.download_diagnostics
    return result


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def urllib_probe(opener=None):
    """Optional one-request comparison with the original CI client, no redirects."""
    opener = opener or urllib.request.build_opener(NoRedirect())
    try:
        with opener.open(URL, timeout=15) as response:
            result = response_diagnostics(
                SimpleNamespace(status_code=response.status, headers=response.headers)
            )
            body = response.read(MAX_BYTES + 1)
            result.update(
                bytes=len(body),
                sha256=sha256(body).hexdigest(),
                body_within_limit=len(body) <= MAX_BYTES,
            )
            return result
    except urllib.error.HTTPError as exc:
        # No denied body is read, retained, printed or retried.
        try:
            return response_diagnostics(
                SimpleNamespace(status_code=exc.code, headers=exc.headers)
            )
        finally:
            exc.close()
    except urllib.error.URLError as exc:
        return {
            "state": "tls_error"
            if isinstance(exc.reason, ssl.SSLError)
            else "provider_unavailable"
        }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--compare-urllib",
        action="store_true",
        help="One additional official GET with the original CI client",
    )
    args = parser.parse_args()
    output = probe()
    if args.compare_urllib:
        output["urllib_comparison"] = urllib_probe()
    print(json.dumps(output, indent=2))
    raise SystemExit(0 if output["ok"] else 2)
