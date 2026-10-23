from __future__ import annotations

import os
import pickle
from pathlib import Path
from typing import Any

LOCAL_CACHE_DIR = Path("cache")
REDIS_KEY_PREFIX = "macrolens:cache:"


def load_macro_cache(name: str) -> Any:
    """Load an existing MacroLens cache without importing Streamlit-era storage.

    Local pickle is the zero-cost/default development path. Redis remains
    supported when REDIS_URL is configured, but the dependency is imported
    lazily so local development is not coupled to Redis.
    """
    redis_url = os.getenv("REDIS_URL", "").strip()
    if redis_url:
        try:
            from redis import Redis
            from redis.exceptions import RedisError
        except ImportError as exc:
            raise RuntimeError("REDIS_URL is configured but redis is not installed.") from exc

        try:
            client = Redis.from_url(
                redis_url,
                decode_responses=False,
                socket_connect_timeout=10,
                socket_timeout=30,
                health_check_interval=30,
            )
            payload = client.get(f"{REDIS_KEY_PREFIX}{name}")
        except RedisError as exc:
            raise RuntimeError(f"Could not load '{name}' from shared cache.") from exc

        if payload is None:
            raise FileNotFoundError(f"No shared cached object found for '{name}'.")
        return pickle.loads(payload)

    path = LOCAL_CACHE_DIR / f"{name}.pkl"
    if not path.exists():
        raise FileNotFoundError(f"No local cached object found for '{name}'.")
    with path.open("rb") as file:
        return pickle.load(file)
