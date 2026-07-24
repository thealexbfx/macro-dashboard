"""Models for historical macro-environment validation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class RegimeStatistics:
    """
    Historical statistics for one macro-environment classification.
    """

    economy: str
    environment_label: str

    first_observation_date: date
    last_observation_date: date

    occurrence_count: int
    observation_count: int
    coverage_ratio: float

    average_duration_observations: float
    median_duration_observations: float
    minimum_duration_observations: int
    maximum_duration_observations: int

    average_duration_days: float
    median_duration_days: float
    minimum_duration_days: int
    maximum_duration_days: int

    average_confidence_score: float
    median_confidence_score: float
    confidence_standard_deviation: float

    average_conviction_score: float
    median_conviction_score: float
    conviction_standard_deviation: float

    average_activity_score: float
    average_inflation_impulse_score: float
    average_financial_impulse_score: float

    current_regime: bool = False

    def __post_init__(self) -> None:
        if not self.economy.strip():
            raise ValueError(
                "economy must not be empty"
            )

        if not self.environment_label.strip():
            raise ValueError(
                "environment_label must not be empty"
            )

        if self.last_observation_date < self.first_observation_date:
            raise ValueError(
                "last_observation_date must not be before "
                "first_observation_date"
            )

        if self.occurrence_count < 1:
            raise ValueError(
                "occurrence_count must be at least 1"
            )

        if self.observation_count < 1:
            raise ValueError(
                "observation_count must be at least 1"
            )

        if not 0.0 <= self.coverage_ratio <= 1.0:
            raise ValueError(
                "coverage_ratio must be between 0 and 1"
            )

        positive_duration_fields = {
            "average_duration_observations": (
                self.average_duration_observations
            ),
            "median_duration_observations": (
                self.median_duration_observations
            ),
            "minimum_duration_observations": (
                self.minimum_duration_observations
            ),
            "maximum_duration_observations": (
                self.maximum_duration_observations
            ),
        }

        for field_name, value in positive_duration_fields.items():
            if value < 1:
                raise ValueError(
                    f"{field_name} must be at least 1"
                )

        non_negative_duration_fields = {
            "average_duration_days": (
                self.average_duration_days
            ),
            "median_duration_days": (
                self.median_duration_days
            ),
            "minimum_duration_days": (
                self.minimum_duration_days
            ),
            "maximum_duration_days": (
                self.maximum_duration_days
            ),
        }

        for field_name, value in non_negative_duration_fields.items():
            if value < 0:
                raise ValueError(
                    f"{field_name} must not be negative"
                )

        probability_fields = {
            "average_confidence_score": (
                self.average_confidence_score
            ),
            "median_confidence_score": (
                self.median_confidence_score
            ),
            "confidence_standard_deviation": (
                self.confidence_standard_deviation
            ),
            "average_conviction_score": (
                self.average_conviction_score
            ),
            "median_conviction_score": (
                self.median_conviction_score
            ),
            "conviction_standard_deviation": (
                self.conviction_standard_deviation
            ),
        }

        for field_name, value in probability_fields.items():
            if not 0.0 <= value <= 1.0:
                raise ValueError(
                    f"{field_name} must be between 0 and 1"
                )

        dimension_scores = {
            "average_activity_score": (
                self.average_activity_score
            ),
            "average_inflation_impulse_score": (
                self.average_inflation_impulse_score
            ),
            "average_financial_impulse_score": (
                self.average_financial_impulse_score
            ),
        }

        for field_name, value in dimension_scores.items():
            if not -1.0 <= value <= 1.0:
                raise ValueError(
                    f"{field_name} must be between -1 and 1"
                )


@dataclass(frozen=True)
class EnvironmentValidationSummary:
    """
    Historical validation summary for one macro-environment history.
    """

    economy: str

    start_date: date
    end_date: date

    observation_count: int
    regime_period_count: int
    unique_regime_count: int

    average_confidence_score: float
    average_conviction_score: float

    most_common_regime: str
    most_persistent_regime: str
    current_regime: str

    transitional_observation_count: int
    transitional_coverage_ratio: float

    regime_statistics: tuple[RegimeStatistics, ...]

    def __post_init__(self) -> None:
        if not self.economy.strip():
            raise ValueError(
                "economy must not be empty"
            )

        if self.end_date < self.start_date:
            raise ValueError(
                "end_date must not be before start_date"
            )

        if self.observation_count < 1:
            raise ValueError(
                "observation_count must be at least 1"
            )

        if self.regime_period_count < 1:
            raise ValueError(
                "regime_period_count must be at least 1"
            )

        if self.unique_regime_count < 1:
            raise ValueError(
                "unique_regime_count must be at least 1"
            )

        if (
            self.unique_regime_count
            != len(self.regime_statistics)
        ):
            raise ValueError(
                "unique_regime_count must match regime_statistics"
            )

        probability_fields = {
            "average_confidence_score": (
                self.average_confidence_score
            ),
            "average_conviction_score": (
                self.average_conviction_score
            ),
            "transitional_coverage_ratio": (
                self.transitional_coverage_ratio
            ),
        }

        for field_name, value in probability_fields.items():
            if not 0.0 <= value <= 1.0:
                raise ValueError(
                    f"{field_name} must be between 0 and 1"
                )

        if self.transitional_observation_count < 0:
            raise ValueError(
                "transitional_observation_count "
                "must not be negative"
            )

        required_labels = {
            "most_common_regime": self.most_common_regime,
            "most_persistent_regime": (
                self.most_persistent_regime
            ),
            "current_regime": self.current_regime,
        }

        for field_name, value in required_labels.items():
            if not value.strip():
                raise ValueError(
                    f"{field_name} must not be empty"
                )
                
@dataclass(frozen=True)
class RegimeTransitionStatistics:
    """
    Historical statistics for one completed regime transition.
    """

    economy: str

    from_environment_label: str
    to_environment_label: str

    transition_count: int

    source_exit_count: int
    transition_probability: float

    first_transition_date: date
    last_transition_date: date

    average_source_duration_observations: float
    median_source_duration_observations: float

    average_source_confidence_score: float
    average_source_conviction_score: float

    average_pre_transition_activity_score: float
    average_pre_transition_inflation_score: float
    average_pre_transition_financial_score: float

    def __post_init__(self) -> None:
        if not self.economy.strip():
            raise ValueError(
                "economy must not be empty"
            )

        required_labels = {
            "from_environment_label": (
                self.from_environment_label
            ),
            "to_environment_label": (
                self.to_environment_label
            ),
        }

        for field_name, value in required_labels.items():
            if not value.strip():
                raise ValueError(
                    f"{field_name} must not be empty"
                )

        if (
            self.from_environment_label
            == self.to_environment_label
        ):
            raise ValueError(
                "a completed transition must change regime"
            )

        if self.transition_count < 1:
            raise ValueError(
                "transition_count must be at least 1"
            )

        if self.source_exit_count < self.transition_count:
            raise ValueError(
                "source_exit_count must be at least "
                "transition_count"
            )

        if not 0.0 <= self.transition_probability <= 1.0:
            raise ValueError(
                "transition_probability must be between 0 and 1"
            )

        if self.last_transition_date < self.first_transition_date:
            raise ValueError(
                "last_transition_date must not be before "
                "first_transition_date"
            )

        duration_fields = {
            "average_source_duration_observations": (
                self.average_source_duration_observations
            ),
            "median_source_duration_observations": (
                self.median_source_duration_observations
            ),
        }

        for field_name, value in duration_fields.items():
            if value < 1:
                raise ValueError(
                    f"{field_name} must be at least 1"
                )

        probability_fields = {
            "average_source_confidence_score": (
                self.average_source_confidence_score
            ),
            "average_source_conviction_score": (
                self.average_source_conviction_score
            ),
        }

        for field_name, value in probability_fields.items():
            if not 0.0 <= value <= 1.0:
                raise ValueError(
                    f"{field_name} must be between 0 and 1"
                )

        dimension_fields = {
            "average_pre_transition_activity_score": (
                self.average_pre_transition_activity_score
            ),
            "average_pre_transition_inflation_score": (
                self.average_pre_transition_inflation_score
            ),
            "average_pre_transition_financial_score": (
                self.average_pre_transition_financial_score
            ),
        }

        for field_name, value in dimension_fields.items():
            if not -1.0 <= value <= 1.0:
                raise ValueError(
                    f"{field_name} must be between -1 and 1"
                )


@dataclass(frozen=True)
class RegimeExitStatistics:
    """
    Exit behavior for one source regime.
    """

    economy: str
    environment_label: str

    completed_exit_count: int
    destination_count: int

    most_common_next_regime: str
    most_common_transition_probability: float

    average_duration_before_exit_observations: float
    average_confidence_before_exit: float
    average_conviction_before_exit: float

    current_regime: bool = False

    def __post_init__(self) -> None:
        if not self.economy.strip():
            raise ValueError(
                "economy must not be empty"
            )

        if not self.environment_label.strip():
            raise ValueError(
                "environment_label must not be empty"
            )

        if self.completed_exit_count < 1:
            raise ValueError(
                "completed_exit_count must be at least 1"
            )

        if self.destination_count < 1:
            raise ValueError(
                "destination_count must be at least 1"
            )

        if not self.most_common_next_regime.strip():
            raise ValueError(
                "most_common_next_regime must not be empty"
            )

        probability_fields = {
            "most_common_transition_probability": (
                self.most_common_transition_probability
            ),
            "average_confidence_before_exit": (
                self.average_confidence_before_exit
            ),
            "average_conviction_before_exit": (
                self.average_conviction_before_exit
            ),
        }

        for field_name, value in probability_fields.items():
            if not 0.0 <= value <= 1.0:
                raise ValueError(
                    f"{field_name} must be between 0 and 1"
                )

        if self.average_duration_before_exit_observations < 1:
            raise ValueError(
                "average_duration_before_exit_observations "
                "must be at least 1"
            )


@dataclass(frozen=True)
class RegimeTransitionSummary:
    """
    Summary of completed regime transitions in an environment history.
    """

    economy: str

    start_date: date
    end_date: date

    regime_period_count: int
    completed_transition_count: int

    unique_transition_count: int
    source_regime_count: int

    most_common_transition: str
    most_common_transition_count: int

    transition_statistics: tuple[
        RegimeTransitionStatistics,
        ...
    ]

    exit_statistics: tuple[
        RegimeExitStatistics,
        ...
    ]

    def __post_init__(self) -> None:
        if not self.economy.strip():
            raise ValueError(
                "economy must not be empty"
            )

        if self.end_date < self.start_date:
            raise ValueError(
                "end_date must not be before start_date"
            )

        if self.regime_period_count < 2:
            raise ValueError(
                "regime_period_count must be at least 2"
            )

        if self.completed_transition_count < 1:
            raise ValueError(
                "completed_transition_count must be at least 1"
            )

        if (
            self.unique_transition_count
            != len(self.transition_statistics)
        ):
            raise ValueError(
                "unique_transition_count must match "
                "transition_statistics"
            )

        if (
            self.source_regime_count
            != len(self.exit_statistics)
        ):
            raise ValueError(
                "source_regime_count must match exit_statistics"
            )

        if not self.most_common_transition.strip():
            raise ValueError(
                "most_common_transition must not be empty"
            )

        if self.most_common_transition_count < 1:
            raise ValueError(
                "most_common_transition_count must be at least 1"
            )
            
@dataclass(frozen=True)
class RegimeStabilityStatistics:
    """
    Historical stability statistics for one environment classification.
    """

    economy: str
    environment_label: str

    occurrence_count: int
    completed_occurrence_count: int
    observation_count: int

    average_duration_observations: float
    median_duration_observations: float
    minimum_duration_observations: int
    maximum_duration_observations: int

    short_lived_occurrence_count: int
    short_lived_occurrence_ratio: float

    average_starting_confidence_score: float
    average_ending_confidence_score: float
    average_confidence_change: float

    average_starting_conviction_score: float
    average_ending_conviction_score: float
    average_conviction_change: float

    current_regime: bool = False

    def __post_init__(self) -> None:
        if not self.economy.strip():
            raise ValueError(
                "economy must not be empty"
            )

        if not self.environment_label.strip():
            raise ValueError(
                "environment_label must not be empty"
            )

        if self.occurrence_count < 1:
            raise ValueError(
                "occurrence_count must be at least 1"
            )

        if not 0 <= self.completed_occurrence_count <= self.occurrence_count:
            raise ValueError(
                "completed_occurrence_count must be between "
                "0 and occurrence_count"
            )

        if self.observation_count < 1:
            raise ValueError(
                "observation_count must be at least 1"
            )

        duration_fields = {
            "average_duration_observations": (
                self.average_duration_observations
            ),
            "median_duration_observations": (
                self.median_duration_observations
            ),
            "minimum_duration_observations": (
                self.minimum_duration_observations
            ),
            "maximum_duration_observations": (
                self.maximum_duration_observations
            ),
        }

        for field_name, value in duration_fields.items():
            if value < 1:
                raise ValueError(
                    f"{field_name} must be at least 1"
                )

        if not 0 <= self.short_lived_occurrence_count <= self.occurrence_count:
            raise ValueError(
                "short_lived_occurrence_count must be between "
                "0 and occurrence_count"
            )

        probability_fields = {
            "short_lived_occurrence_ratio": (
                self.short_lived_occurrence_ratio
            ),
            "average_starting_confidence_score": (
                self.average_starting_confidence_score
            ),
            "average_ending_confidence_score": (
                self.average_ending_confidence_score
            ),
            "average_starting_conviction_score": (
                self.average_starting_conviction_score
            ),
            "average_ending_conviction_score": (
                self.average_ending_conviction_score
            ),
        }

        for field_name, value in probability_fields.items():
            if not 0.0 <= value <= 1.0:
                raise ValueError(
                    f"{field_name} must be between 0 and 1"
                )

        change_fields = {
            "average_confidence_change": (
                self.average_confidence_change
            ),
            "average_conviction_change": (
                self.average_conviction_change
            ),
        }

        for field_name, value in change_fields.items():
            if not -1.0 <= value <= 1.0:
                raise ValueError(
                    f"{field_name} must be between -1 and 1"
                )


@dataclass(frozen=True)
class StabilityValidationSummary:
    """
    Overall stability and churn validation for environment history.
    """

    economy: str

    start_date: date
    end_date: date

    observation_count: int
    regime_period_count: int
    completed_regime_period_count: int

    average_regime_duration_observations: float
    median_regime_duration_observations: float

    short_lived_period_count: int
    short_lived_period_ratio: float
    short_lived_observation_count: int
    short_lived_observation_ratio: float

    completed_transition_count: int
    annualized_transition_rate: float

    oscillation_count: int
    oscillation_ratio: float

    average_confidence_before_transition: float
    average_conviction_before_transition: float

    average_confidence_change_within_period: float
    average_conviction_change_within_period: float

    churn_label: str

    regime_statistics: tuple[
        RegimeStabilityStatistics,
        ...
    ]

    def __post_init__(self) -> None:
        if not self.economy.strip():
            raise ValueError(
                "economy must not be empty"
            )

        if self.end_date < self.start_date:
            raise ValueError(
                "end_date must not be before start_date"
            )

        positive_integer_fields = {
            "observation_count": self.observation_count,
            "regime_period_count": self.regime_period_count,
        }

        for field_name, value in positive_integer_fields.items():
            if value < 1:
                raise ValueError(
                    f"{field_name} must be at least 1"
                )

        if not (
            0
            <= self.completed_regime_period_count
            <= self.regime_period_count
        ):
            raise ValueError(
                "completed_regime_period_count must be between "
                "0 and regime_period_count"
            )

        duration_fields = {
            "average_regime_duration_observations": (
                self.average_regime_duration_observations
            ),
            "median_regime_duration_observations": (
                self.median_regime_duration_observations
            ),
        }

        for field_name, value in duration_fields.items():
            if value < 1:
                raise ValueError(
                    f"{field_name} must be at least 1"
                )

        count_fields = {
            "short_lived_period_count": (
                self.short_lived_period_count
            ),
            "short_lived_observation_count": (
                self.short_lived_observation_count
            ),
            "completed_transition_count": (
                self.completed_transition_count
            ),
            "oscillation_count": self.oscillation_count,
        }

        for field_name, value in count_fields.items():
            if value < 0:
                raise ValueError(
                    f"{field_name} must not be negative"
                )

        probability_fields = {
            "short_lived_period_ratio": (
                self.short_lived_period_ratio
            ),
            "short_lived_observation_ratio": (
                self.short_lived_observation_ratio
            ),
            "oscillation_ratio": (
                self.oscillation_ratio
            ),
            "average_confidence_before_transition": (
                self.average_confidence_before_transition
            ),
            "average_conviction_before_transition": (
                self.average_conviction_before_transition
            ),
        }

        for field_name, value in probability_fields.items():
            if not 0.0 <= value <= 1.0:
                raise ValueError(
                    f"{field_name} must be between 0 and 1"
                )

        if self.annualized_transition_rate < 0:
            raise ValueError(
                "annualized_transition_rate must not be negative"
            )

        change_fields = {
            "average_confidence_change_within_period": (
                self.average_confidence_change_within_period
            ),
            "average_conviction_change_within_period": (
                self.average_conviction_change_within_period
            ),
        }

        for field_name, value in change_fields.items():
            if not -1.0 <= value <= 1.0:
                raise ValueError(
                    f"{field_name} must be between -1 and 1"
                )

        if not self.churn_label.strip():
            raise ValueError(
                "churn_label must not be empty"
            )