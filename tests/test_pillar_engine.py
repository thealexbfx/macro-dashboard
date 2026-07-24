"""Tests for the MacroLens Pillar Engine."""

import pytest

from macro_engine.engine.pillar_engine import (
    calculate_pillar_breadth_score,
    calculate_pillar_confidence_score,
    calculate_pillar_state_score,
    calculate_pillar_trend_score,
    classify_pillar_breadth,
    classify_pillar_confidence,
    classify_pillar_state,
    classify_pillar_trend,
    identify_pillar_key_drivers,
    prepare_pillar_results,
    run_pillar,
)
from macro_engine.models.bucket import BucketResult
from macro_engine.models.pillar import PillarConfig


def make_bucket_result(
    *,
    bucket_id: str,
    name: str,
    state_score: float,
    trend_score: float,
    confidence_score: float = 0.80,
    economy: str = "USA",
    pillar: str = "growth",
) -> BucketResult:
    return BucketResult(
        bucket_id=bucket_id,
        name=name,
        economy=economy,
        pillar=pillar,
        state_score=state_score,
        state_label="Normal",
        trend_score=trend_score,
        trend_label="Stable",
        breadth_score=0.0,
        breadth_label="Mixed",
        confidence_score=confidence_score,
        confidence_label="High",
        indicators_used=3,
        indicator_results=(),
    )


@pytest.fixture
def growth_config() -> PillarConfig:
    return PillarConfig(
        pillar_id="usa_growth",
        pillar="growth",
        name="USA Growth",
        economy="USA",
        minimum_buckets=3,
        bucket_weights={
            "usa_household_demand": 0.35,
            "usa_employment_momentum": 0.30,
            "usa_industrial_activity": 0.20,
            "usa_housing": 0.15,
        },
    )


@pytest.fixture
def growth_results() -> tuple[BucketResult, ...]:
    return (
        make_bucket_result(
            bucket_id="usa_household_demand",
            name="Household Demand",
            state_score=0.60,
            trend_score=0.30,
            confidence_score=0.90,
        ),
        make_bucket_result(
            bucket_id="usa_employment_momentum",
            name="Employment Momentum",
            state_score=0.40,
            trend_score=0.20,
            confidence_score=0.85,
        ),
        make_bucket_result(
            bucket_id="usa_industrial_activity",
            name="Industrial Activity",
            state_score=-0.20,
            trend_score=-0.30,
            confidence_score=0.75,
        ),
        make_bucket_result(
            bucket_id="usa_housing",
            name="Housing",
            state_score=-0.40,
            trend_score=0.10,
            confidence_score=0.70,
        ),
    )


def test_prepare_pillar_results_filters_invalid_matches(
    growth_config,
    growth_results,
):
    wrong_economy = make_bucket_result(
        bucket_id="uk_housing",
        name="UK Housing",
        state_score=0.20,
        trend_score=0.10,
        economy="UK",
    )

    prepared = prepare_pillar_results(
        (*growth_results, wrong_economy),
        growth_config,
    )

    assert len(prepared) == 4
    assert all(result.economy == "USA" for result in prepared)


def test_prepare_pillar_results_requires_minimum_buckets(
    growth_config,
    growth_results,
):
    with pytest.raises(
        ValueError,
        match="requires at least 3 valid buckets",
    ):
        prepare_pillar_results(
            growth_results[:2],
            growth_config,
        )


def test_calculate_pillar_state_score(
    growth_config,
    growth_results,
):
    score = calculate_pillar_state_score(
        growth_results,
        growth_config,
    )

    assert score == pytest.approx(0.23)


def test_calculate_pillar_trend_score(
    growth_config,
    growth_results,
):
    score = calculate_pillar_trend_score(
        growth_results,
        growth_config,
    )

    assert score == pytest.approx(0.12)


def test_calculate_pillar_breadth_score(
    growth_config,
    growth_results,
):
    score = calculate_pillar_breadth_score(
        growth_results,
        growth_config,
    )

    assert score == pytest.approx(0.0)


def test_calculate_pillar_confidence_score(
    growth_config,
    growth_results,
):
    score = calculate_pillar_confidence_score(
        growth_results,
        growth_config,
    )

    assert score == pytest.approx(0.825)


@pytest.mark.parametrize(
    ("score", "label"),
    [
        (0.70, "Very Strong"),
        (0.30, "Strong"),
        (0.00, "Normal"),
        (-0.30, "Weak"),
        (-0.70, "Very Weak"),
    ],
)
def test_classify_pillar_state(score, label):
    assert classify_pillar_state(score) == label


@pytest.mark.parametrize(
    ("score", "label"),
    [
        (0.30, "Improving"),
        (0.00, "Stable"),
        (-0.30, "Deteriorating"),
    ],
)
def test_classify_pillar_trend(score, label):
    assert classify_pillar_trend(score) == label


@pytest.mark.parametrize(
    ("score", "label"),
    [
        (1.00, "Broadly Positive"),
        (0.50, "Mostly Positive"),
        (0.00, "Mixed"),
        (-0.50, "Mostly Negative"),
        (-1.00, "Broadly Negative"),
    ],
)
def test_classify_pillar_breadth(score, label):
    assert classify_pillar_breadth(score) == label


@pytest.mark.parametrize(
    ("score", "label"),
    [
        (0.95, "Very High"),
        (0.80, "High"),
        (0.65, "Moderate"),
        (0.50, "Low"),
        (0.20, "Very Low"),
    ],
)
def test_classify_pillar_confidence(score, label):
    assert classify_pillar_confidence(score) == label


def test_identify_pillar_key_drivers(
    growth_config,
    growth_results,
):
    drivers = identify_pillar_key_drivers(
        growth_results,
        growth_config,
    )

    assert len(drivers) == 3
    assert drivers[0].startswith("Household Demand:")
    assert "positive contribution" in drivers[0]


def test_run_pillar_returns_complete_result(
    growth_config,
    growth_results,
):
    result = run_pillar(
        growth_results,
        growth_config,
    )

    assert result.pillar_id == "usa_growth"
    assert result.state_score == pytest.approx(0.23)
    assert result.state_label == "Strong"
    assert result.trend_score == pytest.approx(0.12)
    assert result.trend_label == "Stable"
    assert result.breadth_score == pytest.approx(0.0)
    assert result.breadth_label == "Mixed"
    assert result.confidence_score == pytest.approx(0.825)
    assert result.confidence_label == "High"
    assert result.buckets_used == 4
    assert result.is_valid is True
    assert "mixed_breadth" in result.flags