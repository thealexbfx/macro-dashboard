import math

from macro_engine.models.pillar import PillarResult
from macro_engine.pipelines.pillars import run_euro_inflation


def test_run_euro_inflation_returns_pillar_result():
    result = run_euro_inflation()

    assert isinstance(result, PillarResult)


def test_euro_inflation_identity():
    result = run_euro_inflation()

    assert result.pillar_id == "euro_inflation"
    assert result.name == "Euro Area Inflation"
    assert result.economy == "Euro Area"


def test_euro_inflation_uses_all_configured_buckets():
    result = run_euro_inflation()

    expected_bucket_ids = {
        "euro_core_inflation_persistence",
        "euro_headline_price_pressure",
        "euro_wage_cost_pressure",
        "euro_monetary_policy_pressure",
    }

    actual_bucket_ids = {
        bucket.bucket_id
        for bucket in result.bucket_results
    }

    assert result.buckets_used == 4
    assert len(result.bucket_results) == 4
    assert actual_bucket_ids == expected_bucket_ids


def test_euro_inflation_scores_are_valid():
    result = run_euro_inflation()

    scores = (
        result.state_score,
        result.trend_score,
        result.breadth_score,
        result.confidence_score,
    )

    assert all(math.isfinite(score) for score in scores)

    assert -1.0 <= result.state_score <= 1.0
    assert -1.0 <= result.trend_score <= 1.0
    assert -1.0 <= result.breadth_score <= 1.0
    assert 0.0 <= result.confidence_score <= 1.0


def test_euro_inflation_has_no_missing_buckets():
    result = run_euro_inflation()

    assert result.diagnostics["missing_bucket_ids"] == []
    assert result.diagnostics["configured_buckets"] == 4
    assert result.diagnostics["buckets_used"] == 4


def test_euro_inflation_weights_are_correct():
    result = run_euro_inflation()

    assert result.diagnostics["weights_used"] == {
        "euro_core_inflation_persistence": 0.30,
        "euro_headline_price_pressure": 0.25,
        "euro_wage_cost_pressure": 0.25,
        "euro_monetary_policy_pressure": 0.20,
    }

# Model-contract tests use synthetic source observations; live providers are tested separately.
import pytest
pytestmark = pytest.mark.usefixtures("synthetic_pipeline_data")
