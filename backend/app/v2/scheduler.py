"""Supervised local refresh loop. Diagnostics contain no exception messages/secrets."""

from __future__ import annotations

import logging
from copy import deepcopy
from datetime import UTC, datetime
from threading import Event, Lock, Thread

from backend.app.v2.workload import WorkloadBusy


class RefreshScheduler:
    def __init__(self, target, interval=60, now_fn=None):
        self.target = target
        self.interval = interval
        self.now_fn = now_fn or (lambda: datetime.now(UTC))
        self.lock = Lock()
        self.stop_event = Event()
        self.thread = None
        self.diagnostics = {
            "started_at": None,
            "heartbeat": None,
            "last_attempt": None,
            "last_success": None,
            "last_failure": None,
            "error_type": None,
            "consecutive_failures": 0,
            "in_progress": False,
            "skipped_busy": 0,
        }

    def start(self):
        if self.thread and self.thread.is_alive():
            return
        self.stop_event = Event()
        stamp = self.now_fn().isoformat()
        with self.lock:
            self.diagnostics.update(
                started_at=stamp, heartbeat=stamp, in_progress=False
            )
        self.thread = Thread(target=self._run, daemon=True, name="macrolens-discovery")
        self.thread.start()

    def _run(self):
        while not self.stop_event.wait(self.interval):
            self.run_once()

    def run_once(self):
        stamp = self.now_fn().isoformat()
        with self.lock:
            self.diagnostics.update(
                heartbeat=stamp, last_attempt=stamp, in_progress=True
            )
        try:
            self.target()
        except WorkloadBusy:
            with self.lock:
                self.diagnostics["skipped_busy"] += 1
        except Exception as exc:  # noqa: BLE001 -- supervise the outer worker boundary
            # An unexpected exception is an engine failure, not a reason to lose the loop.
            with self.lock:
                self.diagnostics.update(
                    last_failure=self.now_fn().isoformat(),
                    error_type=type(exc).__name__,
                )
                self.diagnostics["consecutive_failures"] += 1
            logging.getLogger(__name__).warning(
                "Discovery refresh failed (%s); evidence retained; next tick will retry.",
                type(exc).__name__,
            )
        else:
            with self.lock:
                self.diagnostics.update(
                    last_success=self.now_fn().isoformat(),
                    consecutive_failures=0,
                    error_type=None,
                )
        finally:
            with self.lock:
                self.diagnostics.update(
                    heartbeat=self.now_fn().isoformat(), in_progress=False
                )

    def status(self):
        with self.lock:
            result = deepcopy(self.diagnostics)
        result["thread_alive"] = bool(self.thread and self.thread.is_alive())
        result["stopping"] = self.stop_event.is_set()
        age = (
            (
                self.now_fn() - datetime.fromisoformat(result["heartbeat"])
            ).total_seconds()
            if result["heartbeat"]
            else None
        )
        result["heartbeat_age_seconds"] = age
        result["ready"] = (
            result["thread_alive"]
            and not result["stopping"]
            and age is not None
            and age <= max(180, self.interval * 3)
            and result["consecutive_failures"] < 3
        )
        return result

    def stop(self):
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=5)
