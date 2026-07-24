"""Tests for MacroLens pillar model contracts."""

import pytest

from macro_engine.models.pillar import PillarConfig, PillarResult


def test_pillar_config_accepts_valid_configuration():
    config = PillarConfig(
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
        description="Aggregates major US cyclical growth buckets.",
    )

    assert config.pillar_id == "usa_growth"
    assert config.name == "USA Growth"
    assert config.economy == "USA"
    assert config.minimum_buckets == 3
    assert len(config.bucket_weights) == 4


@pytest.mark.parametrize(
    ("field_name", "field_value"),
    [
        ("pillar_id", ""),
        ("pillar", ""),
        ("name", ""),
        ("economy", ""),
        ("pillar_id", "   "),
        ("name", "   "),
        ("economy", "   "),
    ],
)
def test_pillar_config_rejects_empty_required_fields(
    field_name,
    field_value,
):
    kwargs = {
        "pillar_id": "usa_growth",
        "pillar": "growth",
        "name": "USA Growth",
        "economy": "USA",
    }

    kwargs[field_name] = field_value

    with pytest.raises(ValueError, match=field_name):
        PillarConfig(**kwargs)


def test_pillar_config_rejects_invalid_minimum_buckets():
    with pytest.raises(
        ValueError,
        match="minimum_buckets must be at least 1",
    ):
        PillarConfig(
            pillar_id="usa_growth",
            pillar="growth",
            name="USA Growth",
            economy="USA",
            minimum_buckets=0,
        )


def test_pillar_config_rejects_negative_bucket_weights():
    with pytest.raises(
        ValueError,
        match="bucket weights must not be negative",
    ):
        PillarConfig(
            pillar_id="usa_growth",
            pillar="growth",
            name="USA Growth",
            economy="USA",
            bucket_weights={
                "usa_household_demand": -0.10,
            },
        )


def test_pillar_result_is_valid_with_usable_signal():
    result = PillarResult(
        pillar_id="usa_growth",
        name="USA Growth",
        economy="USA",
        state_score=0.30,
        state_label="Strong",
        trend_score=0.20,
        trend_label="Improving",
        breadth_score=0.50,
        breadth_label="Mostly Positive",
        confidence_score=0.85,
        confidence_label="High",
        buckets_used=4,
        bucket_results=(),
    )

    assert result.is_valid is True


def test_pillar_result_is_invalid_without_buckets():
    result = PillarResult(
        pillar_id="usa_growth",
        name="USA Growth",
        economy="USA",
        state_score=0.0,
        state_label="Normal",
        trend_score=0.0,
        trend_label="Stable",
        breadth_score=0.0,
        breadth_label="Mixed",
        confidence_score=0.85,
        confidence_label="High",
        buckets_used=0,
        bucket_results=(),
    )

    assert result.is_valid is False


def test_pillar_result_is_invalid_without_confidence():
    result = PillarResult(
        pillar_id="usa_growth",
        name="USA Growth",
        economy="USA",
        state_score=0.0,
        state_label="Normal",
        trend_score=0.0,
        trend_label="Stable",
        breadth_score=0.0,
        breadth_label="Mixed",
        confidence_score=0.0,
        confidence_label="Very Low",
        buckets_used=4,
        bucket_results=(),
    )

    assert result.is_valid is False
    
def test_usa_growth_metadata_is_valid():
    from macro_engine.metadata.pillars import USA_GROWTH

    assert USA_GROWTH.pillar_id == "usa_growth"
    assert USA_GROWTH.pillar == "growth"
    assert USA_GROWTH.economy == "USA"
    assert USA_GROWTH.minimum_buckets == 3
    assert sum(USA_GROWTH.bucket_weights.values()) == pytest.approx(1.0)
    assert set(USA_GROWTH.bucket_weights) == {
        "usa_household_demand",
        "usa_employment_momentum",
        "usa_industrial_activity",
        "usa_housing",
    }