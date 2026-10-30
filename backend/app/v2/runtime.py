"""Bounded Discovery reads with preserved SQLite evidence and on-demand archives."""

from __future__ import annotations

import json
import uuid
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import UTC, datetime
from hashlib import sha256
from threading import Lock
from time import monotonic

from backend.app.v2.definitions import SPECS
from backend.app.v2.dynamic_scan import VERSION, scan
from backend.app.v2.followups import suggestions
from backend.app.v2.history import HistoricalLibrary
from backend.app.v2.memory import DiscoveryMemory
from backend.app.v2.state import dumps
from backend.app.v2.workload import WorkloadBusy, analytical_workload


class DynamicDiscovery:
    def __init__(
        self, data_service, transform_fn, store, workload=None, cache_seconds=30
    ):
        self.data_service, self.transform_fn, self.store = (
            data_service,
            transform_fn,
            store,
        )
        self.memory = DiscoveryMemory(store)
        self.library = HistoricalLibrary(store, transform_fn)
        self.lock = Lock()
        self.workload = workload or analytical_workload
        self.cache_seconds = cache_seconds
        self._cache = None
        self._expires = 0
        self._cache_day = None
        self._cache_signature = None
        self._data = None
        self._data_signature = None
        self._data_day = None
        self._enriched = None
        self._enriched_key = None

    def _now(self):
        return (
            self.data_service.now_fn()
            if hasattr(self.data_service, "now_fn")
            else datetime.now(UTC)
        )

    def _metadata(self):
        with self.store.connection() as db:
            sources = [
                tuple(r)
                for r in db.execute(
                    "SELECT id,checked_at,next_due,failures FROM source_cache ORDER BY id"
                )
            ]
            report = db.execute(
                "SELECT fingerprint,calculated_at FROM reports WHERE id='current'"
            ).fetchone()
            ai = tuple(
                db.execute("SELECT COUNT(*),MAX(generated_at) FROM ai_cache").fetchone()
            )
            revision = tuple(
                db.execute(
                    "SELECT COUNT(*),MAX(last_meaningful),SUM(version) FROM stories WHERE status!='Archived'"
                ).fetchone()
            )
            totals = (
                tuple(
                    tuple(r)
                    for r in db.execute(
                        "SELECT status,COUNT(*) FROM stories GROUP BY status"
                    )
                ),
                db.execute("SELECT COUNT(*) FROM library").fetchone()[0],
            )
        return sources, (tuple(report) if report else None), ai, revision, totals

    def get(self, force_check=False):
        day = str(self.data_service.today_fn())
        if (
            not force_check
            and self._cache is not None
            and self._cache_day == day
            and monotonic() < self._expires
        ):
            return deepcopy(self._cache)
        if not self.lock.acquire(blocking=False):
            raise WorkloadBusy("Discovery refresh is running; retry shortly.")
        try:
            with self.workload.enter():
                metadata = self._metadata()
                sources = metadata[0]
                now = self._now()
                due = any(datetime.fromisoformat(r[2]) <= now for r in sources)
                if (
                    sources
                    and self._cache is not None
                    and metadata == self._cache_signature
                    and not due
                    and self._cache_day == day
                ):
                    result = self._cache
                else:
                    result = self._build(metadata, due, day)
                self._cache = result
                self._cache_day = day
                self._cache_signature = self._metadata()
                # Unknown/non-persistent test services cannot safely use the source-revision shortcut.
                ttl = self.cache_seconds if self._cache_signature[0] else 0
                if self._cache_signature[0]:
                    ttl = min(
                        ttl,
                        max(
                            1,
                            min(
                                (
                                    datetime.fromisoformat(r[2]) - self._now()
                                ).total_seconds()
                                for r in self._cache_signature[0]
                            ),
                        ),
                    )
                self._expires = monotonic() + ttl
                return deepcopy(result)
        finally:
            self.lock.release()

    def _build(self, metadata, due, day):
        source_signature = metadata[0]
        if (
            not source_signature
            or self._data is None
            or source_signature != self._data_signature
            or due
            or day != self._data_day
        ):
            with ThreadPoolExecutor(max_workers=5) as pool:
                self._data = list(pool.map(self.data_service.get, SPECS))
            self._data_signature = self._metadata()[0]
            self._data_day = day
            self._numeric_fingerprint = sha256(
                dumps(
                    {
                        "version": VERSION,
                        "data": [
                            (
                                d.id,
                                d.status,
                                d.definition,
                                [o.model_dump() for o in d.observations],
                                d.verification.get("status"),
                            )
                            for d in self._data
                        ],
                    }
                ).encode()
            ).hexdigest()
        data = self._data
        fingerprint = self._numeric_fingerprint
        with self.store.connection() as db:
            previous = db.execute("SELECT * FROM reports WHERE id='current'").fetchone()
        if previous and previous["fingerprint"] == fingerprint:
            report = json.loads(previous["payload"])
        else:
            owner = uuid.uuid4().hex
            if not self.store.acquire(
                "scan", owner, datetime.now(UTC).timestamp(), 300
            ):
                raise RuntimeError(
                    "A discovery scan is already running; persisted evidence retained. Retry shortly."
                )
            try:
                report = scan(data, self.transform_fn, self.data_service.today_fn())
                self.memory.apply(report["findings"], data, now=self._now())
                report["active_keys"] = [f["event_key"] for f in report["findings"]]
                report["snapshot_fingerprint"] = fingerprint
                self.library.seed(data, self._now())
                with self.store.connection(True) as db:
                    db.execute(
                        "INSERT OR REPLACE INTO reports VALUES (?,?,?,?)",
                        ("current", fingerprint, dumps(report), report["generated_at"]),
                    )
            finally:
                self.store.release("scan", owner)
        counts = self.memory.counts()
        keys = set(report["active_keys"])
        current_metadata = self._metadata()
        enriched_key = (
            fingerprint,
            day,
            current_metadata[2],
            current_metadata[3],
            counts["historical"],
        )
        if self._enriched_key != enriched_key:
            candidates = self.memory.list(
                keys, data, now=self._now(), archived=False, event_keys=keys, limit=100
            )
            eligible = [
                f
                for f in candidates
                if f["lifecycle"]["qualifies_now"]
                and all(v == "ok" for v in f["current_source_status"].values())
                and f["lifecycle"]["status"] in {"New", "Updated"}
            ]
            eligible.sort(
                key=lambda f: (
                    f["lifecycle"]["last_meaningful_update"][:10],
                    f["ranking"]["score"],
                ),
                reverse=True,
            )
            promoted = []
            seen = set()
            for f in eligible:
                identity = tuple(sorted(f["datasets"]))
                if identity in seen:
                    continue
                promoted.append(f)
                seen.add(identity)
                if len(promoted) == 5:
                    break
            following = self.memory.list(
                keys,
                data,
                now=self._now(),
                archived=False,
                limit=10,
                exclude=[f["id"] for f in promoted],
            )
            for f in promoted + following:
                self._suggest(f, data)
            self._enriched = {
                "findings": promoted,
                "following": following,
                "historical": self.library.records(data, limit=6),
            }
            self._enriched_key = enriched_key
        report.update(deepcopy(self._enriched))
        report.update(
            archived=[],
            archived_total=counts["archived"],
            following_total=max(0, counts["active"] - len(report["findings"])),
            historical_total=counts["historical"],
            page_limits={"following": 10, "historical": 6, "archives": 20},
            source_times=[
                {
                    "id": d.id,
                    "observed": d.latest_observation_date,
                    "retrieved": d.retrieved_at,
                    "published": d.publication_date,
                    "status": d.status,
                    "checked": d.release_metadata.get("last_checked_at"),
                    "next_check": d.release_metadata.get("next_check_at"),
                }
                for d in data
            ],
        )
        return report

    def _suggest(self, f, data):
        with self.store.connection() as db:
            cached = db.execute(
                "SELECT payload FROM ai_cache WHERE cache_key=?", (ai_cache_key(f),)
            ).fetchone()
        candidates = (
            json.loads(cached["payload"]).get("candidates", []) if cached else []
        )
        f["suggestions"] = suggestions(f, data, self.transform_fn, candidates)

    def summaries(self, archived=True, limit=20, offset=0, kind="all"):
        exclude = () if archived else tuple(f["id"] for f in self.get()["findings"])
        return self.memory.summaries(
            archived=archived, limit=limit, offset=offset, exclude=exclude, kind=kind
        )

    def story(self, identity):
        report = self.get()
        if not self.lock.acquire(blocking=False):
            raise WorkloadBusy("Discovery refresh is running; retry shortly.")
        try:
            with self.workload.enter():
                rows = self.memory.list(
                    set(report["active_keys"]),
                    self._data,
                    now=self._now(),
                    identity=identity,
                    limit=1,
                )
                if not rows:
                    return None
                f = rows[0]
                # The original archived evidence is returned intact; no unrelated current analysis.
                if f["lifecycle"]["status"] == "Archived":
                    f["suggestions"] = []
                else:
                    self._suggest(f, self._data)
                return f
        finally:
            self.lock.release()

    def historical_page(self, limit=6, offset=0):
        self.get()
        with self.workload.enter():
            total = self.memory.counts()["historical"]
            return {
                "items": self.library.records(self._data, limit=limit, offset=offset),
                "total": total,
                "offset": offset,
                "next_offset": offset + limit if offset + limit < total else None,
            }

    def manual(self):
        owner = uuid.uuid4().hex
        allowed = self.store.acquire(
            "manual-refresh", owner, datetime.now(UTC).timestamp(), 300
        )
        return {
            **self.get(force_check=allowed),
            "manual_refresh": {
                "accepted": allowed,
                "cooldown_seconds": 300,
                "note": "Checked due sources only. No AI generation; no rate-limit bypass.",
            },
        }


def ai_cache_key(f):
    return sha256(
        dumps(
            {
                "id": f["id"],
                "version": f.get("evidence_version", 1),
                "fingerprint": f.get("evidence_fingerprint"),
                "prompt": "research-candidates-v1",
                "model": "gpt-6-luna",
            }
        ).encode()
    ).hexdigest()
