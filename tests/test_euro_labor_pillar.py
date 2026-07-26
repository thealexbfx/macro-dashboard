"""Tests for the Euro Area Labor pillar."""

import math

from macro_engine.models.pillar import PillarResult
from macro_engine.pipelines.pillars import run_euro_labor


def test_euro_labor_returns_pillar_result():
    result = run_euro_labor()

    assert isinstance(result, PillarResult)


def test_euro_labor_identity():
    result = run_euro_labor()

    assert result.pillar_id == "euro_labor"
    assert result.name == "Euro Area Labor"
    assert result.economy == "Euro Area"


def test_euro_labor_uses_employment_conditions_bucket():
    result = run_euro_labor()

    bucket_ids = {
        bucket.bucket_id
        for bucket in result.bucket_results
    }

    assert bucket_ids == {
        "euro_employment_conditions",
    }


def test_euro_labor_uses_two_indicators():
    result = run_euro_labor()

    bucket = result.bucket_results[0]

    indicator_ids = {
        indicator.indicator_id
        for indicator in bucket.indicator_results
    }

    assert indicator_ids == {
        "euro_total_employment_yoy",
        "euro_unemployment_rate",
    }


def test_euro_labor_scores_are_finite_and_bounded():
    result = run_euro_labor()

    assert math.isfinite(result.state_score)
    assert math.isfinite(result.trend_score)
    assert math.isfinite(result.breadth_score)
    assert math.isfinite(result.confidence_score)

    assert -1.0 <= result.state_score <= 1.0
    assert -1.0 <= result.trend_score <= 1.0
    assert 0.0 <= result.breadth_score <= 1.0
    assert 0.0 <= result.confidence_score <= 1.0


def test_euro_labor_has_no_missing_buckets_or_indicators():
    result = run_euro_labor()

    assert result.diagnostics["missing_bucket_ids"] == []

    bucket = result.bucket_results[0]

    assert bucket.diagnostics["missing_indicator_ids"] == []


def test_euro_labor_weights_are_correct():
    result = run_euro_labor()

    assert result.diagnostics["weights_used"] == {
        "euro_employment_conditions": 1.0,
    }

    bucket = result.bucket_results[0]

    assert bucket.diagnostics["weights_used"] == {
        "euro_total_employment_yoy": 0.5,
        "euro_unemployment_rate": 0.5,
    }