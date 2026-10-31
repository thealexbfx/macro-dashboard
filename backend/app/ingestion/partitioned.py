"""Inactive native ingestion engine: bounded pages, staged generations, atomic promotion.

Only explicit callers with an already-migrated disposable/staging store can use
this engine. No app, CLI, source registry, scheduler, public reader or AI hook is
changed. Existing ingest_* tables and their private WB observations are untouched.
"""

import json
import re
import shutil
import sqlite3
import time
import uuid
from contextlib import closing
from dataclasses import asdict
from datetime import UTC, datetime
from hashlib import sha256
from itertools import pairwise
from threading import Event, Lock

from backend.app.catalog.manifest import LEGACY_PUBLIC_SOURCES
from backend.app.ingestion.contracts import ProviderError
from backend.app.ingestion.native import digest, instant
from backend.app.ingestion.partition_contracts import DEFAULT_BOUNDS, Page, Window

PROTECTED = frozenset(LEGACY_PUBLIC_SOURCES) | {
    "wb_brent_monthly",
    "wb_copper_monthly",
    "wb_iron_ore_monthly",
}


def serialized(value):
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), default=lambda x: x.isoformat()
    )


class PartitionedIngestion:
    def __init__(
        self,
        store,
        definitions,
        adapters,
        *,
        bounds=DEFAULT_BOUNDS,
        now_fn=None,
        cancel=None,
        max_generation_rows=10000,
        compact_completed_staging=False,
        max_storage_bytes=256 * 1024 * 1024,
    ):
        if not 1 <= len(definitions) <= 64 or len({d.id for d in definitions}) != len(
            definitions
        ):
            raise ValueError("Bounded explicit definitions required")
        if any(d.id in PROTECTED or d.provider not in adapters for d in definitions):
            raise ValueError(
                "Existing datasets cannot be shadowed or implicitly registered"
            )
        if (
            type(max_generation_rows) is not int
            or not 1 <= max_generation_rows <= 50000
        ):
            raise ValueError("Unsafe generation row budget")
        self.max_generation_rows = max_generation_rows
        if type(compact_completed_staging) is not bool:
            raise TypeError("Explicit staging retention policy required")
        self.compact_completed_staging = compact_completed_staging
        if (
            type(max_storage_bytes) is not int
            or not 64 * 1024 * 1024 <= max_storage_bytes <= 384 * 1024 * 1024
        ):
            raise ValueError("Unsafe storage budget")
        self.max_storage_bytes = max_storage_bytes
        self.store, self.bounds, self.adapters = store, bounds, dict(adapters)
        self.definitions = {d.id: d for d in definitions}
        self.now = now_fn or (lambda: datetime.now(UTC))
        self.cancel, self.lock = cancel or Event(), Lock()
        self.capacity()
        # Preflight through SQLite read-only mode before Store can initialize any
        # schema. A mistyped path must never create a database or apply migrations.
        try:
            with closing(
                sqlite3.connect(
                    store.path.resolve().as_uri() + "?mode=ro", uri=True, timeout=2
                )
            ) as db:
                if db.execute(
                    "SELECT name FROM catalog_schema_versions WHERE version=2"
                ).fetchone() != ("batch0_native_partition_foundation",):
                    raise ValueError("Explicit version 2 migration required")
                db.execute("SELECT id FROM norm_datasets LIMIT 0")
                db.execute("SELECT id FROM source_cache LIMIT 0")
        except sqlite3.Error as exc:
            raise ValueError("Explicit version 2 migration required") from exc
        with store.connection(True, timeout=2) as db:
            # Missing v2 tables fail here. Constructor must never migrate implicitly.
            for definition in definitions:
                alias = db.execute(
                    "SELECT id FROM norm_datasets WHERE source_identity=? AND id!=?",
                    (definition.source_identity, definition.id),
                ).fetchone()
                if alias:
                    raise ValueError("Canonical source selection already registered")
                old = db.execute(
                    "SELECT definition_hash,definition FROM norm_datasets WHERE id=?",
                    (definition.id,),
                ).fetchone()
                if old and old[0] != definition.fingerprint:
                    raise ValueError(
                        "Definition change requires explicit version review"
                    )
                db.execute(
                    "INSERT OR IGNORE INTO norm_datasets(id,provider,definition,definition_hash,source_identity) VALUES(?,?,?,?,?)",
                    (
                        definition.id,
                        definition.provider,
                        serialized(asdict(definition)),
                        definition.fingerprint,
                        definition.source_identity,
                    ),
                )
                if old and old[1] != serialized(asdict(definition)):
                    db.execute(
                        "UPDATE norm_datasets SET definition=? WHERE id=?",
                        (serialized(asdict(definition)), definition.id),
                    )

    def capacity(self):
        total = sum(
            p.stat().st_size
            for suffix in ("", "-wal", "-shm", "-journal")
            if (p := self.store.path.with_name(self.store.path.name + suffix)).exists()
        )
        if (
            total >= self.max_storage_bytes
            or shutil.disk_usage(self.store.path.parent).free < 64 * 1024 * 1024
        ):
            raise ProviderError("storage_budget")
        if self.cancel.is_set():
            raise ProviderError("cancelled")

    def create_generation(self, dataset_id, partitions, *, generation_id=None):
        definition = self.definitions[dataset_id]
        if (
            not isinstance(partitions, (tuple, list))
            or not 1 <= len(partitions) <= 32
            or any(not isinstance(w, Window) for w in partitions)
        ):
            raise ValueError("Invalid bounded partition plan")
        plans = sorted(partitions, key=lambda w: w.start)
        if any(a.end >= b.start for a, b in pairwise(plans)):
            raise ValueError("Overlapping source windows")
        key = generation_id or uuid.uuid4().hex
        if not re.fullmatch(r"[a-zA-Z0-9_]{1,96}", key):
            raise ValueError("Invalid generation identity")
        self.capacity()
        with self.store.connection(True, timeout=2) as db:
            existing = db.execute(
                "SELECT * FROM norm_generations WHERE id=?", (key,)
            ).fetchone()
            if existing:
                windows = db.execute(
                    "SELECT start_date,end_date FROM norm_partitions WHERE generation_id=? ORDER BY start_date",
                    (key,),
                ).fetchall()
                if (
                    existing["dataset_id"] != dataset_id
                    or existing["definition_hash"] != definition.fingerprint
                    or [tuple(x) for x in windows]
                    != [(w.start.isoformat(), w.end.isoformat()) for w in plans]
                ):
                    raise ValueError("Generation idempotency conflict")
                return key
            db.execute(
                "INSERT INTO norm_generations VALUES(?,?,?,'staging',NULL,?,NULL)",
                (
                    key,
                    dataset_id,
                    definition.fingerprint,
                    instant(self.now()).isoformat(),
                ),
            )
            db.executemany(
                "INSERT INTO norm_partitions(id,generation_id,start_date,end_date) VALUES(?,?,?,?)",
                [
                    (f"{key}_{i:02d}", key, w.start.isoformat(), w.end.isoformat())
                    for i, w in enumerate(plans)
                ],
            )
        return key

    def next_source_release(self, dataset_id, after=None):
        """Only return a supplied official release instant; no synthetic cadence."""
        return self.definitions[dataset_id].calendar.next_release(after or self.now())

    def status(self):
        """Internal bounded diagnostics, never observations, credentials or cursors."""
        with self.store.connection(timeout=2) as db:
            placeholders = ",".join("?" for _ in self.definitions)
            jobs = [
                dict(r)
                for r in db.execute(
                    f"SELECT g.dataset_id,p.id,p.state,p.page_count,p.failures,p.error_code,p.next_due FROM norm_partitions p JOIN norm_generations g ON g.id=p.generation_id WHERE g.dataset_id IN ({placeholders}) AND g.state='staging' ORDER BY p.next_due,p.id LIMIT 64",
                    tuple(self.definitions),
                )
            ]
        return {
            "partitions": jobs,
            "public_display": False,
            "ai_allowed": False,
            "discovery_allowed": False,
        }

    def restart_generation(self, generation_id):
        """Retain staged evidence; restart ALL windows if a source snapshot changed."""
        self.capacity()
        with self.store.connection(True, timeout=2) as db:
            generation = db.execute(
                "SELECT * FROM norm_generations WHERE id=?", (generation_id,)
            ).fetchone()
            if (
                not generation
                or generation["dataset_id"] not in self.definitions
                or generation["state"] != "staging"
            ):
                raise ValueError("Only an incomplete known generation can restart")
            plans = [
                Window(
                    datetime.fromisoformat(r[0]).date(),
                    datetime.fromisoformat(r[1]).date(),
                )
                for r in db.execute(
                    "SELECT start_date,end_date FROM norm_partitions WHERE generation_id=? ORDER BY start_date",
                    (generation_id,),
                )
            ]
            db.execute(
                "UPDATE norm_generations SET state='superseded' WHERE id=?",
                (generation_id,),
            )
            db.execute(
                "UPDATE norm_partitions SET state='superseded' WHERE generation_id=?",
                (generation_id,),
            )
            key = uuid.uuid4().hex
            db.execute(
                "INSERT INTO norm_generations VALUES(?,?,?,'staging',NULL,?,NULL)",
                (
                    key,
                    generation["dataset_id"],
                    generation["definition_hash"],
                    instant(self.now()).isoformat(),
                ),
            )
            db.executemany(
                "INSERT INTO norm_partitions(id,generation_id,start_date,end_date) VALUES(?,?,?,?)",
                [
                    (f"{key}_{i:02d}", key, w.start.isoformat(), w.end.isoformat())
                    for i, w in enumerate(plans)
                ],
            )
        return key

    def run_once(self):
        if not self.lock.acquire(blocking=False):
            return {"state": "busy"}
        owner, run_id, job = uuid.uuid4().hex, uuid.uuid4().hex, None
        try:
            self.capacity()
            stamp = instant(self.now())
            with self.store.connection(True, timeout=2) as db:
                held = db.execute(
                    "SELECT * FROM norm_worker_lease WHERE singleton=1"
                ).fetchone()
                if held and held["expires_at"] > stamp.timestamp():
                    return {"state": "busy"}
                slots = ",".join("?" for _ in self.definitions)
                row = db.execute(
                    f"SELECT p.*,g.dataset_id,g.snapshot_hash,g.definition_hash FROM norm_partitions p JOIN norm_generations g ON g.id=p.generation_id WHERE g.state='staging' AND g.dataset_id IN ({slots}) AND p.state IN ('pending','failed','running') AND p.next_due<=? ORDER BY p.next_due,p.id LIMIT 1",
                    (*self.definitions, stamp.timestamp()),
                ).fetchone()
                if row is None:
                    return {"state": "idle"}
                job = dict(row)
                db.execute(
                    "INSERT INTO norm_worker_lease VALUES(1,?,?) ON CONFLICT(singleton) DO UPDATE SET owner=excluded.owner,expires_at=excluded.expires_at",
                    (owner, stamp.timestamp() + 120),
                )
                db.execute(
                    "UPDATE norm_runs SET state='abandoned',finished_at=?,error_code='worker_interrupted' WHERE partition_id=? AND state='running'",
                    (stamp.isoformat(), job["id"]),
                )
                db.execute(
                    "INSERT INTO norm_runs VALUES(?,?,'running',?,NULL,NULL)",
                    (run_id, job["id"], stamp.isoformat()),
                )
                db.execute(
                    "UPDATE norm_partitions SET state='running',last_attempt=? WHERE id=?",
                    (stamp.isoformat(), job["id"]),
                )
            definition = self.definitions[job["dataset_id"]]
            window = Window(
                datetime.fromisoformat(job["start_date"]).date(),
                datetime.fromisoformat(job["end_date"]).date(),
            )
            started = time.monotonic()
            page = self.adapters[definition.provider].fetch(
                definition, window, job["cursor"], self.bounds
            )
            if time.monotonic() - started > self.bounds.seconds:
                raise ProviderError("transport_deadline")
            self.capacity()
            points = self._validate(definition, window, page, job)
            with self.store.connection(True, timeout=2) as db:
                self._fence(db, owner, job)
                generation = db.execute(
                    "SELECT * FROM norm_generations WHERE id=?", (job["generation_id"],)
                ).fetchone()
                if generation["snapshot_hash"] not in {None, page.snapshot_hash}:
                    raise ProviderError("snapshot_changed")
                db.execute(
                    "UPDATE norm_generations SET snapshot_hash=? WHERE id=?",
                    (page.snapshot_hash, job["generation_id"]),
                )
                request_hash, next_hash = (
                    digest(job["cursor"]),
                    digest(page.next_cursor),
                )
                if (
                    db.execute(
                        "SELECT 1 FROM norm_pages WHERE partition_id=? AND request_hash=?",
                        (job["id"], request_hash),
                    ).fetchone()
                    or page.next_cursor is not None
                    and db.execute(
                        "SELECT 1 FROM norm_pages WHERE partition_id=? AND request_hash=?",
                        (job["id"], next_hash),
                    ).fetchone()
                ):
                    raise ProviderError("checkpoint_cycle")
                if (
                    job["page_count"] >= 64
                    or job["page_count"] == 63
                    and page.next_cursor is not None
                ):
                    raise ProviderError("partition_page_budget")
                total = db.execute(
                    "SELECT count(*) FROM norm_staged WHERE generation_id=?",
                    (job["generation_id"],),
                ).fetchone()[0]
                if total + len(points) > self.max_generation_rows:
                    raise ProviderError("generation_row_budget")
                for key, payload, value, start, end in points:
                    if db.execute(
                        "SELECT 1 FROM norm_staged WHERE generation_id=? AND period_key=?",
                        (job["generation_id"], key),
                    ).fetchone():
                        raise ProviderError("duplicate_observation")
                    db.execute(
                        "INSERT INTO norm_staged VALUES(?,?,?,?,?,?,?,?,?)",
                        (
                            job["generation_id"],
                            key,
                            start,
                            end,
                            job["id"],
                            payload,
                            value,
                            page.content_hash,
                            instant(page.checked_at).isoformat(),
                        ),
                    )
                db.execute(
                    "INSERT INTO norm_pages VALUES(?,?,?,?,?)",
                    (
                        job["id"],
                        request_hash,
                        page.content_hash,
                        next_hash,
                        len(points),
                    ),
                )
                state = "complete" if page.next_cursor is None else "pending"
                db.execute(
                    "UPDATE norm_partitions SET cursor=?,state=?,page_count=page_count+1,failures=0,error_code=NULL,last_success=?,next_due=? WHERE id=?",
                    (
                        page.next_cursor,
                        state,
                        instant(self.now()).isoformat(),
                        instant(self.now()).timestamp(),
                        job["id"],
                    ),
                )
                remaining = db.execute(
                    "SELECT count(*) FROM norm_partitions WHERE generation_id=? AND state!='complete'",
                    (job["generation_id"],),
                ).fetchone()[0]
                if not remaining:
                    self._promote(db, definition, job["generation_id"])
                self._check_lease(db, owner)
                db.execute(
                    "UPDATE norm_runs SET state=?,finished_at=? WHERE id=?",
                    (state, instant(self.now()).isoformat(), run_id),
                )
            return {
                "state": state,
                "dataset_id": definition.id,
                "partition_id": job["id"],
            }
        except Exception as exc:  # noqa: BLE001 -- safe durable provider boundary
            code = (
                exc.code
                if isinstance(exc, ProviderError)
                and isinstance(exc.code, str)
                and re.fullmatch(r"[a-z0-9_]{1,64}", exc.code)
                else "invalid_source"
                if isinstance(exc, (ValueError, KeyError, TypeError))
                else "internal_error"
            )
            if job is not None:
                try:
                    with self.store.connection(True, timeout=2) as db:
                        held = db.execute(
                            "SELECT owner FROM norm_worker_lease WHERE singleton=1"
                        ).fetchone()
                        current = db.execute(
                            "SELECT state FROM norm_generations WHERE id=?",
                            (job["generation_id"],),
                        ).fetchone()
                        if (
                            held
                            and held[0] == owner
                            and current
                            and current[0] == "staging"
                        ):
                            delay = max(
                                min(86400, 60 * 2 ** min(job["failures"] + 1, 10)),
                                exc.retry_after
                                if isinstance(exc, ProviderError)
                                else 0,
                            )
                            db.execute(
                                "UPDATE norm_partitions SET state='failed',failures=failures+1,error_code=?,next_due=? WHERE id=?",
                                (
                                    code,
                                    instant(self.now()).timestamp() + delay,
                                    job["id"],
                                ),
                            )
                            db.execute(
                                "UPDATE norm_runs SET state='failed',finished_at=?,error_code=? WHERE id=?",
                                (instant(self.now()).isoformat(), code, run_id),
                            )
                except sqlite3.Error:
                    code = "database_unavailable"
            return {"state": "failed", "error_code": code}
        finally:
            try:
                if job is not None:
                    with self.store.connection(True, timeout=2) as db:
                        db.execute(
                            "DELETE FROM norm_worker_lease WHERE singleton=1 AND owner=?",
                            (owner,),
                        )
            except sqlite3.Error:
                pass  # Expiry fencing permits recovery; never mask the original failure.
            finally:
                self.lock.release()

    def _fence(self, db, owner, job):
        self._check_lease(db, owner)
        current = db.execute(
            "SELECT definition_hash FROM norm_datasets WHERE id=?", (job["dataset_id"],)
        ).fetchone()
        if not current or current[0] != job["definition_hash"]:
            raise ProviderError("definition_changed")
        row = db.execute(
            "SELECT p.cursor,p.page_count,g.state FROM norm_partitions p JOIN norm_generations g ON g.id=p.generation_id WHERE p.id=?",
            (job["id"],),
        ).fetchone()
        if (
            not row
            or row["state"] != "staging"
            or row["cursor"] != job["cursor"]
            or row["page_count"] != job["page_count"]
        ):
            raise ProviderError("lease_lost")

    def _check_lease(self, db, owner):
        held = db.execute(
            "SELECT * FROM norm_worker_lease WHERE singleton=1"
        ).fetchone()
        if (
            not held
            or held["owner"] != owner
            or held["expires_at"] <= instant(self.now()).timestamp()
        ):
            raise ProviderError("lease_lost")

    def _validate(self, definition, window, page, job):
        if (
            not isinstance(page, Page)
            or definition.fingerprint != job["definition_hash"]
            or len(page.points) > self.bounds.records
            or page.next_cursor is not None
            and page.next_cursor == job["cursor"]
        ):
            raise ProviderError("invalid_page")
        if instant(page.checked_at) > instant(self.now()):
            raise ProviderError("future_source_check")
        result, seen, size = [], set(), 0
        for point in page.points:
            period = point.validated(definition, page.checked_at)
            if not window.start <= period.start <= window.end or period.key in seen:
                raise ProviderError("duplicate_or_outside_partition")
            seen.add(period.key)
            value = float(point.value) if point.value is not None else None
            payload = serialized(
                {
                    "period_label": point.label,
                    "reference_start": period.start.isoformat(),
                    "reference_end": period.end.isoformat(),
                    "event_at": period.event_at,
                    "event_id": point.event_id,
                    "value": value,
                    "missing": value is None,
                    "flags": point.flags,
                    "release_at": instant(point.release_at).isoformat()
                    if point.release_at
                    else None,
                    "source_revision": point.source_revision,
                    "frequency": definition.frequency,
                    "units": definition.units,
                    "adjustment": definition.adjustment,
                    "calendar_id": definition.calendar.id,
                    "definition_hash": definition.fingerprint,
                    "source_url": page.source_url,
                }
            )
            size += len(payload.encode())
            if size > self.bounds.response_bytes:
                raise ProviderError("normalized_page_budget")
            result.append(
                (
                    period.key,
                    payload,
                    value,
                    period.start.isoformat(),
                    period.end.isoformat(),
                )
            )
        return result

    def _promote(self, db, definition, generation_id):
        if not db.execute(
            "SELECT 1 FROM norm_staged WHERE generation_id=? LIMIT 1", (generation_id,)
        ).fetchone():
            raise ProviderError("empty_generation")
        missing = db.execute(
            "SELECT 1 FROM norm_observations o JOIN norm_partitions p ON p.generation_id=? AND o.reference_start BETWEEN p.start_date AND p.end_date LEFT JOIN norm_staged s ON s.generation_id=p.generation_id AND s.period_key=o.period_key WHERE o.dataset_id=? AND s.period_key IS NULL LIMIT 1",
            (generation_id, definition.id),
        ).fetchone()
        if missing:
            raise ProviderError("history_omitted")
        query = db.execute(
            "SELECT * FROM norm_staged WHERE generation_id=? ORDER BY period_key",
            (generation_id,),
        )
        quality = True
        while rows := query.fetchmany(250):
            for row in rows:
                old = db.execute(
                    "SELECT * FROM norm_observations WHERE dataset_id=? AND period_key=?",
                    (definition.id, row["period_key"]),
                ).fetchone()
                if old and row["checked_at"] < old["checked_at"]:
                    raise ProviderError("stale_response")
                revision = (
                    1
                    if old is None
                    else old["revision"] + (old["payload"] != row["payload"])
                )
                if old and revision != old["revision"]:
                    db.execute(
                        "INSERT INTO norm_revisions VALUES(?,?,?,?,?,?,?)",
                        (
                            definition.id,
                            row["period_key"],
                            old["revision"],
                            old["payload"],
                            old["artifact_hash"],
                            instant(self.now()).isoformat(),
                            generation_id,
                        ),
                    )
                db.execute(
                    "INSERT INTO norm_observations VALUES(?,?,?,?,?,?,?,?,?,?) ON CONFLICT(dataset_id,period_key) DO UPDATE SET payload=excluded.payload,value=excluded.value,artifact_hash=excluded.artifact_hash,checked_at=excluded.checked_at,revision=excluded.revision,generation_id=excluded.generation_id",
                    (
                        definition.id,
                        row["period_key"],
                        row["reference_start"],
                        row["reference_end"],
                        row["payload"],
                        row["value"],
                        row["artifact_hash"],
                        row["checked_at"],
                        revision,
                        generation_id,
                    ),
                )
                if self.compact_completed_staging:
                    db.execute(
                        "INSERT INTO catalog_staging_digests VALUES(?,?,?)",
                        (
                            generation_id,
                            row["period_key"],
                            sha256(row["payload"].encode()).hexdigest(),
                        ),
                    )
                quality = quality and not any(
                    x.casefold().split("=", 1)[-1]
                    in {"unit_review", "quarantined", "partial_period"}
                    for x in json.loads(row["payload"])["flags"]
                )
        hashes = [
            tuple(r)
            for r in db.execute(
                "SELECT p.start_date,p.end_date,x.request_hash,x.content_hash,x.next_hash FROM norm_pages x JOIN norm_partitions p ON p.id=x.partition_id WHERE p.generation_id=? ORDER BY p.start_date,x.request_hash",
                (generation_id,),
            )
        ]
        snapshot = db.execute(
            "SELECT snapshot_hash FROM norm_generations WHERE id=?", (generation_id,)
        ).fetchone()[0]
        aggregate = digest(
            {
                "snapshot": snapshot,
                "definition": definition.fingerprint,
                "pages": hashes,
            }
        )
        stamp = instant(self.now()).isoformat()
        db.execute(
            "UPDATE norm_generations SET state='complete',completed_at=? WHERE id=?",
            (stamp, generation_id),
        )
        db.execute(
            "INSERT INTO catalog_dataset_completeness VALUES(?,?,?,?,NULL,?,?,?)",
            (
                definition.id,
                generation_id,
                aggregate,
                definition.fingerprint,
                "complete" if quality else "partial",
                int(quality),
                stamp,
            ),
        )
        db.execute(
            "INSERT INTO norm_dataset_state VALUES(?,?,?) ON CONFLICT(dataset_id) DO UPDATE SET active_generation=excluded.active_generation,updated_at=excluded.updated_at",
            (definition.id, generation_id, stamp),
        )
        if self.compact_completed_staging:
            # Replace only duplicated payload bytes with the exact SHA-256 proof.
            # Every stage key/partition/value/date/artifact remains. Complete
            # original payloads remain in observations and revision history.
            db.execute(
                "UPDATE norm_staged SET payload='' WHERE generation_id=?",
                (generation_id,),
            )
