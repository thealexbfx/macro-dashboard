from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import date
from typing import Callable, Any

from app_pages.macro_engine.loaders import (
    JAPAN_HISTORY_START_DATE,
    STANDARD_HISTORY_START_DATE,
    load_euro_environment_history,
    load_euro_macro_environment,
    load_japan_environment_history,
    load_japan_macro_environment,
    load_uk_environment_history,
    load_uk_macro_environment,
    load_usa_environment_history,
    load_usa_macro_environment,
)
from macro_engine.cache.storage import save_cache


def refresh_and_save(
    *,
    display_name: str,
    cache_name: str,
    loader: Callable[[], Any],
) -> None:
    print(f"Refreshing {display_name}...")

    result = loader()

    save_cache(
        cache_name,
        result,
    )

    print(f"{display_name} complete.")


def refresh_current_environments() -> None:
    jobs = [
        (
            "USA environment",
            "usa_environment",
            load_usa_macro_environment,
        ),
        (
            "Euro Area environment",
            "euro_environment",
            load_euro_macro_environment,
        ),
        (
            "United Kingdom environment",
            "uk_environment",
            load_uk_macro_environment,
        ),
        (
            "Japan environment",
            "japan_environment",
            load_japan_macro_environment,
        ),
    ]

    with ThreadPoolExecutor(
        max_workers=4
    ) as executor:
        futures = [
            executor.submit(
                refresh_and_save,
                display_name=display_name,
                cache_name=cache_name,
                loader=loader,
            )
            for display_name, cache_name, loader
            in jobs
        ]

        for future in futures:
            future.result()


def refresh_environment_histories() -> None:
    today = date.today()

    jobs = [
        (
            "USA environment history",
            "usa_environment_history",
            lambda: load_usa_environment_history(
                start_date=STANDARD_HISTORY_START_DATE,
                end_date=today,
            ),
        ),
        (
            "Euro Area environment history",
            "euro_environment_history",
            lambda: load_euro_environment_history(
                start_date=STANDARD_HISTORY_START_DATE,
                end_date=today,
            ),
        ),
        (
            "United Kingdom environment history",
            "uk_environment_history",
            lambda: load_uk_environment_history(
                start_date=STANDARD_HISTORY_START_DATE,
                end_date=today,
            ),
        ),
        (
            "Japan environment history",
            "japan_environment_history",
            lambda: load_japan_environment_history(
                start_date=JAPAN_HISTORY_START_DATE,
                end_date=today,
            ),
        ),
    ]

    with ThreadPoolExecutor(
        max_workers=4
    ) as executor:
        futures = [
            executor.submit(
                refresh_and_save,
                display_name=display_name,
                cache_name=cache_name,
                loader=loader,
            )
            for display_name, cache_name, loader
            in jobs
        ]

        for future in futures:
            future.result()


def refresh_all() -> None:
    print("=" * 60)
    print("Refreshing MacroLens")
    print("=" * 60)

    print()
    print("CURRENT ENVIRONMENTS")
    print("-" * 60)

    refresh_current_environments()

    print()
    print("ENVIRONMENT HISTORIES")
    print("-" * 60)

    refresh_environment_histories()

    print()
    print("MacroLens refresh complete.")


if __name__ == "__main__":
    refresh_all()