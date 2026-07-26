"""Tests for the Euro Area Liquidity pillar."""

import math

from macro_engine.models.pillar import PillarResult
from macro_engine.pipelines.pillars import run_euro_liquidity


def test_euro_liquidity_returns_pillar_result():
    result = run_euro_liquidity()

    assert isinstance(result, PillarResult)


def test_euro_liquidity_identity():
    result = run_euro_liquidity()

    assert result.pillar_id == "euro_liquidity"
    assert result.name == "Euro Area Liquidity"
    assert result.economy == "Euro Area"


def test_euro_liquidity_uses_expected_buckets():
    result = run_euro_liquidity()

    bucket_ids = {
        bucket.bucket_id
        for bucket in result.bucket_results
    }

    assert bucket_ids == {
        "euro_central_bank_liquidity",
        "euro_money_conditions",
    }


def test_euro_liquidity_uses_expected_indicators():
    result = run_euro_liquidity()

    indicator_ids = {
        indicator.indicator_id
        for bucket in result.bucket_results
        for indicator in bucket.indicator_results
    }

    assert indicator_ids == {
        "euro_ecb_balance_sheet_13w_change",
        "euro_m3_yoy",
    }


def test_euro_liquidity_scores_are_finite_and_bounded():
    result = run_euro_liquidity()

    assert math.isfinite(result.state_score)
    assert math.isfinite(result.trend_score)
    assert math.isfinite(result.breadth_score)
    assert math.isfinite(result.confidence_score)

    assert -1.0 <= result.state_score <= 1.0
    assert -1.0 <= result.trend_score <= 1.0
    assert -1.0 <= result.breadth_score <= 1.0
    assert 0.0 <= result.confidence_score <= 1.0


def test_euro_liquidity_has_no_missing_components():
    result = run_euro_liquidity()

    assert result.diagnostics["missing_bucket_ids"] == []

    for bucket in result.bucket_results:
        assert bucket.diagnostics["missing_indicator_ids"] == []


def test_euro_liquidity_weights_are_correct():
    result = run_euro_liquidity()

    assert result.diagnostics["weights_used"] == {
        "euro_central_bank_liquidity": 0.55,
        "euro_money_conditions": 0.45,
    }