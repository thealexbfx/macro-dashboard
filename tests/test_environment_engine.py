from datetime import date

import pytest

from macro_engine.engine.environment_engine import (
    build_environment_result,
    calculate_environment_confidence,
    calculate_overall_direction,
    classify_environment_confidence,
    detect_confirmations,
    detect_tensions,
    validate_environment_inputs,
    build_environment_summary,
    calculate_activity_impulse,
    calculate_financial_impulse,
    calculate_inflation_impulse,
    classify_activity_impulse,
    classify_financial_impulse,
    classify_inflation_impulse,
    classify_macro_environment,
    calculate_dimension_margin,
    calculate_dimension_margins,
    calculate_environment_conviction,
    classify_environment_conviction,
    detect_dimension_boundary_flags,
    create_environment_snapshot,
    build_regime_periods,
)
from macro_engine.models.environment import (
    MacroEnvironmentConfig,
    MacroEnvironmentHistory,
    MacroEnvironmentSnapshot,
)
from macro_engine.models.pillar import PillarResult

def make_history_snapshot(
    snapshot_date: date,
    environment_label: str,
    *,
    activity_score: float = 0.20,
    inflation_score: float = 0.30,
    financial_score: float = 0.00,
    confidence_score: float = 0.80,
    conviction_score: float = 0.50,
) -> MacroEnvironmentSnapshot:
    return MacroEnvironmentSnapshot(
        economy="USA",
        as_of_date=snapshot_date,
        activity_score=activity_score,
        activity_label="Expanding",
        inflation_impulse_score=inflation_score,
        inflation_impulse_label="Accelerating",
        financial_impulse_score=financial_score,
        financial_impulse_label="Neutral",
        environment_label=environment_label,
        confidence_score=confidence_score,
        environment_conviction_score=conviction_score,
        environment_conviction_label="Moderate",
        flags=(),
    )
    
def test_build_regime_periods_groups_consecutive_labels() -> None:
    history = MacroEnvironmentHistory(
        economy="USA",
        snapshots=(
            make_history_snapshot(
                date(2026, 1, 31),
                "Goldilocks Expansion",
            ),
            make_history_snapshot(
                date(2026, 2, 28),
                "Goldilocks Expansion",
            ),
            make_history_snapshot(
                date(2026, 3, 31),
                "Reflationary Transition",
            ),
            make_history_snapshot(
                date(2026, 4, 30),
                "Reflationary Transition",
            ),
            make_history_snapshot(
                date(2026, 5, 31),
                "Reflationary Transition",
            ),
        ),
    )

    periods = build_regime_periods(history)

    assert len(periods) == 2

    assert periods[0].environment_label == (
        "Goldilocks Expansion"
    )
    assert periods[0].observation_count == 2
    assert periods[0].is_current is False

    assert periods[1].environment_label == (
        "Reflationary Transition"
    )
    assert periods[1].observation_count == 3
    assert periods[1].is_current is True


def test_build_regime_periods_handles_repeated_nonconsecutive_regime() -> None:
    history = MacroEnvironmentHistory(
        economy="USA",
        snapshots=(
            make_history_snapshot(
                date(2026, 1, 31),
                "Goldilocks Expansion",
            ),
            make_history_snapshot(
                date(2026, 2, 28),
                "Reflationary Transition",
            ),
            make_history_snapshot(
                date(2026, 3, 31),
                "Goldilocks Expansion",
            ),
        ),
    )

    periods = build_regime_periods(history)

    assert len(periods) == 3
    assert periods[0].environment_label == (
        "Goldilocks Expansion"
    )
    assert periods[1].environment_label == (
        "Reflationary Transition"
    )
    assert periods[2].environment_label == (
        "Goldilocks Expansion"
    )


def test_build_regime_periods_calculates_average_scores() -> None:
    history = MacroEnvironmentHistory(
        economy="USA",
        snapshots=(
            make_history_snapshot(
                date(2026, 1, 31),
                "Reflationary Transition",
                confidence_score=0.80,
                conviction_score=0.30,
            ),
            make_history_snapshot(
                date(2026, 2, 28),
                "Reflationary Transition",
                confidence_score=0.90,
                conviction_score=0.50,
            ),
        ),
    )

    period = build_regime_periods(history)[0]

    assert period.average_confidence_score == 0.85
    assert period.average_conviction_score == 0.40


def test_build_regime_periods_tracks_dimension_changes() -> None:
    history = MacroEnvironmentHistory(
        economy="USA",
        snapshots=(
            make_history_snapshot(
                date(2026, 1, 31),
                "Reflationary Transition",
                activity_score=0.16,
                inflation_score=0.30,
                financial_score=-0.05,
            ),
            make_history_snapshot(
                date(2026, 2, 28),
                "Reflationary Transition",
                activity_score=0.28,
                inflation_score=0.45,
                financial_score=0.08,
            ),
        ),
    )

    period = build_regime_periods(history)[0]

    assert period.activity_change == 0.12
    assert period.inflation_change == 0.15
    assert period.financial_change == 0.13

def test_create_environment_snapshot_from_result() -> None:
    config = MacroEnvironmentConfig(
        economy="USA",
        minimum_pillars=5,
    )

    results = (
        make_pillar_result("USA Growth", trend_score=0.25),
        make_pillar_result("USA Inflation", trend_score=0.48),
        make_pillar_result("USA Labor", trend_score=0.04),
        make_pillar_result("USA Liquidity", trend_score=-0.07),
        make_pillar_result("USA Policy", trend_score=0.24),
    )

    result = build_environment_result(
        config=config,
        pillar_results=results,
        as_of_date=date(2026, 7, 21),
    )

    snapshot = create_environment_snapshot(result)

    assert snapshot.economy == result.economy
    assert snapshot.as_of_date == result.as_of_date
    assert snapshot.activity_score == result.activity_score
    assert (
        snapshot.inflation_impulse_score
        == result.inflation_impulse_score
    )
    assert (
        snapshot.financial_impulse_score
        == result.financial_impulse_score
    )
    assert snapshot.environment_label == result.environment_label
    assert snapshot.confidence_score == result.confidence_score
    assert (
        snapshot.environment_conviction_score
        == result.environment_conviction_score
    )
    assert snapshot.flags == result.flags


def test_create_environment_snapshot_requires_date() -> None:
    config = MacroEnvironmentConfig(
        economy="USA",
        minimum_pillars=3,
    )

    results = (
        make_pillar_result("USA Growth"),
        make_pillar_result("USA Labor"),
        make_pillar_result("USA Inflation"),
    )

    result = build_environment_result(
        config=config,
        pillar_results=results,
    )

    with pytest.raises(ValueError, match="as_of_date"):
        create_environment_snapshot(result)

@pytest.mark.parametrize(
    ("score", "expected"),
    [
        (0.15, 0.0),
        (-0.15, 0.0),
        (0.50, 1.0),
        (-0.50, 1.0),
        (0.00, 1.0),
    ],
)
def test_calculate_dimension_margin(
    score: float,
    expected: float,
) -> None:
    assert calculate_dimension_margin(score) == expected


def test_activity_score_near_boundary_has_low_margin() -> None:
    margin = calculate_dimension_margin(0.1729)

    assert 0.06 <= margin <= 0.07


def test_calculate_dimension_margins_returns_all_dimensions() -> None:
    margins = calculate_dimension_margins(
        activity_score=0.1729,
        inflation_impulse_score=0.4877,
        financial_impulse_score=0.0534,
    )

    assert set(margins) == {
        "activity",
        "inflation",
        "financial",
    }

    assert margins["activity"] < 0.10
    assert margins["inflation"] > 0.90
    assert margins["financial"] > 0.60


def test_calculate_environment_conviction_uses_confidence_and_margins() -> None:
    conviction = calculate_environment_conviction(
        confidence_score=0.90,
        dimension_margins={
            "activity": 0.10,
            "inflation": 0.90,
            "financial": 0.60,
        },
    )

    assert 0.35 <= conviction <= 0.45
    assert (
        classify_environment_conviction(conviction)
        == "Moderate"
    )


@pytest.mark.parametrize(
    ("score", "expected"),
    [
        (0.80, "High"),
        (0.50, "Moderate"),
        (0.20, "Low"),
    ],
)
def test_classify_environment_conviction(
    score: float,
    expected: str,
) -> None:
    assert classify_environment_conviction(score) == expected


def test_detect_dimension_boundary_flags() -> None:
    flags = detect_dimension_boundary_flags(
        {
            "activity": 0.08,
            "inflation": 0.95,
            "financial": 0.50,
        }
    )

    assert flags == ("activity_near_boundary",)


def test_build_environment_result_populates_conviction() -> None:
    config = MacroEnvironmentConfig(
        economy="USA",
        minimum_pillars=5,
    )

    results = (
        make_pillar_result(
            "USA Growth",
            trend_score=0.25,
        ),
        make_pillar_result(
            "USA Inflation",
            trend_score=0.48,
        ),
        make_pillar_result(
            "USA Labor",
            trend_score=0.04,
        ),
        make_pillar_result(
            "USA Liquidity",
            trend_score=-0.07,
        ),
        make_pillar_result(
            "USA Policy",
            trend_score=0.24,
        ),
    )

    result = build_environment_result(
        config=config,
        pillar_results=results,
    )

    assert set(result.dimension_margins) == {
        "activity",
        "inflation",
        "financial",
    }

    assert 0.0 <= result.environment_conviction_score <= 1.0
    assert result.environment_conviction_label in {
        "Low",
        "Moderate",
        "High",
    }

    assert "activity_near_boundary" in result.flags

def make_pillar_result(
    name: str,
    *,
    economy: str = "USA",
    state_score: float = 0.25,
    trend_score: float = 0.25,
    breadth_score: float = 0.70,
    confidence_score: float = 0.80,
) -> PillarResult:
    pillar_key = name.lower().replace(" ", "_")

    return PillarResult(
        pillar_id=f"usa_{pillar_key}",
        name=name,
        economy=economy,
        state_score=state_score,
        state_label="Moderate",
        trend_score=trend_score,
        trend_label="Improving",
        breadth_score=breadth_score,
        breadth_label="Broad",
        confidence_score=confidence_score,
        confidence_label="High",
        buckets_used=0,
        bucket_results=(),
        key_drivers=(),
        flags=(),
        diagnostics={},
    )


def test_validate_environment_inputs_accepts_valid_results() -> None:
    config = MacroEnvironmentConfig(
        economy="USA",
        minimum_pillars=3,
    )

    results = (
        make_pillar_result("Growth"),
        make_pillar_result("Inflation"),
        make_pillar_result("Labor"),
    )

    validated = validate_environment_inputs(config, results)

    assert validated == results


def test_validate_environment_inputs_rejects_too_few_pillars() -> None:
    config = MacroEnvironmentConfig(
        economy="USA",
        minimum_pillars=3,
    )

    with pytest.raises(ValueError, match="at least 3"):
        validate_environment_inputs(
            config,
            (
                make_pillar_result("Growth"),
                make_pillar_result("Labor"),
            ),
        )


def test_validate_environment_inputs_rejects_mixed_economies() -> None:
    config = MacroEnvironmentConfig(
        economy="USA",
        minimum_pillars=2,
    )

    with pytest.raises(ValueError, match="configured economy"):
        validate_environment_inputs(
            config,
            (
                make_pillar_result("Growth"),
                make_pillar_result("Labor", economy="UK"),
            ),
        )


def test_validate_environment_inputs_rejects_duplicate_names() -> None:
    config = MacroEnvironmentConfig(
        economy="USA",
        minimum_pillars=2,
    )

    with pytest.raises(ValueError, match="unique"):
        validate_environment_inputs(
            config,
            (
                make_pillar_result("Growth"),
                make_pillar_result("Growth"),
            ),
        )


def test_calculate_environment_confidence_uses_pillar_confidence() -> None:
    results = (
        make_pillar_result("Growth", confidence_score=0.90),
        make_pillar_result("Labor", confidence_score=0.80),
        make_pillar_result("Inflation", confidence_score=0.70),
    )

    score = calculate_environment_confidence(results)

    assert 0.70 <= score <= 0.80


@pytest.mark.parametrize(
    ("score", "expected"),
    [
        (0.85, "High"),
        (0.70, "Moderate"),
        (0.50, "Low"),
        (0.20, "Very Low"),
    ],
)
def test_classify_environment_confidence(
    score: float,
    expected: str,
) -> None:
    assert classify_environment_confidence(score) == expected


def test_overall_direction_is_broadly_improving() -> None:
    results = (
        make_pillar_result("Growth", trend_score=0.70),
        make_pillar_result("Labor", trend_score=0.60),
        make_pillar_result("Liquidity", trend_score=0.50),
    )

    assert calculate_overall_direction(results) == "Broadly Improving"


def test_overall_direction_is_mixed() -> None:
    results = (
        make_pillar_result("Growth", trend_score=0.60),
        make_pillar_result("Liquidity", trend_score=0.50),
        make_pillar_result("Labor", trend_score=-0.50),
        make_pillar_result("Inflation", trend_score=-0.60),
    )

    assert calculate_overall_direction(results) == "Mixed"


def test_detect_confirmations_finds_growth_labor_confirmation() -> None:
    pillar_map = {
        "growth": make_pillar_result("Growth", trend_score=0.50),
        "labor": make_pillar_result("Labor", trend_score=0.40),
    }

    signals = detect_confirmations(pillar_map)

    assert any(
        signal.code == "growth_labor_improving"
        for signal in signals
    )


def test_detect_tensions_finds_growth_labor_divergence() -> None:
    pillar_map = {
        "growth": make_pillar_result("Growth", trend_score=0.50),
        "labor": make_pillar_result("Labor", trend_score=-0.40),
    }

    signals = detect_tensions(pillar_map)

    assert any(
        signal.code == "growth_labor_divergence"
        for signal in signals
    )


def test_build_environment_result_returns_complete_result() -> None:
    config = MacroEnvironmentConfig(
        economy="USA",
        minimum_pillars=3,
        minimum_confidence=0.60,
    )

    results = (
        make_pillar_result("Growth", trend_score=0.50),
        make_pillar_result("Labor", trend_score=0.40),
        make_pillar_result("Liquidity", trend_score=0.30),
    )

    result = build_environment_result(
        config=config,
        pillar_results=results,
        as_of_date=date(2026, 7, 20),
    )

    assert result.economy == "USA"
    assert result.as_of_date == date(2026, 7, 20)
    assert result.overall_direction == "Improving"
    assert result.confidence_label == "High"
    assert len(result.pillar_results) == 3
    assert "Growth" in result.pillar_map
    assert result.confirmations
    assert result.key_drivers
    assert result.diagnostics["pillar_count"] == 3


def test_build_environment_result_flags_low_confidence() -> None:
    config = MacroEnvironmentConfig(
        economy="USA",
        minimum_pillars=3,
        minimum_confidence=0.60,
    )

    results = (
        make_pillar_result("Growth", confidence_score=0.30),
        make_pillar_result("Labor", confidence_score=0.30),
        make_pillar_result("Inflation", confidence_score=0.30),
    )

    result = build_environment_result(
        config=config,
        pillar_results=results,
    )

    assert "low_environment_confidence" in result.flags
    
def test_build_environment_result_recognises_economy_prefixed_names() -> None:
    config = MacroEnvironmentConfig(
        economy="USA",
        minimum_pillars=3,
    )

    results = (
        make_pillar_result("USA Growth", trend_score=0.50),
        make_pillar_result("USA Labor", trend_score=0.40),
        make_pillar_result("USA Liquidity", trend_score=0.30),
    )

    result = build_environment_result(
        config=config,
        pillar_results=results,
    )

    confirmation_codes = {
        signal.code for signal in result.confirmations
    }

    assert "growth_labor_improving" in confirmation_codes
    assert "growth_liquidity_supportive" in confirmation_codes
    
def test_calculate_activity_impulse_combines_growth_and_labor() -> None:
    pillar_map = {
        "growth": make_pillar_result(
            "Growth",
            trend_score=0.50,
        ),
        "labor": make_pillar_result(
            "Labor",
            trend_score=0.10,
        ),
    }

    score = calculate_activity_impulse(pillar_map)

    assert 0.30 <= score <= 0.40
    assert classify_activity_impulse(score) == "Expanding"


def test_calculate_inflation_impulse_preserves_pressure_direction() -> None:
    pillar_map = {
        "inflation": make_pillar_result(
            "Inflation",
            trend_score=0.55,
        ),
    }

    score = calculate_inflation_impulse(pillar_map)

    assert score == 0.55
    assert classify_inflation_impulse(score) == "Strongly Accelerating"


def test_calculate_financial_impulse_combines_liquidity_and_policy() -> None:
    pillar_map = {
        "liquidity": make_pillar_result(
            "Liquidity",
            trend_score=-0.10,
        ),
        "policy": make_pillar_result(
            "Policy",
            trend_score=0.40,
        ),
    }

    score = calculate_financial_impulse(pillar_map)

    assert 0.05 <= score <= 0.15
    assert classify_financial_impulse(score) == "Neutral"


@pytest.mark.parametrize(
    (
        "activity",
        "inflation",
        "financial",
        "expected",
    ),
    [
        (
            0.40,
            -0.40,
            0.30,
            "Goldilocks Expansion",
        ),
        (
            0.40,
            0.40,
            0.30,
            "Reflationary Expansion",
        ),
        (
            0.40,
            0.40,
            0.00,
            "Reflationary Transition",
        ),
        (
            -0.40,
            0.40,
            -0.30,
            "Stagflationary Slowdown",
        ),
        (
            -0.40,
            -0.40,
            0.30,
            "Policy-Response Slowdown",
        ),
        (
            0.00,
            0.00,
            0.00,
            "Mixed / Transitional",
        ),
    ],
)
def test_classify_macro_environment(
    activity: float,
    inflation: float,
    financial: float,
    expected: str,
) -> None:
    assert (
        classify_macro_environment(
            activity_score=activity,
            inflation_impulse_score=inflation,
            financial_impulse_score=financial,
        )
        == expected
    )


def test_build_environment_summary_describes_each_dimension() -> None:
    summary = build_environment_summary(
        activity_label="Expanding",
        inflation_impulse_label="Accelerating",
        financial_impulse_label="Neutral",
        environment_label="Reflationary Transition",
    )

    normalized_summary = summary.lower()

    assert "reflationary transition" in normalized_summary
    assert "activity is expanding" in normalized_summary
    assert "inflation pressure is accelerating" in normalized_summary
    assert "financial impulse is neutral" in normalized_summary

def test_build_environment_result_populates_macro_dimensions() -> None:
    config = MacroEnvironmentConfig(
        economy="USA",
        minimum_pillars=5,
    )

    results = (
        make_pillar_result(
            "USA Growth",
            trend_score=0.40,
        ),
        make_pillar_result(
            "USA Inflation",
            trend_score=0.50,
        ),
        make_pillar_result(
            "USA Labor",
            trend_score=0.20,
        ),
        make_pillar_result(
            "USA Liquidity",
            trend_score=0.00,
        ),
        make_pillar_result(
            "USA Policy",
            trend_score=0.20,
        ),
    )

    result = build_environment_result(
        config=config,
        pillar_results=results,
    )

    assert result.activity_score > 0.15
    assert result.activity_label == "Expanding"

    assert result.inflation_impulse_score == 0.50
    assert (
        result.inflation_impulse_label
        == "Strongly Accelerating"
    )

    assert result.financial_impulse_label == "Neutral"
    assert result.environment_label == "Reflationary Transition"
    assert result.environment_summary