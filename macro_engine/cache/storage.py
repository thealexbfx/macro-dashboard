from __future__ import annotations

import pickle
from pathlib import Path
from typing import Any


CACHE_DIR = Path("cache")


def _ensure_cache_dir() -> None:
    CACHE_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )


def save_cache(
    name: str,
    value: Any,
) -> None:
    _ensure_cache_dir()

    path = CACHE_DIR / f"{name}.pkl"

    with path.open("wb") as file:
        pickle.dump(
            value,
            file,
            protocol=pickle.HIGHEST_PROTOCOL,
        )


def load_cache(
    name: str,
) -> Any:

    path = CACHE_DIR / f"{name}.pkl"

    if not path.exists():
        raise FileNotFoundError(
            f"No cached object found for '{name}'."
        )

    with path.open("rb") as file:
        return pickle.load(file)


def cache_exists(
    name: str,
) -> bool:

    return (
        CACHE_DIR / f"{name}.pkl"
    ).exists()