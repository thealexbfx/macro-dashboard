"""Opt-in sequential native ingestion/refresh. Never migrates or grants rights.

The reviewed registry defines identity; an operator configuration approves work,
not publication. Only the existing explicit release CLI can grant public display.
"""

import json
import logging
import re
import sqlite3
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from threading import Event, Lock

from backend.app.catalog.releases import candidates
from backend.app.ingestion.contracts import ProviderError
from backend.app.ingestion.expansion_sources import PARSERS, parse_ons_construction
from backend.app.ingestion.native import digest, instant, native_period
from backend.app.ingestion.official_snapshots import (
    SnapshotAdapter,
    download,
    freeze,
    safe_url,
)
from backend.app.ingestion.partition_contracts import Bounds, windows
from backend.app.ingestion.partitioned import PartitionedIngestion
from backend.app.v2.native_reader import NativeReader

ROOT = Path(__file__).resolve().parents[3]
CONFIG = ROOT / "catalog/refresh_policy.json"
LOG = logging.getLogger(__name__)
DAY = 86400
MAX_FILES = 96 * 1024 * 1024


def migrate(db):
    """Explicit additive migration; application startup never calls this."""
    if not db.execute(
        "SELECT 1 FROM catalog_schema_versions WHERE version=3"
    ).fetchone():
        raise ValueError("Version 3 release schema required")
    db.execute("""CREATE TABLE IF NOT EXISTS catalog_refresh_jobs (
        dataset_id TEXT PRIMARY KEY, next_due REAL NOT NULL DEFAULT 0,
        last_attempt TEXT, last_check TEXT, last_success TEXT, last_change TEXT,
        failures INTEGER NOT NULL DEFAULT 0, error_code TEXT,
        raw_hash TEXT, content_hash TEXT, etag TEXT, last_modified TEXT,
        pending TEXT, provenance TEXT NOT NULL DEFAULT '{}')""")
    db.execute(
        "INSERT OR IGNORE INTO catalog_schema_versions VALUES(4,'catalog_refresh_jobs')"
    )


def policy(path=CONFIG):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    pubs = candidates()
    rows = data["datasets"]
    if len(rows) > 400 or len({r["id"] for r in rows}) != len(rows):
        raise ValueError("Invalid bounded refresh policy")
    for row in rows:
        if (
            row["id"] not in pubs
            or type(row["ingest_approved"]) is not bool
            or type(row["automation_ready"]) is not bool
            or row["mode"] not in {"stage", "refresh"}
            or type(row["check_seconds"]) is not int
            or not DAY <= row["check_seconds"] <= 31 * DAY
        ):
            raise ValueError("Unknown/protected ID or unsafe refresh policy")
    return {r["id"]: r for r in rows if r["ingest_approved"]}


def source_entries():
    rows = {}
    for name in ("datasets.json", "source_overrides.json"):
        for row in json.loads((ROOT / "catalog" / name).read_text(encoding="utf-8"))[
            "datasets"
        ]:
            rows[row["id"]] = row
    return rows


def endpoint(entry):
    url = entry["source"]["endpoint"]
    if entry["source"]["provider"] == "eia":
        code = entry["source"]["selector"].split(".")
        if len(code) != 3 or code[0] not in {"PET", "NG"}:
            raise ProviderError("unsupported_eia_download")
        section = "pet" if code[0] == "PET" else "ng"
        url = f"https://www.eia.gov/dnav/{section}/hist_xls/{code[1]}{code[2].lower()}.xls"
    return safe_url(url)


def semantic(points, definition):
    return digest(
        sorted(
            [
                [
                    native_period(p.period, definition, p.event_id).key,
                    p.label,
                    p.value,
                    list(p.flags),
                    instant(p.release_at).isoformat() if p.release_at else None,
                    p.source_revision,
                    p.event_id,
                ]
                for p in points
            ]
        )
    )


class CatalogRefresh:
    def __init__(self, store, *, config=CONFIG, fetch=download, now=None, cancel=None):
        self.store, self.fetch = store, fetch
        self.now = now or (lambda: datetime.now(UTC))
        self.cancel = cancel or Event()
        self.rules, self.publications, self.entries = (
            policy(config),
            candidates(),
            source_entries(),
        )
        self.reader = NativeReader(store.path, self.publications, now_fn=self.now)
        self.directory = store.path.parent / "catalog-refresh-snapshots"
        self.lock = Lock()
        self.cache = (
            None  # At most one bounded source response, shared by adjacent selections.
        )
        with store.connection(timeout=2) as db:
            db.execute("SELECT dataset_id FROM catalog_refresh_jobs LIMIT 0")

    def _permission(self, key):
        if self.rules[key]["mode"] == "refresh":
            # No implicit publication: a previously approved display grant is mandatory.
            self.reader.metadata(key)

    def _capacity(self):
        if self.cancel.is_set():
            raise ProviderError("cancelled")
        self.directory.mkdir(parents=True, exist_ok=True)
        total = sum(p.stat().st_size for p in self.directory.glob("*.json"))
        if total >= MAX_FILES:
            raise ProviderError("snapshot_budget")

    def _validate(self, key, definition, points, metadata):
        reviewed = self.publications[key].definition
        if definition.fingerprint != reviewed.fingerprint:
            raise ProviderError("definition_drift")
        if (
            definition.provider == "eurostat"
            and metadata.get("unit_label") != reviewed.units
        ):
            raise ProviderError("unit_drift")
        checked, seen = self.now(), {}
        for point in points:
            period = point.validated(reviewed, checked)
            if period.key in seen:
                raise ProviderError("duplicate_observation")
            if any(
                f.casefold().split("=", 1)[-1]
                in {"unit_review", "quarantined", "partial_period"}
                for f in point.flags
            ):
                raise ProviderError("source_quality")
            seen[period.key] = point
        if not seen or len(seen) > 50000:
            raise ProviderError("empty_or_oversized_history")
        with self.store.connection(timeout=2) as db:
            old = db.execute(
                "SELECT period_key,value,payload FROM norm_observations WHERE dataset_id=?",
                (key,),
            )
            stored = []
            for row in old:
                point = seen.get(row[0])
                if point is None:
                    raise ProviderError("history_omitted")
                if row[1] is not None and point.value is None and not point.flags:
                    raise ProviderError("unexplained_value_loss")
                p = json.loads(row[2])
                stored.append(
                    [
                        row[0],
                        p["period_label"],
                        p["value"],
                        p["flags"],
                        p["release_at"],
                        p["source_revision"],
                        p["event_id"],
                    ]
                )
        return semantic(points, reviewed), digest(sorted(stored)) if stored else None

    def _download(self, key, job):
        entry, pub = self.entries[key], self.publications[key]
        provider = pub.definition.provider
        rule = self.rules[key]
        if not rule["automation_ready"] or provider not in PARSERS:
            raise ProviderError("source_requires_adapter_review")
        url = endpoint(entry)
        if url != pub.source_url:
            raise ProviderError("source_url_drift")
        cache_key = (url, self.now().date().isoformat())
        if self.cache and self.cache[0] == cache_key:
            body, response = self.cache[1:]
        else:
            self.cache = None
            validators = (
                {k: job[k] for k in ("etag", "last_modified")}
                if job["content_hash"]
                else {}
            )
            body, response = self.fetch(url, validators=validators)
            if body is not None:
                self.cache = (cache_key, body, response)
        if body is None:
            if not job["content_hash"] or not response.get("not_modified"):
                raise ProviderError("unexpected_not_modified")
            return None, response
        if len(body) > 8 * 1024 * 1024:
            raise ProviderError("response_size_limit")
        raw = sha256(body).hexdigest()
        if raw == job["raw_hash"]:
            return None, response | {"raw_hash": raw}
        parse = (
            parse_ons_construction
            if provider == "ons" and ".xlsx" in url
            else PARSERS[provider]
        )
        definition, points, metadata = parse(entry, body)
        content, stored = self._validate(key, definition, points, metadata)
        response = response | {"raw_hash": raw, "content_hash": content}
        if content == stored:
            return None, response
        path, snapshot_hash = freeze(
            self.directory, pub.definition, points, body, url, metadata | response
        )
        starts = [native_period(p.period, pub.definition).start for p in points]
        return {
            "snapshot": snapshot_hash,
            "path": str(path),
            "raw_hash": raw,
            "content_hash": content,
            "first": min(starts).isoformat(),
            "last": max(starts).isoformat(),
            "response": response,
            "source_release": metadata.get("release_date") or metadata.get("updated"),
            "next_release": metadata.get("next_release"),
        }, response

    def _ingest(self, key, pending):
        from datetime import date

        pub = self.publications[key]
        path = Path(pending["path"])
        if path.parent.resolve() != self.directory.resolve():
            raise ProviderError("invalid_checkpoint_path")
        engine = PartitionedIngestion(
            self.store,
            [pub.definition],
            {pub.definition.provider: SnapshotAdapter(path, pending["snapshot"])},
            bounds=Bounds(records=250),
            max_generation_rows=50000,
            compact_completed_staging=True,
            preserve_unchanged_rows=True,
            max_storage_bytes=384 * 1024 * 1024,
            cancel=self.cancel,
        )
        generation = (
            "refresh_" + digest({"id": key, "snapshot": pending["snapshot"]})[:48]
        )
        with self.store.connection(timeout=2) as db:
            state = db.execute(
                "SELECT state FROM norm_generations WHERE id=?", (generation,)
            ).fetchone()
        if state and state[0] == "complete":
            return True
        engine.create_generation(
            key,
            windows(
                date.fromisoformat(pending["first"]),
                date.fromisoformat(pending["last"]),
                span_days=3660,
            ),
            generation_id=generation,
        )
        for _ in range(16):  # At most 4,000 records per supervisor dispatch.
            self._permission(key)
            self._capacity()
            result = engine.run_once()
            if result["state"] in {"failed", "busy"}:
                raise ProviderError(result.get("error_code", "worker_busy"))
            with self.store.connection(timeout=2) as db:
                if (
                    db.execute(
                        "SELECT state FROM norm_generations WHERE id=?", (generation,)
                    ).fetchone()[0]
                    == "complete"
                ):
                    return True
        return False

    def run_once(self):
        if not self.rules:
            return {"state": "idle"}
        if not self.lock.acquire(blocking=False):
            return {"state": "busy"}
        owner, key = uuid.uuid4().hex, None
        acquired = False
        try:
            stamp = self.now()
            acquired = self.store.acquire(
                "catalog-refresh", owner, stamp.timestamp(), 300, timeout=2
            )
            if not acquired:
                return {"state": "busy"}
            with self.store.connection(timeout=2) as db:
                jobs = {
                    r["dataset_id"]: dict(r)
                    for r in db.execute("SELECT * FROM catalog_refresh_jobs")
                }
            missing = [k for k in self.rules if k not in jobs]
            if missing:
                with self.store.connection(True, timeout=2) as db:
                    for i, key in enumerate(missing):
                        db.execute(
                            "INSERT OR IGNORE INTO catalog_refresh_jobs(dataset_id,next_due) VALUES(?,?)",
                            (key, stamp.timestamp() + i * 60),
                        )
                with self.store.connection(timeout=2) as db:
                    jobs = {
                        r["dataset_id"]: dict(r)
                        for r in db.execute("SELECT * FROM catalog_refresh_jobs")
                    }
            due = [k for k in self.rules if jobs[k]["next_due"] <= stamp.timestamp()]
            if not due:
                return {"state": "idle"}
            key = min(
                due, key=lambda k: (jobs[k]["next_due"], endpoint(self.entries[k]), k)
            )
            job = jobs[key]
            self._permission(key)
            self._capacity()
            with self.store.connection(True, timeout=2) as db:
                db.execute(
                    "UPDATE catalog_refresh_jobs SET last_attempt=? WHERE dataset_id=?",
                    (stamp.isoformat(), key),
                )
            pending = json.loads(job["pending"]) if job["pending"] else None
            response = pending["response"] if pending else {}
            if pending is None:
                pending, response = self._download(key, job)
                if pending:
                    with self.store.connection(True, timeout=2) as db:
                        db.execute(
                            "UPDATE catalog_refresh_jobs SET pending=?,last_check=? WHERE dataset_id=?",
                            (json.dumps(pending), stamp.isoformat(), key),
                        )
            complete = pending is None or self._ingest(key, pending)
            if not complete:
                with self.store.connection(True, timeout=2) as db:
                    db.execute(
                        "UPDATE catalog_refresh_jobs SET next_due=? WHERE dataset_id=?",
                        (self.now().timestamp() + 60, key),
                    )
                return {"id": key, "state": "checkpointed"}
            finished = self.now()
            content = (pending or response).get("content_hash") or job["content_hash"]
            provenance = json.loads(job["provenance"])
            provenance.update(
                source_checked_at=finished.isoformat(),
                source_url=self.publications[key].source_url,
            )
            if pending:
                provenance.update(
                    source_release=pending.get("source_release"),
                    next_release=pending.get("next_release"),
                    imported_at=finished.isoformat(),
                )
            with self.store.connection(True, timeout=2) as db:
                held = db.execute(
                    "SELECT owner,expires_at FROM leases WHERE name='catalog-refresh'"
                ).fetchone()
                if not held or held[0] != owner or held[1] <= finished.timestamp():
                    raise ProviderError("lease_lost")
                db.execute(
                    """UPDATE catalog_refresh_jobs SET next_due=?,last_check=?,last_success=?,
                    last_change=?,failures=0,error_code=NULL,raw_hash=?,content_hash=?,etag=?,last_modified=?,
                    pending=NULL,provenance=? WHERE dataset_id=?""",
                    (
                        finished.timestamp() + self.rules[key]["check_seconds"],
                        finished.isoformat(),
                        finished.isoformat(),
                        finished.isoformat() if pending else job["last_change"],
                        (pending or response).get("raw_hash") or job["raw_hash"],
                        content,
                        response.get("etag"),
                        response.get("last_modified"),
                        json.dumps(provenance),
                        key,
                    ),
                )
            # Only this worker's snapshots, never observations/revisions or operator archives.
            self._prune_files()
            self._compact_obsolete(key)
            result = {
                "id": key,
                "state": "changed" if pending else "unchanged",
                "next_due": finished.timestamp() + self.rules[key]["check_seconds"],
            }
            LOG.info("Catalog refresh %s", json.dumps(result))
            return result
        except Exception as exc:  # noqa: BLE001 -- keep supervisor alive, last-good data intact
            code = (
                exc.code
                if isinstance(exc, ProviderError)
                else "database_busy"
                if isinstance(exc, sqlite3.OperationalError)
                else "invalid_source"
            )
            if not isinstance(code, str) or not re.fullmatch(r"[a-z0-9_]{1,64}", code):
                code = "invalid_source"
            if key:
                try:
                    with self.store.connection(True, timeout=2) as db:
                        row = db.execute(
                            "SELECT failures FROM catalog_refresh_jobs WHERE dataset_id=?",
                            (key,),
                        ).fetchone()
                        failures = min(30, row[0] + 1)
                        delay = (
                            DAY
                            if code
                            in {
                                "http_401",
                                "http_403",
                                "source_requires_adapter_review",
                                "definition_drift",
                                "unit_drift",
                            }
                            else min(DAY, 300 * 2 ** min(failures - 1, 9))
                        )
                        delay = max(delay, getattr(exc, "retry_after", 0))
                        db.execute(
                            "UPDATE catalog_refresh_jobs SET failures=?,error_code=?,next_due=?,last_check=? WHERE dataset_id=?",
                            (
                                failures,
                                code,
                                self.now().timestamp() + delay,
                                self.now().isoformat(),
                                key,
                            ),
                        )
                        if code == "http_429":
                            provider = self.publications[key].definition.provider
                            for sibling in self.rules:
                                if (
                                    self.publications[sibling].definition.provider
                                    == provider
                                ):
                                    db.execute(
                                        "UPDATE catalog_refresh_jobs SET next_due=max(next_due,?) WHERE dataset_id=?",
                                        (
                                            self.now().timestamp() + max(3600, delay),
                                            sibling,
                                        ),
                                    )
                except sqlite3.Error:
                    pass  # No reset; next scheduler tick retries durable state.
            LOG.warning(
                "Catalog refresh failed id=%s code=%s; last-good data retained",
                key,
                code,
            )
            return {"id": key, "state": "failed", "error_code": code}
        finally:
            if acquired:
                try:
                    self.store.release("catalog-refresh", owner, timeout=2)
                except sqlite3.Error:
                    pass
            self.lock.release()

    def _prune_files(self):
        with self.store.connection(timeout=2) as db:
            keep = {
                json.loads(r[0])["path"]
                for r in db.execute(
                    "SELECT pending FROM catalog_refresh_jobs WHERE pending IS NOT NULL"
                )
            }
        # Completed source payloads have durable SQLite proofs; keep only pending files.
        for path in self.directory.glob("*.json"):
            if str(path) not in keep:
                path.unlink(missing_ok=True)

    def _compact_obsolete(self, key):
        # Only obsolete proof detail created by this worker, never initial release
        # generations, observation values, revision history, grants or research.
        # Retain generation/snapshot identity and aggregate completeness hashes.
        with self.store.connection(True, timeout=2) as db:
            old = db.execute(
                """SELECT id FROM norm_generations g WHERE dataset_id=?
                AND state='complete' AND substr(id,1,8)='refresh_'
                AND NOT EXISTS(SELECT 1 FROM norm_observations o WHERE o.generation_id=g.id)
                AND NOT EXISTS(SELECT 1 FROM norm_dataset_state s WHERE s.active_generation=g.id)
                ORDER BY completed_at DESC LIMIT -1 OFFSET 1""",
                (key,),
            ).fetchall()
            for row in old:
                generation = row[0]
                db.execute(
                    "DELETE FROM norm_runs WHERE partition_id IN (SELECT id FROM norm_partitions WHERE generation_id=?)",
                    (generation,),
                )
                db.execute(
                    "DELETE FROM norm_pages WHERE partition_id IN (SELECT id FROM norm_partitions WHERE generation_id=?)",
                    (generation,),
                )
                for table in (
                    "catalog_staging_receipts",
                    "catalog_staging_digests",
                    "norm_staged",
                ):
                    db.execute(
                        f"DELETE FROM {table} WHERE generation_id=?", (generation,)
                    )
                db.execute(
                    "DELETE FROM norm_partitions WHERE generation_id=?", (generation,)
                )

    def status(self):
        with self.store.connection(timeout=2) as db:
            return [
                dict(r)
                for r in db.execute(
                    "SELECT dataset_id,last_attempt,last_check,last_success,last_change,failures,error_code,next_due,pending IS NOT NULL AS checkpointed FROM catalog_refresh_jobs ORDER BY dataset_id"
                )
            ]


class CatalogRefreshWorker:
    def __init__(self, store, *, enabled=False, config=CONFIG):
        self.store, self.enabled, self.config = store, enabled, config
        self.cancel, self.lock = Event(), Lock()
        self.pool = self.future = self.engine = None
        self.error_code = None
        self.restart_requested = False

    def start(self):
        with self.lock:
            if self.cancel.is_set():
                self.restart_requested = True

    def _run(self):
        try:
            if self.engine is None:
                self.engine = CatalogRefresh(
                    self.store, config=self.config, cancel=self.cancel
                )
            result = self.engine.run_once()
            self.error_code = result.get("error_code")
        except Exception:  # noqa: BLE001 -- migration/config errors must not kill Discovery
            self.error_code = "refresh_unavailable"
            LOG.warning(
                "Catalog refresh unavailable; explicit migration and approved configuration required"
            )

    def tick(self):
        with self.lock:
            if self.restart_requested:
                if self.future and not self.future.done():
                    return
                self.pool = self.engine = None
                self.cancel = Event()
                self.restart_requested = False
            if (
                not self.enabled
                or self.cancel.is_set()
                or self.future
                and not self.future.done()
            ):
                return
            if self.pool is None:
                self.pool = ThreadPoolExecutor(
                    max_workers=1, thread_name_prefix="catalog-refresh"
                )
            self.future = self.pool.submit(self._run)

    def stop(self):
        with self.lock:
            self.restart_requested = False
            self.cancel.set()
            if self.pool:
                self.pool.shutdown(wait=False, cancel_futures=True)

    def status(self):
        try:
            jobs = self.engine.status() if self.engine else []
        except sqlite3.Error:
            jobs = []
        return {
            "enabled": self.enabled,
            "in_progress": bool(self.future and not self.future.done()),
            "error_code": self.error_code,
            "jobs": jobs,
        }


def main():
    import argparse
    from backend.app.v2.state import Store

    parser = argparse.ArgumentParser(
        description="Explicit additive refresh migration or read-only status; never runs ingestion"
    )
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--operation", choices=("migrate", "status"), required=True)
    args = parser.parse_args()
    if not args.database.is_file():
        parser.error("Existing explicit database required")
    if args.operation == "migrate":
        with Store(args.database).connection(True) as db:
            migrate(db)
        print(json.dumps({"schema": 4, "published": 0, "scheduled_refresh": False}))
    else:
        from contextlib import closing

        with closing(
            sqlite3.connect(args.database.resolve().as_uri() + "?mode=ro", uri=True)
        ) as db:
            db.row_factory = sqlite3.Row
            rows = db.execute(
                "SELECT dataset_id,last_check,last_success,last_change,failures,error_code,next_due FROM catalog_refresh_jobs ORDER BY dataset_id"
            )
            print(json.dumps([dict(r) for r in rows], indent=2))


if __name__ == "__main__":
    main()
