"""Release-aware persistent cache around the unchanged V2 data provider path."""

from __future__ import annotations

import json
import logging
import uuid
from datetime import UTC, datetime, timedelta
from threading import Lock
from time import monotonic

from backend.app.v2.definitions import SPECS
from backend.app.v2.integrity import assess_freshness
from backend.app.v2.state import dumps


def interval(dataset, now, failures=0):
    if not dataset.release_metadata.get(
        "source_check_succeeded", dataset.status == "ok"
    ):
        return min(3600, 300 * 2 ** min(failures, 4))
    if dataset.frequency == "daily":
        return 21600
    if dataset.frequency == "weekly":
        return 43200
    next_release = dataset.release_metadata.get("next_release_date")
    if next_release:
        distance = (datetime.fromisoformat(next_release).date() - now.date()).days
        if distance <= 1:
            return 10800
        if distance <= 7:
            return 43200
    return 86400


def scheduled_service_class(base, dataset_class):
    class ScheduledDataService(base):
        def __init__(self, store, *args, now_fn=None, **kwargs):
            super().__init__(*args, **kwargs)
            self.store = store
            self.now_fn = now_fn or (lambda: datetime.now(UTC))
            self.key_locks = {key: Lock() for key in SPECS}

        def get(self, key):
            if key not in SPECS:
                raise ValueError("Unknown dataset ID")
            withheld = self.withheld_dataset(key)
            if withheld is not None:
                return withheld
            with self.key_locks[key]:
                now = self.now_fn()
                with self.store.connection() as db:
                    cached = db.execute(
                        "SELECT * FROM source_cache WHERE id=?", (key,)
                    ).fetchone()
                if cached and datetime.fromisoformat(cached["next_due"]) > now:
                    d = legacy_telemetry_view(
                        dataset_class.model_validate(json.loads(cached["payload"]))
                    )
                    # Reassess reference freshness, never pretend cache read is retrieval.
                    if d.status == "ok" and d.latest_observation_date:
                        stale, reason, _release = assess_freshness(
                            SPECS[key],
                            datetime.fromisoformat(d.latest_observation_date).date(),
                            self.today_fn(),
                        )
                        if stale:
                            d = d.model_copy(
                                update={"status": "stale", "message": reason}
                            )
                    return d
                owner = uuid.uuid4().hex
                if not self.store.acquire("source:" + key, owner, now.timestamp(), 120):
                    if cached:
                        d = legacy_telemetry_view(
                            dataset_class.model_validate(json.loads(cached["payload"]))
                        )
                        if d.status == "ok" and d.latest_observation_date:
                            stale, reason, _ = assess_freshness(
                                SPECS[key],
                                datetime.fromisoformat(
                                    d.latest_observation_date
                                ).date(),
                                self.today_fn(),
                            )
                            if stale:
                                d = d.model_copy(
                                    update={"status": "stale", "message": reason}
                                )
                        return d
                    return dataset_class(
                        **SPECS[key].__dict__,
                        status="unavailable",
                        message="Source check is already running; retry shortly.",
                    )
                try:
                    if cached:
                        previous = dataset_class.model_validate(
                            json.loads(cached["payload"])
                        )
                        with self.lock:
                            self.cache[key] = (monotonic() - self.ttl - 1, previous)
                    else:
                        # An absent persistent row must not promote a preexisting
                        # in-memory cache hit into a newly checked source success.
                        with self.lock:
                            memory = self.cache.get(key)
                            if memory:
                                self.cache[key] = (
                                    monotonic() - self.ttl - 1,
                                    memory[1],
                                )
                    d = super().get(key)
                    succeeded = d.release_metadata.get("source_check_succeeded") is True
                    failures = (
                        (cached["failures"] if cached else 0) + 1
                        if not succeeded
                        else 0
                    )
                    next_due = now + timedelta(seconds=interval(d, now, failures))
                    metadata = {
                        **d.release_metadata,
                        "last_checked_at": now.isoformat(),
                        "source_check_telemetry": "recorded_success"
                        if succeeded
                        else "recorded_failure",
                        "next_check_at": next_due.isoformat(),
                        "retrieval_time_note": "Provider retrieval and source observation/publication dates are distinct.",
                        "last_source_success_at": now.isoformat()
                        if succeeded
                        else d.release_metadata.get("last_source_success_at"),
                        "source_error_code": None
                        if succeeded
                        else d.release_metadata.get(
                            "source_error_code", "provider_unavailable_or_invalid"
                        ),
                    }
                    d = d.model_copy(update={"release_metadata": metadata})
                    with self.store.connection(True) as db:
                        db.execute(
                            "INSERT OR REPLACE INTO source_cache VALUES (?,?,?,?,?)",
                            (
                                key,
                                dumps(d.model_dump()),
                                now.isoformat(),
                                next_due.isoformat(),
                                failures,
                            ),
                        )
                    logging.getLogger("uvicorn.error.legacy_refresh").log(
                        logging.INFO if succeeded else logging.WARNING,
                        "Legacy source id=%s checked=%s success=%s next=%s failures=%s",
                        key,
                        now.isoformat(),
                        metadata["last_source_success_at"],
                        next_due.isoformat(),
                        failures,
                    )
                    return d
                finally:
                    self.store.release("source:" + key, owner)

        def freshness_summary(self):
            with self.store.connection() as db:
                return [
                    dict(row)
                    for row in db.execute(
                        "SELECT id,checked_at,next_due,failures FROM source_cache ORDER BY id"
                    )
                ]

    return ScheduledDataService


def legacy_telemetry_view(dataset):
    """Annotate old cache reads in memory only; never infer or backfill success."""
    meta = dataset.release_metadata
    if "source_check_succeeded" not in meta and not meta.get("last_source_success_at"):
        return dataset.model_copy(
            update={
                "release_metadata": {
                    **meta,
                    "source_check_telemetry": "legacy_unverified",
                    "last_source_success_at": None,
                }
            }
        )
    return dataset
