"""Scheduled data, deterministic scans and persistent memory; no automatic paid calls."""

from __future__ import annotations

import json
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from hashlib import sha256
from threading import Lock

from backend.app.v2.definitions import SPECS
from backend.app.v2.dynamic_scan import VERSION, scan
from backend.app.v2.followups import suggestions
from backend.app.v2.history import HistoricalLibrary
from backend.app.v2.memory import DiscoveryMemory
from backend.app.v2.state import dumps


class DynamicDiscovery:
    def __init__(self, data_service, transform_fn, store):
        self.data_service, self.transform_fn, self.store = (
            data_service,
            transform_fn,
            store,
        )
        self.memory = DiscoveryMemory(store)
        self.library = HistoricalLibrary(store, transform_fn)
        self.lock = Lock()

    def get(self):
        with self.lock:
            with ThreadPoolExecutor(max_workers=5) as pool:
                data = list(pool.map(self.data_service.get, SPECS))
            fingerprint = sha256(
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
                            for d in data
                        ],
                    }
                ).encode()
            ).hexdigest()
            with self.store.connection() as db:
                previous = db.execute(
                    "SELECT * FROM reports WHERE id='current'"
                ).fetchone()
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
                    self.memory.apply(report["findings"], data)
                    report["active_keys"] = [f["event_key"] for f in report["findings"]]
                    report["snapshot_fingerprint"] = fingerprint
                    self.library.seed(data, datetime.now(UTC))
                    with self.store.connection(True) as db:
                        db.execute(
                            "INSERT OR REPLACE INTO reports VALUES (?,?,?,?)",
                            (
                                "current",
                                fingerprint,
                                dumps(report),
                                report["generated_at"],
                            ),
                        )
                finally:
                    self.store.release("scan", owner)
            stories = self.memory.list(set(report["active_keys"]), data)
            for f in stories:
                candidates = []
                with self.store.connection() as db:
                    cached = db.execute(
                        "SELECT payload FROM ai_cache WHERE cache_key=?",
                        (ai_cache_key(f),),
                    ).fetchone()
                if cached:
                    candidates = json.loads(cached["payload"]).get("candidates", [])
                f["suggestions"] = suggestions(f, data, self.transform_fn, candidates)
            active = [f for f in stories if f["lifecycle"]["status"] != "Archived"]
            eligible = [
                f
                for f in active
                if f["lifecycle"]["qualifies_now"]
                and all(s == "ok" for s in f["current_source_status"].values())
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
                if tuple(sorted(f["datasets"])) in seen:
                    continue
                promoted.append(f)
                seen.add(tuple(sorted(f["datasets"])))
                if len(promoted) == 5:
                    break
            report.update(
                findings=promoted,
                following=[
                    f for f in active if f["id"] not in {i["id"] for i in promoted}
                ],
                archived=[f for f in stories if f["lifecycle"]["status"] == "Archived"],
                historical=self.library.records(data),
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

    def manual(self):
        owner = uuid.uuid4().hex
        allowed = self.store.acquire(
            "manual-refresh", owner, datetime.now(UTC).timestamp(), 300
        )
        # Keep lease until cooldown expires; manual never bypasses source due times.
        return {
            **self.get(),
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
