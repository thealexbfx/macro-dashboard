from __future__ import annotations

from macro_engine.pipelines.environment import run_usa_macro_environment


DIVIDER = "=" * 64
SUB_DIVIDER = "-" * 64


def format_score(score: float) -> str:
    return f"{score:+.2f}"


def format_optional_date(value: object) -> str:
    return str(value) if value is not None else "Latest available data"


def print_header(title: str) -> None:
    print()
    print(DIVIDER)
    print(title)
    print(DIVIDER)


def print_current_environment(result: object) -> None:
    print_header("MACROLENS — USA MACRO ENVIRONMENT")

    print(f"Economy:       {result.economy}")
    print(f"As of:         {format_optional_date(result.as_of_date)}")

    print()
    print(f"Environment:   {result.environment_label}")
    print(f"Direction:     {result.overall_direction}")
    print(
        f"Confidence:    {result.confidence_label} "
        f"({result.confidence_score:.2f})"
    )
    print(
        f"Conviction:    {result.environment_conviction_label} "
        f"({result.environment_conviction_score:.2f})"
    )

    print()
    print(result.environment_summary)


def print_dimensions(result: object) -> None:
    print_header("MACRO DIMENSIONS")

    dimensions = (
        (
            "Activity",
            result.activity_label,
            result.activity_score,
            result.dimension_margins.get("activity"),
        ),
        (
            "Inflation",
            result.inflation_impulse_label,
            result.inflation_impulse_score,
            result.dimension_margins.get("inflation"),
        ),
        (
            "Financial",
            result.financial_impulse_label,
            result.financial_impulse_score,
            result.dimension_margins.get("financial"),
        ),
    )

    for name, label, score, margin in dimensions:
        margin_text = (
            f"{margin:.2f}"
            if isinstance(margin, (int, float))
            else "N/A"
        )

        print(
            f"{name:<12}"
            f"{label:<18}"
            f"Score: {format_score(score):>6}   "
            f"Margin: {margin_text}"
        )


def print_pillars(result: object) -> None:
    print_header("USA MACRO PILLARS")

    for pillar in result.pillar_results:
        print(f"{pillar.name}")
        print(SUB_DIVIDER)

        print(
            f"State:       {pillar.state_label} "
            f"({format_score(pillar.state_score)})"
        )
        print(
            f"Trend:       {pillar.trend_label} "
            f"({format_score(pillar.trend_score)})"
        )
        print(
            f"Breadth:     {pillar.breadth_label} "
            f"({pillar.breadth_score:.2f})"
        )
        print(
            f"Confidence:  {pillar.confidence_label} "
            f"({pillar.confidence_score:.2f})"
        )

        if pillar.flags:
            print(f"Flags:       {', '.join(pillar.flags)}")

        if pillar.key_drivers:
            print("Drivers:")

            for driver in pillar.key_drivers:
                print(f"  - {driver}")

        print()


def print_key_drivers(result: object) -> None:
    print_header("ENVIRONMENT DRIVERS")

    if not result.key_drivers:
        print("No key drivers were identified.")
        return

    for driver in result.key_drivers:
        print(f"- {driver}")


def print_signals(result: object) -> None:
    print_header("SIGNALS AND RISKS")

    simple_sections = (
        ("Confirmations", result.confirmations),
        ("Tensions", result.tensions),
        ("Flags", result.flags),
    )

    for title, values in simple_sections:
        print(f"{title}:")

        if values:
            for value in values:
                print(f"  - {value}")
        else:
            print("  None")

        print()

    print("Transition signals:")

    if not result.transition_signals:
        print("  None")
    else:
        for signal in result.transition_signals:
            print(f"  - [{signal.severity.upper()}] {signal.message}")

            if signal.pillars:
                print(f"    Pillars: {', '.join(signal.pillars)}")

            print(f"    Code: {signal.code}")

    print()

def main() -> None:
    result = run_usa_macro_environment()

    print_current_environment(result)
    print_dimensions(result)
    print_pillars(result)
    print_key_drivers(result)
    print_signals(result)

    print(DIVIDER)
    print("END OF USA MACRO ENVIRONMENT REPORT")
    print(DIVIDER)


if __name__ == "__main__":
    main()