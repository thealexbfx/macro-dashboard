from __future__ import annotations

import traceback
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from typing import Any, Callable

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


def run_refresh_jobs(
    jobs: list[tuple[str, str, Callable[[], Any]]],
    *,
    failure_label: str,
) -> list[str]:
    """
    Run refresh jobs concurrently.

    A failure in one job does not prevent the other jobs from completing.
    Failed jobs keep their previous cached value because save_cache() is
    only called after the loader completes successfully.
    """
    failures: list[str] = []

    with ThreadPoolExecutor(max_workers=4) as executor:
        future_map = {
            executor.submit(
                refresh_and_save,
                display_name=display_name,
                cache_name=cache_name,
                loader=loader,
            ): display_name
            for display_name, cache_name, loader in jobs
        }

        for future, display_name in future_map.items():
            try:
                future.result()

            except Exception as exc:
                failures.append(display_name)

                print()
                print("=" * 60)
                print(f"ERROR refreshing {display_name}")
                print(f"{type(exc).__name__}: {exc}")
                traceback.print_exc()
                print("=" * 60)
                print()

    if failures:
        print(
            f"WARNING: Some {failure_label} failed to refresh: "
            + ", ".join(failures)
        )

    return failures


def refresh_current_environments() -> list[str]:
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

    return run_refresh_jobs(
        jobs,
        failure_label="current environments",
    )


def refresh_environment_histories() -> list[str]:
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

    return run_refresh_jobs(
        jobs,
        failure_label="environment histories",
    )


def refresh_all() -> None:
    print("=" * 60)
    print("Refreshing MacroLens")
    print("=" * 60)

    print()
    print("CURRENT ENVIRONMENTS")
    print("-" * 60)

    current_failures = refresh_current_environments()

    print()
    print("ENVIRONMENT HISTORIES")
    print("-" * 60)

    history_failures = refresh_environment_histories()

    print()
    print("=" * 60)

    if current_failures or history_failures:
        print("MacroLens refresh completed with warnings.")

        if current_failures:
            print(
                "Current environment failures: "
                + ", ".join(current_failures)
            )

        if history_failures:
            print(
                "Environment history failures: "
                + ", ".join(history_failures)
            )

        print(
            "Successful refreshes were saved. "
            "Failed refreshes retain their previous cached values."
        )

    else:
        print("MacroLens refresh complete.")

    print("=" * 60)


if __name__ == "__main__":
    refresh_all()