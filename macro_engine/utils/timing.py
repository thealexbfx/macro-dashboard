from __future__ import annotations

from contextlib import contextmanager
from time import perf_counter
from typing import Iterator


@contextmanager
def log_runtime(label: str) -> Iterator[None]:
    started_at = perf_counter()

    try:
        yield
    finally:
        elapsed_seconds = perf_counter() - started_at

        print(
            f"[PERFORMANCE] "
            f"{label}: "
            f"{elapsed_seconds:.2f}s"
        )