"""Tests for the reusable MacroLens Bucket Engine."""

from dataclasses import replace
from datetime import date

import pytest

from macro_engine.engine.bucket_engine import (
    calculate_bucket_breadth_score,
    calculate_bucket_confidence_score,
    calculate_bucket_state_score,
    calculate_bucket_trend_score,
    classify_bucket_breadth,
    classify_bucket_confidence,
    classify_bucket_state,
    classify_bucket_trend,
    identify_key_drivers,
    prepare_bucket_results,
    run_bucket,
)
from macro_engine.metadata.buckets import USA_HOUSEHOLD_DEMAND
from macro_engine.models.indicator import IndicatorResult


def make_indicator_result(
    indicator_id: str,
    name: str,
    state_score: float,
    trend_score: float,
    confidence_score: float = 0.90,
    economy: str = "USA",
    pillar: str = "growth",
) -> IndicatorResult:
    """Create a valid IndicatorResult for bucket-engine tests."""
    return IndicatorResult(
        indicator_id=indicator_id,
        name=name,
        economy=economy,
        pillar=pillar,
        bucket="household_demand",
        latest_value=1.0,
        latest_date=date(2026, 6, 1),
        state_value=1.0,
        state_score=state_score,
        state_label="Normal",
        trend_value=0.1,
        trend_score=trend_score,
        trend_label="Stable",
        historical_percentile=50.0,
        confidence_score=confidence_score,
        confidence_label="Very High",
        observations_used=100,
        flags=(),
        diagnostics={},
    )


@pytest.fixture
def household_results() -> tuple[IndicatorResult, ...]:
    return (
        make_indicator_result(
            "usa_real_personal_consumption",
            "Real Personal Consumption",
            0.067,
            0.40,
        ),
        make_indicator_result(
            "usa_retail_sales",
            "Retail Sales",
            0.513,
            -0.20,
        ),
        make_indicator_result(
            "usa_personal_income",
            "Personal Income",
            0.134,
            0.65,
        ),
    )


def test_prepare_bucket_results_accepts_valid_results(
    household_results,
) -> None:
    prepared = prepare_bucket_results(
        household_results,
        USA_HOUSEHOLD_DEMAND,
    )

    assert len(prepared) == 3


def test_prepare_bucket_results_rejects_insufficient_results(
    household_results,
) -> None:
    with pytest.raises(ValueError):
        prepare_bucket_results(
            household_results[:1],
            USA_HOUSEHOLD_DEMAND,
        )


def test_prepare_bucket_results_filters_wrong_economy(
    household_results,
) -> None:
    wrong_economy = replace(
        household_results[0],
        economy="UK",
    )

    prepared = prepare_bucket_results(
        (wrong_economy, *household_results[1:]),
        USA_HOUSEHOLD_DEMAND,
    )

    assert len(prepared) == 2
    assert all(result.economy == "USA" for result in prepared)


def test_calculate_bucket_state_score(
    household_results,
) -> None:
    score = calculate_bucket_state_score(
        household_results,
        USA_HOUSEHOLD_DEMAND,
    )

    expected = (
        (0.067 * 0.45)
        + (0.513 * 0.30)
        + (0.134 * 0.25)
    )

    assert score == pytest.approx(expected)


def test_calculate_bucket_trend_score(
    household_results,
) -> None:
    score = calculate_bucket_trend_score(
        household_results,
        USA_HOUSEHOLD_DEMAND,
    )

    expected = (
        (0.40 * 0.45)
        + (-0.20 * 0.30)
        + (0.65 * 0.25)
    )

    assert score == pytest.approx(expected)


def test_calculate_bucket_breadth_score(
    household_results,
) -> None:
    score = calculate_bucket_breadth_score(
        household_results,
        USA_HOUSEHOLD_DEMAND,
    )

    assert score == pytest.approx(2 / 3)


def test_calculate_bucket_confidence_score(
    household_results,
) -> None:
    score = calculate_bucket_confidence_score(
        household_results,
        USA_HOUSEHOLD_DEMAND,
    )

    assert score == pytest.approx(0.90)


@pytest.mark.parametrize(
    ("score", "expected"),
    [
        (0.70, "Very Strong"),
        (0.20, "Strong"),
        (0.00, "Normal"),
        (-0.20, "Weak"),
        (-0.70, "Very Weak"),
    ],
)
def test_classify_bucket_state(
    score: float,
    expected: str,
) -> None:
    assert classify_bucket_state(score) == expected


@pytest.mark.parametrize(
    ("score", "expected"),
    [
        (0.20, "Improving"),
        (0.00, "Stable"),
        (-0.20, "Deteriorating"),
    ],
)
def test_classify_bucket_trend(
    score: float,
    expected: str,
) -> None:
    assert classify_bucket_trend(score) == expected


@pytest.mark.parametrize(
    ("score", "expected"),
    [
        (1.00, "Broadly Positive"),
        (0.50, "Mostly Positive"),
        (0.00, "Mixed"),
        (-0.50, "Mostly Negative"),
        (-1.00, "Broadly Negative"),
    ],
)
def test_classify_bucket_breadth(
    score: float,
    expected: str,
) -> None:
    assert classify_bucket_breadth(score) == expected


@pytest.mark.parametrize(
    ("score", "expected"),
    [
        (0.90, "Very High"),
        (0.75, "High"),
        (0.60, "Moderate"),
        (0.40, "Low"),
        (0.20, "Very Low"),
    ],
)
def test_classify_bucket_confidence(
    score: float,
    expected: str,
) -> None:
    assert classify_bucket_confidence(score) == expected


def test_identify_key_drivers_orders_by_contribution(
    household_results,
) -> None:
    drivers = identify_key_drivers(
        household_results,
        USA_HOUSEHOLD_DEMAND,
    )

    assert drivers[0].startswith("Retail Sales")
    assert drivers[1].startswith("Personal Income")
    assert drivers[2].startswith("Real Personal Consumption")


def test_run_bucket_returns_complete_result(
    household_results,
) -> None:
    result = run_bucket(
        household_results,
        USA_HOUSEHOLD_DEMAND,
    )

    assert result.bucket_id == "usa_household_demand"
    assert result.name == "Household Demand"
    assert result.state_label == "Strong"
    assert result.trend_label == "Improving"
    assert result.breadth_label == "Mostly Positive"
    assert result.confidence_label == "Very High"
    assert result.indicators_used == 3
    assert result.is_valid
    assert result.flags == ()