"""A shared, non-queuing cap for expensive V2 analytical work per process."""

from contextlib import contextmanager
from threading import BoundedSemaphore


class WorkloadBusy(RuntimeError):
    pass


class WorkloadLimit:
    def __init__(self, capacity=1):
        self.semaphore = BoundedSemaphore(capacity)

    @contextmanager
    def enter(self):
        if not self.semaphore.acquire(blocking=False):
            raise WorkloadBusy("Research worker is busy; retry shortly.")
        try:
            yield
        finally:
            self.semaphore.release()


analytical_workload = WorkloadLimit()
