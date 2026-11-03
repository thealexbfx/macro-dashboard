"""One leased provider job per tick, short atomic writes, durable retry/cursor state."""

import json
import math
import re
import shutil
import uuid
from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from datetime import UTC, datetime
from threading import Event, Lock

from backend.app.ingestion.contracts import Adapter, ProviderError
from backend.app.v2.state import dumps


def month_offset(period, months):
    y, m = map(int, period.split("-"))
    v = y * 12 + m - 1 + months
    return f"{v // 12:04d}-{v % 12 + 1:02d}"


class Ingestion:
    def __init__(
        self,
        store,
        adapters: Sequence[Adapter],
        now_fn=None,
        chunk_months=120,
        cancel_event=None,
    ):
        self.store = store
        self.cancel_event = cancel_event or Event()
        self.adapters = {a.id: a for a in adapters}
        self.now_fn = now_fn or (lambda: datetime.now(UTC))
        if len(self.adapters) != len(adapters) or not 1 <= chunk_months <= 120:
            raise ValueError("Invalid provider registry or backfill bound")
        self.chunk_months = chunk_months
        seen = set()
        for adapter in adapters:
            for spec in adapter.series:
                if (
                    spec.id in seen
                    or spec.provider != adapter.id
                    or spec.frequency != "monthly"
                ):
                    raise ValueError(
                        "Invalid registry: foundation pilot supports native monthly periods"
                    )
                seen.add(spec.id)
        self.register()

    def register(self):
        with self.store.connection(True, timeout=2) as db:
            for adapter in self.adapters.values():
                db.execute(
                    "INSERT OR IGNORE INTO ingest_jobs(provider) VALUES (?)",
                    (adapter.id,),
                )
                for spec in adapter.series:
                    db.execute(
                        "INSERT OR IGNORE INTO ingest_datasets(id,provider,metadata,updated_at) VALUES (?,?,?,?)",
                        (
                            spec.id,
                            adapter.id,
                            dumps(asdict(spec)),
                            self.now_fn().isoformat(),
                        ),
                    )

    def _check_cancelled(self):
        if self.cancel_event.is_set():
            raise ProviderError("cancelled")

    def _capacity(self):
        # Stop safely, never prune existing data to make space. Include WAL in quota.
        size = 0
        for suffix in ("", "-wal", "-shm", "-journal"):
            path = self.store.path.with_name(self.store.path.name + suffix)
            try:
                size += path.stat().st_size
            except FileNotFoundError:
                if not suffix:
                    raise ProviderError("state_unavailable") from None
                # SQLite may checkpoint and remove a sidecar between stat calls.
                continue
        if (
            size >= 256 * 1024 * 1024
            or shutil.disk_usage(self.store.path.parent).free < 64 * 1024 * 1024
        ):
            raise ProviderError("storage_budget")

    def _validate(self, adapter, batch):
        ids = {s.id for s in adapter.series}
        if set(batch.metadata) != ids or not batch.points or len(batch.points) > 5000:
            raise ProviderError("invalid_batch")
        if {p.dataset_id for p in batch.points} != ids or not re.fullmatch(
            r"[0-9a-f]{64}", batch.source_hash
        ):
            raise ProviderError("invalid_batch")
        seen = set()
        for p in batch.points:
            if p.dataset_id not in ids or (p.dataset_id, p.period) in seen:
                raise ProviderError("duplicate_or_unknown_observation")
            try:
                date = datetime.strptime(p.period, "%Y-%m")
            except ValueError as exc:
                raise ProviderError("invalid_period") from exc
            if date.strftime("%Y-%m") != p.period or p.period > self.now_fn().strftime(
                "%Y-%m"
            ):
                raise ProviderError("invalid_period")
            if p.value is not None and not math.isfinite(p.value):
                raise ProviderError("invalid_value")
            seen.add((p.dataset_id, p.period))
        with self.store.connection(timeout=2) as db:
            for spec in adapter.series:
                meta = batch.metadata[spec.id]
                if meta.get("coverage_gaps"):
                    raise ProviderError("missing_period_rows")
                previous = json.loads(
                    db.execute(
                        "SELECT metadata FROM ingest_datasets WHERE id=?", (spec.id,)
                    ).fetchone()[0]
                ).get("validation")
                if previous and (
                    meta["first_period"] > previous["first_period"]
                    or meta["last_period"] < previous["last_period"]
                ):
                    raise ProviderError("history_truncated")

    def run_once(self, force=False):
        now = self.now_fn()
        with self.store.connection(timeout=2) as db:
            jobs = db.execute(
                "SELECT * FROM ingest_jobs ORDER BY next_due,provider"
            ).fetchall()
        for job in jobs:
            if job["provider"] not in self.adapters or (
                not force and job["next_due"] > now.timestamp()
            ):
                continue
            result = self._run(job["provider"], now, force)
            if result is not None:
                return result
        return {"state": "idle"}

    def _run(self, provider, now, force):
        owner = uuid.uuid4().hex
        lease = "ingestion:" + provider
        if not self.store.acquire(lease, owner, now.timestamp(), 180, timeout=2):
            return None
        run_id = uuid.uuid4().hex
        started = False
        try:
            with self.store.connection(True, timeout=2) as db:
                job = dict(
                    db.execute(
                        "SELECT * FROM ingest_jobs WHERE provider=?", (provider,)
                    ).fetchone()
                )
                if not force and job["next_due"] > now.timestamp():
                    return None
                db.execute(
                    "UPDATE ingest_runs SET state='abandoned',finished_at=?,error_code='worker_interrupted' WHERE provider=? AND state='running'",
                    (now.isoformat(), provider),
                )
                db.execute(
                    "INSERT INTO ingest_runs(id,provider,started_at,state) VALUES (?,?,?,'running')",
                    (run_id, provider, now.isoformat()),
                )
                db.execute(
                    "UPDATE ingest_jobs SET last_attempt=? WHERE provider=?",
                    (now.isoformat(), provider),
                )
                started = True
            self._check_cancelled()
            self._capacity()
            adapter = self.adapters[provider]
            batch = adapter.fetch()  # No SQLite write lock while downloading/parsing.
            self._check_cancelled()
            self._validate(adapter, batch)
            periods = sorted({p.period for p in batch.points})
            full = (
                bool(job["cursor"])
                or not job["source_hash"]
                or now.timestamp() - job["last_full_check"] >= 30 * 86400
            )
            # A daily unchanged hash must not indefinitely postpone old-revision reconciliation.
            unchanged = batch.source_hash == job["source_hash"] and not full
            start = (
                job["cursor"]
                if job["cursor"] and batch.source_hash == job["source_hash"]
                else periods[0]
                if full
                else month_offset(periods[-1], -23)
            )
            selected_periods = (
                []
                if unchanged
                else [p for p in periods if p >= start][: self.chunk_months]
            )
            chosen = set(selected_periods)
            more = bool(chosen and selected_periods[-1] < periods[-1])
            cursor = month_offset(selected_periods[-1], 1) if more else None
            changes = {"inserted": 0, "revised": 0}
            self._capacity()
            finished = self.now_fn()
            with self.store.connection(True, timeout=2) as db:
                self._check_cancelled()
                # Fencing: an expired/reassigned lease may never commit stale results.
                held = db.execute(
                    "SELECT owner,expires_at FROM leases WHERE name=?", (lease,)
                ).fetchone()
                if (
                    not held
                    or held["owner"] != owner
                    or held["expires_at"] <= finished.timestamp()
                ):
                    raise ProviderError("lease_lost")
                for p in batch.points:
                    if p.period not in chosen:
                        continue
                    old = db.execute(
                        "SELECT * FROM ingest_observations WHERE dataset_id=? AND period=?",
                        (p.dataset_id, p.period),
                    ).fetchone()
                    if old is None:
                        db.execute(
                            "INSERT INTO ingest_observations VALUES (?,?,?,?,1,?,?,?)",
                            (
                                p.dataset_id,
                                p.period,
                                p.value,
                                p.quality,
                                finished.isoformat(),
                                finished.isoformat(),
                                run_id,
                            ),
                        )
                        changes["inserted"] += 1
                    elif old["value"] != p.value or old["quality"] != p.quality:
                        db.execute(
                            "INSERT INTO ingest_revisions VALUES (?,?,?,?,?,?,?)",
                            (
                                p.dataset_id,
                                p.period,
                                old["revision"],
                                old["value"],
                                old["quality"],
                                finished.isoformat(),
                                run_id,
                            ),
                        )
                        db.execute(
                            "UPDATE ingest_observations SET value=?,quality=?,revision=revision+1,changed_at=?,run_id=? WHERE dataset_id=? AND period=?",
                            (
                                p.value,
                                p.quality,
                                finished.isoformat(),
                                run_id,
                                p.dataset_id,
                                p.period,
                            ),
                        )
                        changes["revised"] += 1
                for spec in adapter.series:
                    metadata = {
                        **asdict(spec),
                        "source_url": batch.source_url,
                        "source_hash": batch.source_hash,
                        "validation": batch.metadata[spec.id],
                        "source_checked_at": batch.checked_at.isoformat(),
                        "parser_version": 1,
                    }
                    db.execute(
                        "UPDATE ingest_datasets SET metadata=?,updated_at=? WHERE id=?",
                        (dumps(metadata), finished.isoformat(), spec.id),
                    )
                full_check = (
                    finished.timestamp()
                    if not more and full
                    else job["last_full_check"]
                )
                db.execute(
                    "UPDATE ingest_jobs SET cursor=?,next_due=?,failures=0,last_success=?,error_code=NULL,source_hash=?,last_full_check=? WHERE provider=?",
                    (
                        cursor,
                        finished.timestamp() + (60 if more else 86400),
                        finished.isoformat(),
                        batch.source_hash,
                        full_check,
                        provider,
                    ),
                )
                state = (
                    "unchanged" if unchanged else "backfilling" if more else "complete"
                )
                db.execute(
                    "UPDATE ingest_runs SET finished_at=?,state=?,inserted=?,revised=?,source_hash=?,byte_count=?,source_checked_at=? WHERE id=?",
                    (
                        finished.isoformat(),
                        state,
                        changes["inserted"],
                        changes["revised"],
                        batch.source_hash,
                        batch.byte_count,
                        batch.checked_at.isoformat(),
                        run_id,
                    ),
                )
            return {"state": state, "provider": provider, **changes, "cursor": cursor}
        except Exception as exc:  # noqa: BLE001 -- durable provider boundary
            # Persist a safe failure without replacing last good observations or metadata.
            code = (
                exc.code
                if isinstance(exc, ProviderError)
                and re.fullmatch(r"[a-z0-9_]{1,64}", exc.code)
                else "internal_error"
            )
            if started:
                with self.store.connection(True, timeout=2) as db:
                    held = db.execute(
                        "SELECT owner FROM leases WHERE name=?", (lease,)
                    ).fetchone()
                    if held and held["owner"] == owner:
                        failures = min(job["failures"] + 1, 20)
                        delay = max(
                            min(86400, 60 * 2 ** min(failures, 10)),
                            getattr(exc, "retry_after", 0),
                        )
                        db.execute(
                            "UPDATE ingest_jobs SET failures=?,error_code=?,next_due=? WHERE provider=?",
                            (
                                failures,
                                code,
                                self.now_fn().timestamp() + delay,
                                provider,
                            ),
                        )
                        db.execute(
                            "UPDATE ingest_runs SET finished_at=?,state='failed',error_code=? WHERE id=?",
                            (self.now_fn().isoformat(), code, run_id),
                        )
            return {"state": "failed", "provider": provider, "error_code": code}
        finally:
            self.store.release(lease, owner, timeout=2)

    def status(self):
        with self.store.connection(timeout=2) as db:
            return {
                "jobs": [
                    dict(r)
                    for r in db.execute("SELECT * FROM ingest_jobs ORDER BY provider")
                ],
                "datasets": [
                    dict(r)
                    for r in db.execute(
                        "SELECT id,public_display,ai_allowed,rights_state FROM ingest_datasets ORDER BY id"
                    )
                ],
                "observations": db.execute(
                    "SELECT COUNT(*) FROM ingest_observations"
                ).fetchone()[0],
                "revisions": db.execute(
                    "SELECT COUNT(*) FROM ingest_revisions"
                ).fetchone()[0],
            }


class IngestionWorker:
    """Existing supervisor dispatches this bounded worker; it never waits for HTTP."""

    def __init__(self, store, enabled=False):
        self.store, self.enabled = store, enabled
        self._lock = Lock()
        self._pool = None
        self._future = None
        self._engine = None
        self._stopped = False
        self._cancel = Event()
        self._reset_engine = False
        self.error_code = None

    def _run(self):
        try:
            if self._engine is None:
                from backend.app.ingestion.world_bank import WorldBank

                self._engine = Ingestion(
                    self.store,
                    [WorldBank(cancel_event=self._cancel)],
                    cancel_event=self._cancel,
                )
            self._engine.cancel_event = self._cancel
            result = self._engine.run_once()
            if result["state"] != "idle":
                self.error_code = result.get("error_code")
        except Exception:  # noqa: BLE001 -- supervised worker/diagnostic boundary
            self.error_code = (
                "worker_error"  # Next tick retries, no unhandled Future exception.
            )

    def start(self):
        with self._lock:
            if self._stopped:
                self._pool = None
                self._reset_engine = True
            self._stopped = False

    def tick(self):
        with self._lock:
            if (
                not self.enabled
                or self._stopped
                or (self._future and not self._future.done())
            ):
                return
            if self._reset_engine:
                self._engine = None
                self._cancel = Event()
                self._reset_engine = False
            if self._pool is None:
                self._pool = ThreadPoolExecutor(
                    max_workers=1, thread_name_prefix="macrolens-ingestion"
                )
            self._future = self._pool.submit(self._run)

    def stop(self):
        with self._lock:
            self._stopped = True
            self._cancel.set()
            if self._pool:
                self._pool.shutdown(wait=False, cancel_futures=True)

    def status(self):
        detail = None
        if self._engine is not None:
            try:
                detail = self._engine.status()
            except Exception:  # noqa: BLE001 -- supervised worker/diagnostic boundary
                self.error_code = "status_unavailable"
        return {
            "state": detail,
            "enabled": self.enabled,
            "in_progress": bool(self._future and not self._future.done()),
            "error_code": self.error_code,
            "public_display": False,
            "ai_allowed": False,
        }
