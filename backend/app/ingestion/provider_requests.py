"""Explicit schema-5, durable free-provider quotas and immutable response reuse.

Counts are reserved before network I/O, including failures. This is a local budget,
not a claim about other applications sharing the same provider/IP quota.
"""

import json
import time
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from pathlib import Path

from backend.app.ingestion.contracts import ProviderError


def migrate(db):
    if not db.execute(
        "SELECT 1 FROM catalog_schema_versions WHERE version=4"
    ).fetchone():
        raise ValueError("Schema 4 required before explicit schema 5")
    db.execute("""CREATE TABLE IF NOT EXISTS catalog_provider_requests (
        provider TEXT NOT NULL, day TEXT NOT NULL, request_hash TEXT NOT NULL,
        attempts INTEGER NOT NULL, response_path TEXT, response_hash TEXT,
        response_metadata TEXT, PRIMARY KEY(provider,day,request_hash))""")
    db.execute(
        "INSERT OR IGNORE INTO catalog_schema_versions VALUES(5,'durable_provider_request_budgets')"
    )


class Requests:
    def __init__(self, store, fetch, directory, now=None):
        self.store, self.fetch, self.directory = store, fetch, Path(directory)
        self.now = now or (lambda: datetime.now(UTC))

    def get(self, provider, url, *, payload=None, quota=24, **kwargs):
        if provider not in {"bls", "dol"} or not 1 <= quota <= 24:
            raise ValueError("Unreviewed request quota")
        self.directory.mkdir(parents=True, exist_ok=True)
        if sum(p.stat().st_size for p in self.directory.glob("*.raw")) > 24 * 1024**2:
            raise ProviderError("provider_cache_budget")
        day = self.now().date().isoformat()
        request = sha256(url.encode() + b"\0" + (payload or b"")).hexdigest()
        with self.store.connection(True, timeout=2) as db:
            cached = db.execute(
                "SELECT * FROM catalog_provider_requests WHERE provider=? AND day=? AND request_hash=?",
                (provider, day, request),
            ).fetchone()
            if cached and cached["response_path"]:
                path = Path(cached["response_path"])
                if (
                    path.resolve().parent != self.directory.resolve()
                    or path.is_symlink()
                    or path.stat().st_size > 8 * 1024**2
                ):
                    raise ProviderError("provider_cache_invalid")
                body = path.read_bytes()
                if sha256(body).hexdigest() != cached["response_hash"]:
                    raise ProviderError("provider_cache_invalid")
                return body, json.loads(cached["response_metadata"])
            used = db.execute(
                "SELECT COALESCE(SUM(attempts),0) FROM catalog_provider_requests WHERE provider=? AND day=?",
                (provider, day),
            ).fetchone()[0]
            if used >= quota:
                error = ProviderError("provider_daily_budget")
                midnight = (self.now() + timedelta(days=1)).replace(
                    hour=0, minute=0, second=0, microsecond=0
                )
                error.retry_after = max(
                    300, int((midnight - self.now()).total_seconds())
                )
                raise error
            db.execute(
                "INSERT INTO catalog_provider_requests(provider,day,request_hash,attempts) VALUES(?,?,?,1) ON CONFLICT(provider,day,request_hash) DO UPDATE SET attempts=attempts+1",
                (provider, day, request),
            )
        body, response = self.fetch(url, payload=payload, **kwargs)
        if not body or len(body) > 8 * 1024**2:
            raise ProviderError("provider_empty_or_oversized")
        digest = sha256(body).hexdigest()
        path = self.directory / (digest + ".raw")
        try:
            with path.open("xb") as out:
                out.write(body)
        except FileExistsError:
            if sha256(path.read_bytes()).hexdigest() != digest:
                raise ProviderError("provider_cache_invalid")
        with self.store.connection(True, timeout=2) as db:
            db.execute(
                "UPDATE catalog_provider_requests SET response_path=?,response_hash=?,response_metadata=? WHERE provider=? AND day=? AND request_hash=?",
                (str(path), digest, json.dumps(response), provider, day, request),
            )
        return body, response

    def prune(self):
        cutoff = (self.now().date() - timedelta(days=2)).isoformat()
        with self.store.connection(True, timeout=2) as db:
            db.execute("DELETE FROM catalog_provider_requests WHERE day < ?", (cutoff,))
            keep = {
                r[0]
                for r in db.execute(
                    "SELECT response_path FROM catalog_provider_requests WHERE response_path IS NOT NULL"
                )
            }
        for path in self.directory.glob("*.raw"):
            if str(path) not in keep:
                path.unlink(missing_ok=True)


def bls_group(entries, requests, *, start=1910):
    """One shared 12-request maximum history, reused for all nine selections.

    Full monthly history is deliberate: BLS seasonal/benchmark revisions can reach
    beyond two years. No partial response is silently merged into a full history.
    """
    from backend.app.ingestion.bls_history import capture

    selectors = sorted(
        {e["source"]["selector"] for e in entries if e["source"]["provider"] == "bls"}
    )
    body, response = capture(
        selectors,
        start=start,
        end=requests.now().year,
        fetch=lambda url, **kw: requests.get("bls", url, **kw),
        pause=time.sleep,
    )
    # The unregistered API currently disables its catalog. Observation availability
    # is not definition verification; do not enable these public jobs prematurely.
    data = json.loads(body)
    expected = {
        e["source"]["selector"]: e.get("reviewed_catalog")
        for e in entries
        if e["source"]["provider"] == "bls"
    }
    for row in data["Results"]["series"]:
        if (
            not expected.get(row["seriesID"])
            or row.get("catalog") != expected[row["seriesID"]]
        ):
            raise ProviderError("bls_definition_metadata_unavailable")
    return body, response
