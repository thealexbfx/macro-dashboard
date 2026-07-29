from datetime import date

from macro_engine.comparison import (
    build_comparison_observations,
    build_recent_environment_change,
    pillar_for,
)
from macro_engine.models.environment import (
    MacroEnvironmentResult,
    MacroEnvironmentSnapshot,
)
from macro_engine.models.pillar import PillarResult


def make_pillar(economy: str, name: str, score: float) -> PillarResult:
    return PillarResult(
        pillar_id=f"{economy.lower()}_{name.lower()}",
        name=f"{economy} {name}",
        economy=economy,
        state_score=score,
        state_label="Positive" if score > 0 else "Negative" if score < 0 else "Neutral",
        trend_score=score,
        trend_label="Improving" if score > 0 else "Weakening" if score < 0 else "Stable",
        breadth_score=0.5,
        breadth_label="Balanced",
        confidence_score=0.75,
        confidence_label="High",
        buckets_used=1,
        bucket_results=(),
    )


def make_result(
    economy: str,
    *,
    growth: float,
    inflation: float,
    liquidity: float,
    policy: float,
    confidence: float = 0.75,
    conviction: float = 0.65,
) -> MacroEnvironmentResult:
    pillars = tuple(
        make_pillar(economy, name, score)
        for name, score in (
            ("Growth", growth),
            ("Inflation", inflation),
            ("Labor", 0.1),
            ("Liquidity", liquidity),
            ("Policy", policy),
        )
    )
    return MacroEnvironmentResult(
        economy=economy,
        as_of_date=date(2026, 6, 30),
        pillar_results=pillars,
        pillar_map={pillar.name: pillar for pillar in pillars},
        overall_direction="Improving",
        environment_label="Stable Expansion",
        environment_summary="Test environment.",
        confidence_score=confidence,
        confidence_label="High",
        environment_conviction_score=conviction,
        environment_conviction_label="Moderate",
    )


def make_snapshot(as_of_date: date, label: str) -> MacroEnvironmentSnapshot:
    return MacroEnvironmentSnapshot(
        economy="USA",
        as_of_date=as_of_date,
        activity_score=0.2,
        activity_label="Positive",
        inflation_impulse_score=0.1,
        inflation_impulse_label="Stable",
        financial_impulse_score=0.0,
        financial_impulse_label="Neutral",
        environment_label=label,
        confidence_score=0.7,
        environment_conviction_score=0.6,
        environment_conviction_label="Moderate",
    )


def test_pillar_for_matches_normalized_pillar_id() -> None:
    result = make_result(
        "USA",
        growth=0.4,
        inflation=0.2,
        liquidity=-0.1,
        policy=0.3,
    )

    assert pillar_for(result, "growth") is not None
    assert pillar_for(result, "growth").state_score == 0.4


def test_observations_select_cross_economy_extremes() -> None:
    usa = make_result(
        "USA",
        growth=0.6,
        inflation=0.1,
        liquidity=0.2,
        policy=0.1,
    )
    japan = make_result(
        "Japan",
        growth=-0.2,
        inflation=0.5,
        liquidity=-0.7,
        policy=0.4,
    )

    observations = build_comparison_observations((usa, japan))

    assert len(observations) == 4
    assert observations[0].economy == "United States"
    assert observations[1].economy == "Japan"
    assert observations[2].economy == "Japan"
    assert observations[3].economy == "Japan"
    assert "sell" not in " ".join(item.message for item in observations).lower()


def test_recent_change_uses_latest_two_successful_snapshots() -> None:
    result = make_result(
        "USA",
        growth=0.4,
        inflation=0.2,
        liquidity=-0.1,
        policy=0.3,
    )
    snapshots = (
        make_snapshot(date(2026, 4, 30), "Slowdown"),
        make_snapshot(date(2026, 5, 31), "Slowdown"),
        make_snapshot(date(2026, 6, 30), "Stable Expansion"),
    )

    change = build_recent_environment_change(result, snapshots)

    assert change is not None
    assert change.economy == "United States"
    assert change.current_environment == "Stable Expansion"
    assert change.previous_environment == "Slowdown"
    assert change.changed is True


def test_recent_change_requires_two_successful_snapshots() -> None:
    result = make_result(
        "USA",
        growth=0.4,
        inflation=0.2,
        liquidity=-0.1,
        policy=0.3,
    )

    assert build_recent_environment_change(
        result,
        (make_snapshot(date(2026, 6, 30), "Stable Expansion"),),
    ) is None
