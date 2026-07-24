import pytest

from macro_engine.models.bucket import BucketResult
from macro_engine.models.pillar import PillarResult

from macro_engine.pipelines.pillars import run_usa_growth


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