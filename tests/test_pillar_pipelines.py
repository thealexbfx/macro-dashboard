import pytest

from macro_engine.models.bucket import BucketResult
from macro_engine.models.pillar import PillarResult


from macro_engine.pipelines.pillars import (
    run_euro_growth,
    run_usa_growth,
    run_uk_growth,
    run_japan_growth,
)


def dummy_bucket(name):
    return BucketResult(
        bucket_id=name,
        name=name,
        economy="USA",
        pillar="growth",
        state_score=0.2,
        state_label="Strong",
        trend_score=0.1,
        trend_label="Stable",
        breadth_score=0.5,
        breadth_label="Mostly Positive",
        confidence_score=0.8,
        confidence_label="High",
        indicators_used=5,
        indicator_results=(),
    )

def dummy_euro_bucket(bucket_id):
    return BucketResult(
        bucket_id=bucket_id,
        name=bucket_id,
        economy="Euro Area",
        pillar="growth",
        state_score=0.2,
        state_label="Strong",
        trend_score=0.1,
        trend_label="Stable",
        breadth_score=0.5,
        breadth_label="Mostly Positive",
        confidence_score=0.8,
        confidence_label="High",
        indicators_used=1,
        indicator_results=(),
    )

def test_run_usa_growth_returns_valid_pillar(monkeypatch):

    monkeypatch.setattr(
        "macro_engine.pipelines.pillars.run_usa_household_demand",
        lambda as_of_date=None: dummy_bucket("household"),
    )

    monkeypatch.setattr(
        "macro_engine.pipelines.pillars.run_usa_employment_momentum",
        lambda as_of_date=None: dummy_bucket("employment"),
    )

    monkeypatch.setattr(
        "macro_engine.pipelines.pillars.run_usa_industrial_activity",
        lambda as_of_date=None: dummy_bucket("industry")
    )

    monkeypatch.setattr(
        "macro_engine.pipelines.pillars.run_usa_housing",
        lambda as_of_date=None: dummy_bucket("housing")
    )

    result = run_usa_growth()

    assert isinstance(result, PillarResult)

    assert result.is_valid
    
def test_growth_pipeline_calls_each_bucket_once(monkeypatch):

    calls = {
        "household": 0,
        "employment": 0,
        "industry": 0,
        "housing": 0,
    }

    def household(as_of_date=None):
        calls["household"] += 1
        return dummy_bucket("household")

    def employment(as_of_date=None):
        calls["employment"] += 1
        return dummy_bucket("employment")

    def industry(as_of_date=None):
        calls["industry"] += 1
        return dummy_bucket("industry")

    def housing(as_of_date=None):
        calls["housing"] += 1
        return dummy_bucket("housing")

    monkeypatch.setattr(
        "macro_engine.pipelines.pillars.run_usa_household_demand",
        household,
    )

    monkeypatch.setattr(
        "macro_engine.pipelines.pillars.run_usa_employment_momentum",
        employment,
    )

    monkeypatch.setattr(
        "macro_engine.pipelines.pillars.run_usa_industrial_activity",
        industry,
    )

    monkeypatch.setattr(
        "macro_engine.pipelines.pillars.run_usa_housing",
        housing,
    )

    run_usa_growth()

    assert calls == {
        "household": 1,
        "employment": 1,
        "industry": 1,
        "housing": 1,
    }
    
def test_run_euro_growth_returns_valid_pillar(monkeypatch):

    monkeypatch.setattr(
        "macro_engine.pipelines.pillars.run_euro_economic_activity",
        lambda as_of_date=None: dummy_euro_bucket(
            "euro_economic_activity"
        ),
    )

    monkeypatch.setattr(
        "macro_engine.pipelines.pillars.run_euro_household_demand",
        lambda as_of_date=None: dummy_euro_bucket(
            "euro_household_demand"
        ),
    )

    monkeypatch.setattr(
        "macro_engine.pipelines.pillars.run_euro_industrial_activity",
        lambda as_of_date=None: dummy_euro_bucket(
            "euro_industrial_activity"
        ),
    )

    monkeypatch.setattr(
        "macro_engine.pipelines.pillars.run_euro_forward_looking",
        lambda as_of_date=None: dummy_euro_bucket(
            "euro_forward_looking"
        ),
    )

    result = run_euro_growth()

    assert isinstance(result, PillarResult)
    assert result.is_valid
    assert result.pillar_id == "euro_growth"
    assert result.economy == "Euro Area"


def test_euro_growth_pipeline_calls_each_bucket_once(monkeypatch):

    calls = {
        "economic_activity": 0,
        "household_demand": 0,
        "industrial_activity": 0,
        "forward_looking": 0,
    }

    def economic_activity(as_of_date=None):
        calls["economic_activity"] += 1
        return dummy_euro_bucket("euro_economic_activity")

    def household_demand(as_of_date=None):
        calls["household_demand"] += 1
        return dummy_euro_bucket("euro_household_demand")

    def industrial_activity(as_of_date=None):
        calls["industrial_activity"] += 1
        return dummy_euro_bucket("euro_industrial_activity")

    def forward_looking(as_of_date=None):
        calls["forward_looking"] += 1
        return dummy_euro_bucket("euro_forward_looking")

    monkeypatch.setattr(
        "macro_engine.pipelines.pillars.run_euro_economic_activity",
        economic_activity,
    )

    monkeypatch.setattr(
        "macro_engine.pipelines.pillars.run_euro_household_demand",
        household_demand,
    )

    monkeypatch.setattr(
        "macro_engine.pipelines.pillars.run_euro_industrial_activity",
        industrial_activity,
    )

    monkeypatch.setattr(
        "macro_engine.pipelines.pillars.run_euro_forward_looking",
        forward_looking,
    )

    run_euro_growth()

    assert calls == {
        "economic_activity": 1,
        "household_demand": 1,
        "industrial_activity": 1,
        "forward_looking": 1,
    }
    
def test_run_uk_growth():
    result = run_uk_growth()

    assert result.pillar_id == "uk_growth"
    assert result.name == "UK Growth"
    assert result.economy == "United Kingdom"
    assert result.buckets_used == 4
    assert len(result.bucket_results) == 4
    assert result.diagnostics["missing_bucket_ids"] == []
    
def test_run_japan_growth():
    result = run_japan_growth()

    assert result.pillar_id == "japan_growth"
    assert result.economy == "Japan"
    assert result.buckets_used == 4
    assert result.diagnostics["missing_bucket_ids"] == []