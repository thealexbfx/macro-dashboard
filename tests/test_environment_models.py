from datetime import date

import pytest

from macro_engine.models.environment import (
    EnvironmentSignal,
    MacroEnvironmentConfig,
    MacroEnvironmentHistory,
    MacroEnvironmentResult,
    MacroEnvironmentSnapshot,
    MacroRegimePeriod,
)
from macro_engine.models.pillar import PillarResult

def test_regime_period_accepts_valid_values() -> None:
    starting_snapshot = make_environment_snapshot(
        date(2026, 5, 31),
        activity_score=0.16,
    )
    ending_snapshot = make_environment_snapshot(
        date(2026, 7, 31),
        activity_score=0.25,
    )

    period = MacroRegimePeriod(
        economy="USA",
        environment_label="Reflationary Transition",
        start_date=date(2026, 5, 31),
        end_date=date(2026, 7, 31),
        observation_count=3,
        average_confidence_score=0.88,
        average_conviction_score=0.42,
        starting_snapshot=starting_snapshot,
        ending_snapshot=ending_snapshot,
        is_current=True,
    )

    assert period.observation_count == 3
    assert period.duration_days == 61
    assert period.activity_change == 0.09
    assert period.is_current is True


def test_regime_period_rejects_invalid_dates() -> None:
    starting_snapshot = make_environment_snapshot(
        date(2026, 7, 31)
    )
    ending_snapshot = make_environment_snapshot(
        date(2026, 6, 30)
    )

    with pytest.raises(
        ValueError,
        match="end_date",
    ):
        MacroRegimePeriod(
            economy="USA",
            environment_label="Reflationary Transition",
            start_date=date(2026, 7, 31),
            end_date=date(2026, 6, 30),
            observation_count=2,
            average_confidence_score=0.88,
            average_conviction_score=0.42,
            starting_snapshot=starting_snapshot,
            ending_snapshot=ending_snapshot,
        )


def test_regime_period_rejects_zero_observations() -> None:
    snapshot = make_environment_snapshot(
        date(2026, 7, 31)
    )

    with pytest.raises(
        ValueError,
        match="observation_count",
    ):
        MacroRegimePeriod(
            economy="USA",
            environment_label="Reflationary Transition",
            start_date=date(2026, 7, 31),
            end_date=date(2026, 7, 31),
            observation_count=0,
            average_confidence_score=0.88,
            average_conviction_score=0.42,
            starting_snapshot=snapshot,
            ending_snapshot=snapshot,
        )


def test_regime_period_rejects_mismatched_regime() -> None:
    starting_snapshot = make_environment_snapshot(
        date(2026, 6, 30),
        environment_label="Goldilocks Expansion",
    )
    ending_snapshot = make_environment_snapshot(
        date(2026, 7, 31),
        environment_label="Goldilocks Expansion",
    )

    with pytest.raises(
        ValueError,
        match="period regime",
    ):
        MacroRegimePeriod(
            economy="USA",
            environment_label="Reflationary Transition",
            start_date=date(2026, 6, 30),
            end_date=date(2026, 7, 31),
            observation_count=2,
            average_confidence_score=0.88,
            average_conviction_score=0.42,
            starting_snapshot=starting_snapshot,
            ending_snapshot=ending_snapshot,
        )

def make_environment_snapshot(
    snapshot_date: date,
    *,
    economy: str = "USA",
    environment_label: str = "Reflationary Transition",
    activity_score: float = 0.17,
    inflation_impulse_score: float = 0.49,
    financial_impulse_score: float = 0.07,
    confidence_score: float = 0.89,
    conviction_score: float = 0.36,
) -> MacroEnvironmentSnapshot:
    return MacroEnvironmentSnapshot(
        economy=economy,
        as_of_date=snapshot_date,
        activity_score=activity_score,
        activity_label="Expanding",
        inflation_impulse_score=inflation_impulse_score,
        inflation_impulse_label="Accelerating",
        financial_impulse_score=financial_impulse_score,
        financial_impulse_label="Neutral",
        environment_label=environment_label,
        confidence_score=confidence_score,
        environment_conviction_score=conviction_score,
        environment_conviction_label="Moderate",
        flags=(),
    )


def test_environment_history_accepts_ordered_snapshots() -> None:
    first = make_environment_snapshot(
        date(2026, 5, 31)
    )
    second = make_environment_snapshot(
        date(2026, 6, 30)
    )
    third = make_environment_snapshot(
        date(2026, 7, 21)
    )

    history = MacroEnvironmentHistory(
        economy="USA",
        snapshots=(first, second, third),
    )

    assert history.earliest is first
    assert history.latest is third
    assert history.observation_count == 3


def test_environment_history_rejects_empty_snapshots() -> None:
    with pytest.raises(
        ValueError,
        match="at least one",
    ):
        MacroEnvironmentHistory(
            economy="USA",
            snapshots=(),
        )


def test_environment_history_rejects_mismatched_economy() -> None:
    snapshots = (
        make_environment_snapshot(
            date(2026, 6, 30),
            economy="USA",
        ),
        make_environment_snapshot(
            date(2026, 7, 21),
            economy="UK",
        ),
    )

    with pytest.raises(
        ValueError,
        match="history economy",
    ):
        MacroEnvironmentHistory(
            economy="USA",
            snapshots=snapshots,
        )


def test_environment_history_rejects_duplicate_dates() -> None:
    snapshots = (
        make_environment_snapshot(
            date(2026, 7, 21)
        ),
        make_environment_snapshot(
            date(2026, 7, 21)
        ),
    )

    with pytest.raises(
        ValueError,
        match="unique",
    ):
        MacroEnvironmentHistory(
            economy="USA",
            snapshots=snapshots,
        )


def test_environment_history_rejects_out_of_order_dates() -> None:
    snapshots = (
        make_environment_snapshot(
            date(2026, 7, 21)
        ),
        make_environment_snapshot(
            date(2026, 6, 30)
        ),
    )

    with pytest.raises(
        ValueError,
        match="ordered",
    ):
        MacroEnvironmentHistory(
            economy="USA",
            snapshots=snapshots,
        )

def test_environment_snapshot_accepts_valid_values() -> None:
    snapshot = MacroEnvironmentSnapshot(
        economy="USA",
        as_of_date=date(2026, 7, 21),
        activity_score=0.17,
        activity_label="Expanding",
        inflation_impulse_score=0.49,
        inflation_impulse_label="Accelerating",
        financial_impulse_score=0.07,
        financial_impulse_label="Neutral",
        environment_label="Reflationary Transition",
        confidence_score=0.89,
        environment_conviction_score=0.36,
        environment_conviction_label="Moderate",
        flags=("activity_near_boundary",),
    )

    assert snapshot.economy == "USA"
    assert snapshot.environment_label == "Reflationary Transition"
    assert snapshot.flags == ("activity_near_boundary",)


@pytest.mark.parametrize(
    ("field_name", "field_value"),
    [
        ("activity_score", 1.20),
        ("inflation_impulse_score", -1.20),
        ("financial_impulse_score", 1.20),
    ],
)
def test_environment_snapshot_rejects_invalid_dimension_scores(
    field_name: str,
    field_value: float,
) -> None:
    values = {
        "economy": "USA",
        "as_of_date": date(2026, 7, 21),
        "activity_score": 0.17,
        "activity_label": "Expanding",
        "inflation_impulse_score": 0.49,
        "inflation_impulse_label": "Accelerating",
        "financial_impulse_score": 0.07,
        "financial_impulse_label": "Neutral",
        "environment_label": "Reflationary Transition",
        "confidence_score": 0.89,
        "environment_conviction_score": 0.36,
        "environment_conviction_label": "Moderate",
    }

    values[field_name] = field_value

    with pytest.raises(ValueError, match=field_name):
        MacroEnvironmentSnapshot(**values)


def test_environment_snapshot_rejects_invalid_confidence() -> None:
    with pytest.raises(ValueError, match="confidence_score"):
        MacroEnvironmentSnapshot(
            economy="USA",
            as_of_date=date(2026, 7, 21),
            activity_score=0.17,
            activity_label="Expanding",
            inflation_impulse_score=0.49,
            inflation_impulse_label="Accelerating",
            financial_impulse_score=0.07,
            financial_impulse_label="Neutral",
            environment_label="Reflationary Transition",
            confidence_score=1.20,
            environment_conviction_score=0.36,
            environment_conviction_label="Moderate",
        )


def test_environment_snapshot_rejects_empty_label() -> None:
    with pytest.raises(ValueError, match="environment_label"):
        MacroEnvironmentSnapshot(
            economy="USA",
            as_of_date=date(2026, 7, 21),
            activity_score=0.17,
            activity_label="Expanding",
            inflation_impulse_score=0.49,
            inflation_impulse_label="Accelerating",
            financial_impulse_score=0.07,
            financial_impulse_label="Neutral",
            environment_label="",
            confidence_score=0.89,
            environment_conviction_score=0.36,
            environment_conviction_label="Moderate",
        )

def make_pillar_result(name: str = "Growth") -> PillarResult:
    pillar_key = name.lower().replace(" ", "_")

    return PillarResult(
        pillar_id=f"usa_{pillar_key}",
        name=name,
        economy="USA",
        state_score=0.25,
        state_label="Moderate",
        trend_score=0.10,
        trend_label="Improving",
        breadth_score=0.60,
        breadth_label="Broad",
        confidence_score=0.80,
        confidence_label="High",
        buckets_used=0,
        bucket_results=(),
        key_drivers=(),
        flags=(),
        diagnostics={},
    )


def test_environment_config_accepts_valid_values() -> None:
    config = MacroEnvironmentConfig(
        economy="USA",
        minimum_pillars=3,
        minimum_confidence=0.60,
    )

    assert config.economy == "USA"
    assert config.minimum_pillars == 3
    assert config.minimum_confidence == 0.60


def test_environment_config_rejects_empty_economy() -> None:
    with pytest.raises(ValueError, match="economy"):
        MacroEnvironmentConfig(economy="")


def test_environment_config_rejects_invalid_minimum_pillars() -> None:
    with pytest.raises(ValueError, match="minimum_pillars"):
        MacroEnvironmentConfig(
            economy="USA",
            minimum_pillars=0,
        )


def test_environment_signal_accepts_valid_values() -> None:
    signal = EnvironmentSignal(
        code="growth_labor_confirmation",
        message="Growth and labor are improving together.",
        pillars=("Growth", "Labor"),
        severity="positive",
    )

    assert signal.code == "growth_labor_confirmation"
    assert signal.pillars == ("Growth", "Labor")
    assert signal.severity == "positive"


def test_environment_signal_rejects_invalid_severity() -> None:
    with pytest.raises(ValueError, match="severity"):
        EnvironmentSignal(
            code="test",
            message="Test signal",
            severity="invalid",
        )


def test_environment_result_builds_valid_pillar_map() -> None:
    growth = make_pillar_result("Growth")
    labor = make_pillar_result("Labor")

    result = MacroEnvironmentResult(
        economy="USA",
        as_of_date=date(2026, 7, 20),
        pillar_results=(growth, labor),
        pillar_map={
            "Growth": growth,
            "Labor": labor,
        },
        overall_direction="Improving",
        confidence_score=0.80,
        confidence_label="High",
    )

    assert result.economy == "USA"
    assert result.pillar_map["Growth"] is growth
    assert result.overall_direction == "Improving"


def test_environment_result_rejects_invalid_confidence() -> None:
    growth = make_pillar_result()

    with pytest.raises(ValueError, match="confidence_score"):
        MacroEnvironmentResult(
            economy="USA",
            as_of_date=None,
            pillar_results=(growth,),
            pillar_map={"Growth": growth},
            overall_direction="Improving",
            confidence_score=1.20,
        )


def test_environment_result_rejects_mismatched_pillar_map() -> None:
    growth = make_pillar_result("Growth")

    with pytest.raises(ValueError, match="pillar_map"):
        MacroEnvironmentResult(
            economy="USA",
            as_of_date=None,
            pillar_results=(growth,),
            pillar_map={"Labor": growth},
            overall_direction="Improving",
            confidence_score=0.80,
        )

def test_environment_result_accepts_multidimensional_fields() -> None:
    growth = make_pillar_result("Growth")

    result = MacroEnvironmentResult(
        economy="USA",
        as_of_date=None,
        pillar_results=(growth,),
        pillar_map={"Growth": growth},
        overall_direction="Improving",
        activity_score=0.30,
        activity_label="Expanding",
        inflation_impulse_score=0.50,
        inflation_impulse_label="Accelerating",
        financial_impulse_score=-0.10,
        financial_impulse_label="Neutral",
        environment_label="Reflationary Transition",
        environment_summary=(
            "Activity is improving while inflation pressure is rising."
        ),
        confidence_score=0.80,
        confidence_label="High",
    )

    assert result.activity_score == 0.30
    assert result.activity_label == "Expanding"
    assert result.inflation_impulse_label == "Accelerating"
    assert result.financial_impulse_label == "Neutral"
    assert result.environment_label == "Reflationary Transition"


def test_environment_result_rejects_invalid_activity_score() -> None:
    growth = make_pillar_result("Growth")

    with pytest.raises(ValueError, match="activity_score"):
        MacroEnvironmentResult(
            economy="USA",
            as_of_date=None,
            pillar_results=(growth,),
            pillar_map={"Growth": growth},
            overall_direction="Improving",
            activity_score=1.20,
        )


def test_environment_result_rejects_invalid_inflation_impulse_score() -> None:
    growth = make_pillar_result("Growth")

    with pytest.raises(ValueError, match="inflation_impulse_score"):
        MacroEnvironmentResult(
            economy="USA",
            as_of_date=None,
            pillar_results=(growth,),
            pillar_map={"Growth": growth},
            overall_direction="Improving",
            inflation_impulse_score=-1.20,
        )


def test_environment_result_rejects_invalid_financial_impulse_score() -> None:
    growth = make_pillar_result("Growth")

    with pytest.raises(ValueError, match="financial_impulse_score"):
        MacroEnvironmentResult(
            economy="USA",
            as_of_date=None,
            pillar_results=(growth,),
            pillar_map={"Growth": growth},
            overall_direction="Improving",
            financial_impulse_score=1.20,
        )


def test_environment_result_rejects_empty_environment_summary() -> None:
    growth = make_pillar_result("Growth")

    with pytest.raises(ValueError, match="environment_summary"):
        MacroEnvironmentResult(
            economy="USA",
            as_of_date=None,
            pillar_results=(growth,),
            pillar_map={"Growth": growth},
            overall_direction="Improving",
            environment_summary="",
        )

def test_environment_result_accepts_conviction_fields() -> None:
    growth = make_pillar_result("Growth")

    result = MacroEnvironmentResult(
        economy="USA",
        as_of_date=None,
        pillar_results=(growth,),
        pillar_map={"Growth": growth},
        overall_direction="Improving",
        environment_conviction_score=0.62,
        environment_conviction_label="Moderate",
        dimension_margins={
            "activity": 0.20,
            "inflation": 0.90,
            "financial": 0.55,
        },
    )

    assert result.environment_conviction_score == 0.62
    assert result.environment_conviction_label == "Moderate"
    assert result.dimension_margins["inflation"] == 0.90


def test_environment_result_rejects_invalid_conviction_score() -> None:
    growth = make_pillar_result("Growth")

    with pytest.raises(
        ValueError,
        match="environment_conviction_score",
    ):
        MacroEnvironmentResult(
            economy="USA",
            as_of_date=None,
            pillar_results=(growth,),
            pillar_map={"Growth": growth},
            overall_direction="Improving",
            environment_conviction_score=1.20,
        )


def test_environment_result_rejects_unknown_margin_dimension() -> None:
    growth = make_pillar_result("Growth")

    with pytest.raises(
        ValueError,
        match="unknown dimension",
    ):
        MacroEnvironmentResult(
            economy="USA",
            as_of_date=None,
            pillar_results=(growth,),
            pillar_map={"Growth": growth},
            overall_direction="Improving",
            dimension_margins={
                "activity": 0.50,
                "unknown": 0.50,
            },
        )


def test_environment_result_rejects_invalid_dimension_margin() -> None:
    growth = make_pillar_result("Growth")

    with pytest.raises(
        ValueError,
        match="dimension margins",
    ):
        MacroEnvironmentResult(
            economy="USA",
            as_of_date=None,
            pillar_results=(growth,),
            pillar_map={"Growth": growth},
            overall_direction="Improving",
            dimension_margins={
                "activity": -0.10,
            },
        )