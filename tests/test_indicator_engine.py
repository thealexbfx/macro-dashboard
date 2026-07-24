"""Tests for the MacroLens Indicator Engine."""

import pandas as pd
import pytest
from datetime import date
from macro_engine.metadata.usa_policy import USA_POLICY_RATE


from macro_engine.engine.indicator_engine import (
    calculate_confidence,
    calculate_historical_percentile,
    calculate_state_score,
    calculate_state_value,
    calculate_trend_score,
    calculate_trend_value,
    classify_state,
    classify_trend,
    prepare_indicator_data,
    run_indicator,
    calculate_trend_percentile,
    filter_indicator_data_as_of,
)
from macro_engine.metadata.growth import USA_REAL_PERSONAL_CONSUMPTION

def test_filter_indicator_data_as_of_limits_rows() -> None:
    data = pd.DataFrame(
        {
            "date": pd.to_datetime(
                [
                    "2026-01-31",
                    "2026-02-28",
                    "2026-03-31",
                ]
            ),
            "value": [1.0, 2.0, 3.0],
        }
    )

    filtered = filter_indicator_data_as_of(
        data,
        as_of_date=date(2026, 2, 28),
    )

    assert len(filtered) == 2
    assert filtered["value"].tolist() == [1.0, 2.0]


def test_filter_indicator_data_as_of_rejects_empty_history() -> None:
    data = pd.DataFrame(
        {
            "date": pd.to_datetime(
                [
                    "2026-01-31",
                    "2026-02-28",
                ]
            ),
            "value": [1.0, 2.0],
        }
    )

    with pytest.raises(
        ValueError,
        match="no indicator observations",
    ):
        filter_indicator_data_as_of(
            data,
            as_of_date=date(2025, 12, 31),
        )


def test_run_indicator_respects_as_of_date() -> None:
    data = pd.DataFrame(
        {
            "date": pd.date_range(
                "2020-01-31",
                periods=72,
                freq="ME",
            ),
            "value": range(72),
        }
    )

    result = run_indicator(
        data,
        USA_REAL_PERSONAL_CONSUMPTION,
        as_of_date=date(2024, 12, 31),
    )

    assert result.latest_date == date(2024, 12, 31)

def test_unchanged_trend_is_neutral() -> None:
    data = pd.DataFrame(
        {
            "date": pd.date_range(
                start="2024-01-01",
                periods=600,
                freq="D",
            ),
            "value": [5.0] * 600,
        }
    )

    percentile = calculate_trend_percentile(
        data,
        USA_POLICY_RATE,
    )

    score = calculate_trend_score(
        percentile,
        USA_POLICY_RATE,
    )

    assert percentile == 50.0
    assert score == 0.0
    assert classify_trend(score) == "Stable"

def make_monthly_data(values: list[float]) -> pd.DataFrame:
    """Create a clean monthly date/value test series."""
    return pd.DataFrame(
        {
            "date": pd.date_range(
                start="2020-01-31",
                periods=len(values),
                freq="ME",
            ),
            "value": values,
        }
    )


def test_prepare_indicator_data_cleans_and_sorts() -> None:
    data = pd.DataFrame(
        {
            "date": ["2024-03-31", "bad-date", "2024-01-31", "2024-01-31"],
            "value": ["0.3", "1.0", "0.1", "0.2"],
            "extra": ["a", "b", "c", "d"],
        }
    )

    cleaned = prepare_indicator_data(
        data,
        USA_REAL_PERSONAL_CONSUMPTION,
    )

    assert list(cleaned.columns) == ["date", "value"]
    assert len(cleaned) == 2
    assert cleaned.iloc[0]["value"] == pytest.approx(0.2)
    assert cleaned.iloc[1]["value"] == pytest.approx(0.3)


def test_prepare_indicator_data_rejects_missing_columns() -> None:
    data = pd.DataFrame({"date": ["2024-01-31"]})

    with pytest.raises(ValueError, match="missing required columns"):
        prepare_indicator_data(
            data,
            USA_REAL_PERSONAL_CONSUMPTION,
        )


def test_state_value_uses_latest_three_observations() -> None:
    data = make_monthly_data([0.1, 0.2, 0.3, 0.0, 0.3])

    result = calculate_state_value(
        data,
        USA_REAL_PERSONAL_CONSUMPTION,
    )

    assert result == pytest.approx(0.2)


def test_trend_value_compares_latest_and_previous_windows() -> None:
    data = make_monthly_data(
        [0.1, -0.2, 0.2, 0.3, 0.0, 0.3]
    )

    result = calculate_trend_value(
        data,
        USA_REAL_PERSONAL_CONSUMPTION,
    )

    assert result == pytest.approx(1 / 6)


@pytest.mark.parametrize(
    ("percentile", "expected_score", "expected_label"),
    [
        (90.0, 0.8, "Very Strong"),
        (70.0, 0.4, "Strong"),
        (50.0, 0.0, "Normal"),
        (30.0, -0.4, "Weak"),
        (10.0, -0.8, "Very Weak"),
    ],
)
def test_state_score_and_labels(
    percentile: float,
    expected_score: float,
    expected_label: str,
) -> None:
    score = calculate_state_score(
        percentile,
        USA_REAL_PERSONAL_CONSUMPTION,
    )

    assert score == pytest.approx(expected_score)
    assert classify_state(score) == expected_label


@pytest.mark.parametrize(
    ("percentile", "expected_score", "expected_label"),
    [
        (80.0, 0.6, "Improving"),
        (55.0, 0.1, "Stable"),
        (20.0, -0.6, "Deteriorating"),
    ],
)
def test_trend_score_and_labels(
    percentile: float,
    expected_score: float,
    expected_label: str,
) -> None:
    score = calculate_trend_score(
        percentile,
        USA_REAL_PERSONAL_CONSUMPTION,
    )

    assert score == pytest.approx(expected_score)
    assert classify_trend(score) == expected_label


def test_historical_percentile_is_bounded() -> None:
    values = [0.1] * 237 + [0.2, 0.2, 0.2]
    data = make_monthly_data(values)

    percentile = calculate_historical_percentile(
        data,
        USA_REAL_PERSONAL_CONSUMPTION,
    )

    assert 0.0 <= percentile <= 100.0


def test_confidence_is_capped_at_point_nine() -> None:
    data = make_monthly_data([0.2] * 240)

    confidence, flags, components = calculate_confidence(
        data,
        USA_REAL_PERSONAL_CONSUMPTION,
    )

    assert confidence <= 0.90
    assert "raw_confidence" in components
    assert isinstance(flags, tuple)


def test_run_indicator_returns_valid_result() -> None:
    values = [0.1] * 234 + [0.1, -0.2, 0.2, 0.3, 0.0, 0.3]
    data = make_monthly_data(values)

    result = run_indicator(
        data,
        USA_REAL_PERSONAL_CONSUMPTION,
    )

    assert result.indicator_id == "usa_real_personal_consumption"
    assert result.state_value == pytest.approx(0.2)
    assert result.trend_value == pytest.approx(1 / 6)
    assert result.state_label in {
        "Very Strong",
        "Strong",
        "Normal",
        "Weak",
        "Very Weak",
    }
    assert result.trend_label in {
        "Improving",
        "Stable",
        "Deteriorating",
    }
    assert result.is_valid