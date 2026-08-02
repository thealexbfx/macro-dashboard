from __future__ import annotations

import os
import pickle
from pathlib import Path
from typing import Any

from redis import Redis
from redis.exceptions import RedisError


LOCAL_CACHE_DIR = Path("cache")
REDIS_KEY_PREFIX = "macrolens:cache:"


def _redis_url() -> str | None:
    value = os.getenv("REDIS_URL")

    if not value:
        return None

    return value.strip()


def _redis_client() -> Redis | None:
    url = _redis_url()

    if url is None:
        return None

    return Redis.from_url(
        url,
        decode_responses=False,
        socket_connect_timeout=10,
        socket_timeout=30,
        health_check_interval=30,
    )


def _cache_key(name: str) -> str:
    return f"{REDIS_KEY_PREFIX}{name}"


def _local_cache_path(name: str) -> Path:
    return LOCAL_CACHE_DIR / f"{name}.pkl"


def _save_local(
    name: str,
    value: Any,
) -> None:
    LOCAL_CACHE_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    destination = _local_cache_path(name)
    temporary = destination.with_suffix(".tmp")

    with temporary.open("wb") as file:
        pickle.dump(
            value,
            file,
            protocol=pickle.HIGHEST_PROTOCOL,
        )

    temporary.replace(destination)


def _load_local(name: str) -> Any:
    path = _local_cache_path(name)

    if not path.exists():
        raise FileNotFoundError(
            f"No local cached object found for '{name}'."
        )

    with path.open("rb") as file:
        return pickle.load(file)


def save_cache(
    name: str,
    value: Any,
) -> None:
    payload = pickle.dumps(
        value,
        protocol=pickle.HIGHEST_PROTOCOL,
    )

    client = _redis_client()

    if client is not None:
        try:
            client.set(
                _cache_key(name),
                payload,
            )
            return

        except RedisError as exc:
            raise RuntimeError(
                f"Could not save '{name}' to shared cache."
            ) from exc

    _save_local(
        name,
        value,
    )


def load_cache(name: str) -> Any:
    client = _redis_client()

    if client is not None:
        try:
            payload = client.get(
                _cache_key(name)
            )

        except RedisError as exc:
            raise RuntimeError(
                f"Could not load '{name}' from shared cache."
            ) from exc

        if payload is None:
            raise FileNotFoundError(
                f"No shared cached object found for '{name}'."
            )

        return pickle.loads(payload)

    return _load_local(name)


def cache_exists(name: str) -> bool:
    client = _redis_client()

    if client is not None:
        try:
            return bool(
                client.exists(
                    _cache_key(name)
                )
            )

        except RedisError:
            return False

    return _local_cache_path(name).exists()