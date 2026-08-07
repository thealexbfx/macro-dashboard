from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import date
from typing import Callable, Any

from app_pages.macro_engine.loaders import (
    JAPAN_HISTORY_START_DATE,
    STANDARD_HISTORY_START_DATE,
)

from macro_engine.cache.storage import save_cache

from macro_engine.pipelines.environment import (
    run_euro_macro_environment,
    run_japan_macro_environment,
    run_uk_macro_environment,
    run_usa_macro_environment,
)

from macro_engine.pipelines.history import (
    run_euro_environment_history,
    run_japan_environment_history,
    run_uk_environment_history,
    run_usa_environment_history,
)


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
            run_usa_macro_environment,
        ),
        (
            "Euro Area environment",
            "euro_environment",
            run_euro_macro_environment,
        ),
        (
            "United Kingdom environment",
            "uk_environment",
            run_uk_macro_environment,
        ),
        (
            "Japan environment",
            "japan_environment",
            run_japan_macro_environment,
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
            lambda: run_usa_environment_history(
                start_date=STANDARD_HISTORY_START_DATE,
                end_date=today,
                frequency="monthly",
                continue_on_error=True,
            ),
        ),
        (
            "Euro Area environment history",
            "euro_environment_history",
            lambda: run_euro_environment_history(
                start_date=STANDARD_HISTORY_START_DATE,
                end_date=today,
                frequency="monthly",
                continue_on_error=True,
            ),
        ),
        (
            "United Kingdom environment history",
            "uk_environment_history",
            lambda: run_uk_environment_history(
                start_date=STANDARD_HISTORY_START_DATE,
                end_date=today,
                frequency="monthly",
                continue_on_error=True,
            ),
        ),
        (
            "Japan environment history",
            "japan_environment_history",
            lambda: run_japan_environment_history(
                start_date=JAPAN_HISTORY_START_DATE,
                end_date=today,
                frequency="monthly",
                continue_on_error=True,
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