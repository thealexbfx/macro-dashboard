from __future__ import annotations

from macro_engine.refresh.loaders import (
    load_usa_macro_environment,
    load_euro_macro_environment,
    load_uk_macro_environment,
    load_japan_macro_environment,
)


def refresh_macro() -> None:
    print("Refreshing USA...")
    load_usa_macro_environment()

    print("Refreshing Euro Area...")
    load_euro_macro_environment()

    print("Refreshing United Kingdom...")
    load_uk_macro_environment()

    print("Refreshing Japan...")
    load_japan_macro_environment()

    print("Macro refresh complete.")