from datetime import date
from unittest.mock import patch

from macro_engine.models.environment import MacroEnvironmentResult
from macro_engine.models.pillar import PillarResult
from macro_engine.pipelines.environment import (
    USA_MACRO_ENVIRONMENT,
    run_usa_macro_environment,
)


def make_pillar_result(
    name: str,
    *,
    state_score: float = 0.25,
    trend_score: float = 0.25,
    breadth_score: float = 0.70,
    confidence_score: float = 0.80,
) -> PillarResult:
    pillar_key = name.lower().replace(" ", "_")

    return PillarResult(
        pillar_id=f"usa_{pillar_key}",
        name=name,
        economy="USA",
        state_score=state_score,
        state_label="Moderate",
        trend_score=trend_score,
        trend_label="Improving",
        breadth_score=breadth_score,
        breadth_label="Broad",
        confidence_score=confidence_score,
        confidence_label="High",
        buckets_used=1,
        bucket_results=(),
        key_drivers=(),
        flags=(),
        diagnostics={},
    )


def test_usa_environment_config_is_valid() -> None:
    assert USA_MACRO_ENVIRONMENT.economy == "USA"
    assert USA_MACRO_ENVIRONMENT.minimum_pillars == 5
    assert USA_MACRO_ENVIRONMENT.minimum_confidence == 0.60


@patch("macro_engine.pipelines.environment.run_usa_policy_pillar")
@patch("macro_engine.pipelines.environment.run_usa_liquidity_pillar")
@patch("macro_engine.pipelines.environment.run_usa_labor")
@patch("macro_engine.pipelines.environment.run_usa_inflation")
@patch("macro_engine.pipelines.environment.run_usa_growth")
def test_run_usa_macro_environment_runs_all_pillars(
    mock_growth,
    mock_inflation,
    mock_labor,
    mock_liquidity,
    mock_policy,
) -> None:
    mock_growth.return_value = make_pillar_result(
        "Growth",
        trend_score=0.50,
    )
    mock_inflation.return_value = make_pillar_result(
        "Inflation",
        trend_score=-0.30,
    )
    mock_labor.return_value = make_pillar_result(
        "Labor",
        trend_score=0.40,
    )
    mock_liquidity.return_value = make_pillar_result(
        "Liquidity",
        trend_score=0.30,
    )
    mock_policy.return_value = make_pillar_result(
        "Policy",
        trend_score=0.10,
    )

    result = run_usa_macro_environment(
        as_of_date=date(2026, 7, 20),
    )

    assert isinstance(result, MacroEnvironmentResult)
    assert result.economy == "USA"
    assert result.as_of_date == date(2026, 7, 20)

    assert len(result.pillar_results) == 5
    assert set(result.pillar_map) == {
        "Growth",
        "Inflation",
        "Labor",
        "Liquidity",
        "Policy",
    }

    expected_date = date(2026, 7, 20)

    mock_growth.assert_called_once_with(
        as_of_date=expected_date,
    )
    mock_inflation.assert_called_once_with(
        as_of_date=expected_date,
    )
    mock_labor.assert_called_once_with(
        as_of_date=expected_date,
    )
    mock_liquidity.assert_called_once_with(
        as_of_date=expected_date,
    )
    mock_policy.assert_called_once_with(
        as_of_date=expected_date,
    )


@patch("macro_engine.pipelines.environment.run_usa_policy_pillar")
@patch("macro_engine.pipelines.environment.run_usa_liquidity_pillar")
@patch("macro_engine.pipelines.environment.run_usa_labor")
@patch("macro_engine.pipelines.environment.run_usa_inflation")
@patch("macro_engine.pipelines.environment.run_usa_growth")
def test_usa_environment_detects_confirmations_and_tensions(
    mock_growth,
    mock_inflation,
    mock_labor,
    mock_liquidity,
    mock_policy,
) -> None:
    mock_growth.return_value = make_pillar_result(
        "Growth",
        trend_score=0.50,
    )
    mock_inflation.return_value = make_pillar_result(
        "Inflation",
        trend_score=-0.40,
        breadth_score=0.70,
    )
    mock_labor.return_value = make_pillar_result(
        "Labor",
        trend_score=0.40,
    )
    mock_liquidity.return_value = make_pillar_result(
        "Liquidity",
        trend_score=0.30,
    )
    mock_policy.return_value = make_pillar_result(
        "Policy",
        state_score=0.50,
        trend_score=0.00,
    )

    result = run_usa_macro_environment()

    confirmation_codes = {
        signal.code for signal in result.confirmations
    }
    tension_codes = {
        signal.code for signal in result.tensions
    }

    assert "growth_labor_improving" in confirmation_codes
    assert "growth_liquidity_supportive" in confirmation_codes
    assert "broad_disinflation" in confirmation_codes

    assert (
        "easing_inflation_restrictive_policy"
        in tension_codes
    )


@patch("macro_engine.pipelines.environment.run_usa_policy_pillar")
@patch("macro_engine.pipelines.environment.run_usa_liquidity_pillar")
@patch("macro_engine.pipelines.environment.run_usa_labor")
@patch("macro_engine.pipelines.environment.run_usa_inflation")
@patch("macro_engine.pipelines.environment.run_usa_growth")
def test_usa_environment_preserves_low_confidence_flag(
    mock_growth,
    mock_inflation,
    mock_labor,
    mock_liquidity,
    mock_policy,
) -> None:
    low_confidence_result = make_pillar_result(
        "Growth",
        confidence_score=0.30,
    )

    mock_growth.return_value = low_confidence_result
    mock_inflation.return_value = make_pillar_result(
        "Inflation",
        confidence_score=0.30,
    )
    mock_labor.return_value = make_pillar_result(
        "Labor",
        confidence_score=0.30,
    )
    mock_liquidity.return_value = make_pillar_result(
        "Liquidity",
        confidence_score=0.30,
    )
    mock_policy.return_value = make_pillar_result(
        "Policy",
        confidence_score=0.30,
    )

    result = run_usa_macro_environment()

    assert result.confidence_score == 0.30
    assert result.confidence_label == "Very Low"
    assert "low_environment_confidence" in result.flags