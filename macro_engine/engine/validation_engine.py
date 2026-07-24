"""Historical validation calculations for macro environments."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date
from statistics import fmean, median, pstdev

from macro_engine.engine.environment_engine import (
    build_regime_periods,
)
from macro_engine.models.environment import (
    MacroEnvironmentHistory,
    MacroEnvironmentSnapshot,
    MacroRegimePeriod,
)
from macro_engine.models.validation import (
    EnvironmentValidationSummary,
    RegimeExitStatistics,
    RegimeStabilityStatistics,
    RegimeStatistics,
    RegimeTransitionStatistics,
    RegimeTransitionSummary,
    StabilityValidationSummary,
)


TRANSITIONAL_LABEL_TERMS = (
    "transition",
    "transitional",
    "mixed",
)


def is_transitional_regime(
    environment_label: str,
) -> bool:
    """
    Return whether a regime label represents a transitional state.

    This deliberately uses label terminology rather than hard-coding
    every current environment classification.
    """

    normalized_label = environment_label.strip().lower()

    return any(
        term in normalized_label
        for term in TRANSITIONAL_LABEL_TERMS
    )


def _rounded_mean(
    values: list[float],
) -> float:
    return round(
        fmean(values),
        4,
    )


def _rounded_median(
    values: list[float],
) -> float:
    return round(
        median(values),
        4,
    )


def _rounded_population_standard_deviation(
    values: list[float],
) -> float:
    if len(values) == 1:
        return 0.0

    return round(
        pstdev(values),
        4,
    )


def _group_snapshots_by_regime(
    history: MacroEnvironmentHistory,
) -> dict[str, list[MacroEnvironmentSnapshot]]:
    grouped: dict[
        str,
        list[MacroEnvironmentSnapshot],
    ] = defaultdict(list)

    for snapshot in history.snapshots:
        grouped[snapshot.environment_label].append(
            snapshot
        )

    return dict(grouped)


def _group_periods_by_regime(
    periods: tuple[MacroRegimePeriod, ...],
) -> dict[str, list[MacroRegimePeriod]]:
    grouped: dict[
        str,
        list[MacroRegimePeriod],
    ] = defaultdict(list)

    for period in periods:
        grouped[period.environment_label].append(
            period
        )

    return dict(grouped)


def calculate_regime_statistics(
    history: MacroEnvironmentHistory,
) -> tuple[RegimeStatistics, ...]:
    """
    Calculate statistics for every regime present in history.

    Statistics are ordered by historical coverage, highest first.
    Alphabetical regime label is used as the deterministic tie-breaker.
    """

    periods = build_regime_periods(history)

    snapshots_by_regime = _group_snapshots_by_regime(
        history
    )
    periods_by_regime = _group_periods_by_regime(
        periods
    )

    statistics: list[RegimeStatistics] = []

    current_label = history.latest.environment_label

    for environment_label, snapshots in (
        snapshots_by_regime.items()
    ):
        regime_periods = periods_by_regime[
            environment_label
        ]

        duration_observations = [
            period.observation_count
            for period in regime_periods
        ]

        duration_days = [
            period.duration_days
            for period in regime_periods
        ]

        confidence_scores = [
            snapshot.confidence_score
            for snapshot in snapshots
        ]

        conviction_scores = [
            snapshot.environment_conviction_score
            for snapshot in snapshots
        ]

        activity_scores = [
            snapshot.activity_score
            for snapshot in snapshots
        ]

        inflation_scores = [
            snapshot.inflation_impulse_score
            for snapshot in snapshots
        ]

        financial_scores = [
            snapshot.financial_impulse_score
            for snapshot in snapshots
        ]

        observation_count = len(snapshots)

        statistics.append(
            RegimeStatistics(
                economy=history.economy,
                environment_label=environment_label,
                first_observation_date=(
                    snapshots[0].as_of_date
                ),
                last_observation_date=(
                    snapshots[-1].as_of_date
                ),
                occurrence_count=len(regime_periods),
                observation_count=observation_count,
                coverage_ratio=round(
                    observation_count
                    / history.observation_count,
                    4,
                ),
                average_duration_observations=(
                    _rounded_mean(
                        [
                            float(value)
                            for value
                            in duration_observations
                        ]
                    )
                ),
                median_duration_observations=(
                    _rounded_median(
                        [
                            float(value)
                            for value
                            in duration_observations
                        ]
                    )
                ),
                minimum_duration_observations=min(
                    duration_observations
                ),
                maximum_duration_observations=max(
                    duration_observations
                ),
                average_duration_days=_rounded_mean(
                    [
                        float(value)
                        for value in duration_days
                    ]
                ),
                median_duration_days=_rounded_median(
                    [
                        float(value)
                        for value in duration_days
                    ]
                ),
                minimum_duration_days=min(
                    duration_days
                ),
                maximum_duration_days=max(
                    duration_days
                ),
                average_confidence_score=(
                    _rounded_mean(
                        confidence_scores
                    )
                ),
                median_confidence_score=(
                    _rounded_median(
                        confidence_scores
                    )
                ),
                confidence_standard_deviation=(
                    _rounded_population_standard_deviation(
                        confidence_scores
                    )
                ),
                average_conviction_score=(
                    _rounded_mean(
                        conviction_scores
                    )
                ),
                median_conviction_score=(
                    _rounded_median(
                        conviction_scores
                    )
                ),
                conviction_standard_deviation=(
                    _rounded_population_standard_deviation(
                        conviction_scores
                    )
                ),
                average_activity_score=(
                    _rounded_mean(
                        activity_scores
                    )
                ),
                average_inflation_impulse_score=(
                    _rounded_mean(
                        inflation_scores
                    )
                ),
                average_financial_impulse_score=(
                    _rounded_mean(
                        financial_scores
                    )
                ),
                current_regime=(
                    environment_label
                    == current_label
                ),
            )
        )

    return tuple(
        sorted(
            statistics,
            key=lambda result: (
                -result.observation_count,
                result.environment_label,
            ),
        )
    )
    
def _snapshots_for_period(
    history: MacroEnvironmentHistory,
    period: MacroRegimePeriod,
) -> tuple[MacroEnvironmentSnapshot, ...]:
    """
    Return all historical snapshots contained in one regime period.
    """

    return tuple(
        snapshot
        for snapshot in history.snapshots
        if (
            period.start_date
            <= snapshot.as_of_date
            <= period.end_date
        )
    )


def _classify_churn(
    *,
    short_lived_period_ratio: float,
    annualized_transition_rate: float,
    oscillation_ratio: float,
) -> str:
    """
    Classify overall regime churn using transparent diagnostics.

    This is a validation label, not an investment classification.
    """

    if (
        short_lived_period_ratio >= 0.50
        or annualized_transition_rate >= 8.0
        or oscillation_ratio >= 0.40
    ):
        return "High Churn"

    if (
        short_lived_period_ratio >= 0.30
        or annualized_transition_rate >= 5.0
        or oscillation_ratio >= 0.20
    ):
        return "Moderate Churn"

    return "Low Churn"


def calculate_regime_stability_statistics(
    history: MacroEnvironmentHistory,
    *,
    short_lived_max_observations: int = 1,
) -> tuple[RegimeStabilityStatistics, ...]:
    """
    Calculate stability statistics for each historical regime.

    A short-lived occurrence is one whose observation count is less than
    or equal to short_lived_max_observations.
    """

    if short_lived_max_observations < 1:
        raise ValueError(
            "short_lived_max_observations must be at least 1"
        )

    periods = build_regime_periods(history)

    periods_by_regime: dict[
        str,
        list[MacroRegimePeriod],
    ] = defaultdict(list)

    for period in periods:
        periods_by_regime[
            period.environment_label
        ].append(period)

    current_period = periods[-1]
    current_label = current_period.environment_label

    statistics: list[RegimeStabilityStatistics] = []

    for environment_label, regime_periods in (
        periods_by_regime.items()
    ):
        duration_observations = [
            period.observation_count
            for period in regime_periods
        ]

        starting_confidence_scores: list[float] = []
        ending_confidence_scores: list[float] = []
        confidence_changes: list[float] = []

        starting_conviction_scores: list[float] = []
        ending_conviction_scores: list[float] = []
        conviction_changes: list[float] = []

        observation_count = 0

        for period in regime_periods:
            snapshots = _snapshots_for_period(
                history,
                period,
            )

            if not snapshots:
                raise ValueError(
                    "regime period contains no matching snapshots"
                )

            starting_snapshot = snapshots[0]
            ending_snapshot = snapshots[-1]

            observation_count += len(snapshots)

            starting_confidence_scores.append(
                starting_snapshot.confidence_score
            )
            ending_confidence_scores.append(
                ending_snapshot.confidence_score
            )
            confidence_changes.append(
                ending_snapshot.confidence_score
                - starting_snapshot.confidence_score
            )

            starting_conviction_scores.append(
                starting_snapshot.environment_conviction_score
            )
            ending_conviction_scores.append(
                ending_snapshot.environment_conviction_score
            )
            conviction_changes.append(
                ending_snapshot.environment_conviction_score
                - starting_snapshot.environment_conviction_score
            )

        short_lived_occurrence_count = sum(
            1
            for duration in duration_observations
            if duration <= short_lived_max_observations
        )

        completed_occurrence_count = len(regime_periods)

        if (
            regime_periods[-1].start_date
            == current_period.start_date
            and regime_periods[-1].end_date
            == current_period.end_date
        ):
            completed_occurrence_count -= 1

        statistics.append(
            RegimeStabilityStatistics(
                economy=history.economy,
                environment_label=environment_label,
                occurrence_count=len(regime_periods),
                completed_occurrence_count=(
                    completed_occurrence_count
                ),
                observation_count=observation_count,
                average_duration_observations=(
                    _rounded_mean(
                        [
                            float(value)
                            for value in duration_observations
                        ]
                    )
                ),
                median_duration_observations=(
                    _rounded_median(
                        [
                            float(value)
                            for value in duration_observations
                        ]
                    )
                ),
                minimum_duration_observations=min(
                    duration_observations
                ),
                maximum_duration_observations=max(
                    duration_observations
                ),
                short_lived_occurrence_count=(
                    short_lived_occurrence_count
                ),
                short_lived_occurrence_ratio=round(
                    short_lived_occurrence_count
                    / len(regime_periods),
                    4,
                ),
                average_starting_confidence_score=(
                    _rounded_mean(
                        starting_confidence_scores
                    )
                ),
                average_ending_confidence_score=(
                    _rounded_mean(
                        ending_confidence_scores
                    )
                ),
                average_confidence_change=(
                    _rounded_mean(
                        confidence_changes
                    )
                ),
                average_starting_conviction_score=(
                    _rounded_mean(
                        starting_conviction_scores
                    )
                ),
                average_ending_conviction_score=(
                    _rounded_mean(
                        ending_conviction_scores
                    )
                ),
                average_conviction_change=(
                    _rounded_mean(
                        conviction_changes
                    )
                ),
                current_regime=(
                    environment_label == current_label
                ),
            )
        )

    return tuple(
        sorted(
            statistics,
            key=lambda result: (
                -result.observation_count,
                result.environment_label,
            ),
        )
    )


def count_regime_oscillations(
    history: MacroEnvironmentHistory,
) -> int:
    """
    Count A -> B -> A oscillations across consecutive regime periods.

    Example:

        Goldilocks
        Slowdown
        Goldilocks

    counts as one oscillation.
    """

    periods = build_regime_periods(history)

    return sum(
        1
        for index in range(len(periods) - 2)
        if (
            periods[index].environment_label
            == periods[index + 2].environment_label
            and periods[index].environment_label
            != periods[index + 1].environment_label
        )
    )


def build_stability_validation_summary(
    history: MacroEnvironmentHistory,
    *,
    short_lived_max_observations: int = 1,
) -> StabilityValidationSummary:
    """
    Build the complete environment stability and churn summary.
    """

    if short_lived_max_observations < 1:
        raise ValueError(
            "short_lived_max_observations must be at least 1"
        )

    periods = build_regime_periods(history)

    durations = [
        period.observation_count
        for period in periods
    ]

    short_lived_periods = [
        period
        for period in periods
        if (
            period.observation_count
            <= short_lived_max_observations
        )
    ]

    short_lived_observation_count = sum(
        period.observation_count
        for period in short_lived_periods
    )

    completed_transition_count = max(
        len(periods) - 1,
        0,
    )

    completed_periods = periods[:-1]

    confidence_before_transition = [
        period.ending_snapshot.confidence_score
        for period in completed_periods
    ]

    conviction_before_transition = [
        period.ending_snapshot.environment_conviction_score
        for period in completed_periods
    ]

    confidence_changes: list[float] = []
    conviction_changes: list[float] = []

    for period in periods:
        snapshots = _snapshots_for_period(
            history,
            period,
        )

        starting_snapshot = snapshots[0]
        ending_snapshot = snapshots[-1]

        confidence_changes.append(
            ending_snapshot.confidence_score
            - starting_snapshot.confidence_score
        )

        conviction_changes.append(
            ending_snapshot.environment_conviction_score
            - starting_snapshot.environment_conviction_score
        )

    history_days = (
        history.latest.as_of_date
        - history.earliest.as_of_date
    ).days

    if history_days <= 0:
        annualized_transition_rate = 0.0
    else:
        annualized_transition_rate = round(
            completed_transition_count
            / history_days
            * 365.25,
            4,
        )

    oscillation_count = count_regime_oscillations(
        history
    )

    possible_oscillation_windows = max(
        len(periods) - 2,
        0,
    )

    if possible_oscillation_windows == 0:
        oscillation_ratio = 0.0
    else:
        oscillation_ratio = round(
            oscillation_count
            / possible_oscillation_windows,
            4,
        )

    short_lived_period_ratio = round(
        len(short_lived_periods)
        / len(periods),
        4,
    )

    short_lived_observation_ratio = round(
        short_lived_observation_count
        / history.observation_count,
        4,
    )

    churn_label = _classify_churn(
        short_lived_period_ratio=(
            short_lived_period_ratio
        ),
        annualized_transition_rate=(
            annualized_transition_rate
        ),
        oscillation_ratio=oscillation_ratio,
    )

    if confidence_before_transition:
        average_confidence_before_transition = (
            _rounded_mean(
                confidence_before_transition
            )
        )
    else:
        average_confidence_before_transition = (
            history.latest.confidence_score
        )

    if conviction_before_transition:
        average_conviction_before_transition = (
            _rounded_mean(
                conviction_before_transition
            )
        )
    else:
        average_conviction_before_transition = (
            history.latest.environment_conviction_score
        )

    return StabilityValidationSummary(
        economy=history.economy,
        start_date=history.earliest.as_of_date,
        end_date=history.latest.as_of_date,
        observation_count=history.observation_count,
        regime_period_count=len(periods),
        completed_regime_period_count=max(
            len(periods) - 1,
            0,
        ),
        average_regime_duration_observations=(
            _rounded_mean(
                [
                    float(value)
                    for value in durations
                ]
            )
        ),
        median_regime_duration_observations=(
            _rounded_median(
                [
                    float(value)
                    for value in durations
                ]
            )
        ),
        short_lived_period_count=len(
            short_lived_periods
        ),
        short_lived_period_ratio=(
            short_lived_period_ratio
        ),
        short_lived_observation_count=(
            short_lived_observation_count
        ),
        short_lived_observation_ratio=(
            short_lived_observation_ratio
        ),
        completed_transition_count=(
            completed_transition_count
        ),
        annualized_transition_rate=(
            annualized_transition_rate
        ),
        oscillation_count=oscillation_count,
        oscillation_ratio=oscillation_ratio,
        average_confidence_before_transition=(
            round(
                average_confidence_before_transition,
                4,
            )
        ),
        average_conviction_before_transition=(
            round(
                average_conviction_before_transition,
                4,
            )
        ),
        average_confidence_change_within_period=(
            _rounded_mean(
                confidence_changes
            )
        ),
        average_conviction_change_within_period=(
            _rounded_mean(
                conviction_changes
            )
        ),
        churn_label=churn_label,
        regime_statistics=(
            calculate_regime_stability_statistics(
                history,
                short_lived_max_observations=(
                    short_lived_max_observations
                ),
            )
        ),
    )


def build_environment_validation_summary(
    history: MacroEnvironmentHistory,
) -> EnvironmentValidationSummary:
    """
    Build the primary historical validation summary.
    """

    periods = build_regime_periods(history)

    regime_statistics = calculate_regime_statistics(
        history
    )

    average_confidence_score = _rounded_mean(
        [
            snapshot.confidence_score
            for snapshot in history.snapshots
        ]
    )

    average_conviction_score = _rounded_mean(
        [
            snapshot.environment_conviction_score
            for snapshot in history.snapshots
        ]
    )

    most_common_regime = max(
        regime_statistics,
        key=lambda result: (
            result.observation_count,
            result.environment_label,
        ),
    ).environment_label

    most_persistent_regime = max(
        regime_statistics,
        key=lambda result: (
            result.average_duration_observations,
            result.maximum_duration_observations,
            result.environment_label,
        ),
    ).environment_label

    transitional_observation_count = sum(
        1
        for snapshot in history.snapshots
        if is_transitional_regime(
            snapshot.environment_label
        )
    )

    transitional_coverage_ratio = round(
        transitional_observation_count
        / history.observation_count,
        4,
    )

    return EnvironmentValidationSummary(
        economy=history.economy,
        start_date=history.earliest.as_of_date,
        end_date=history.latest.as_of_date,
        observation_count=history.observation_count,
        regime_period_count=len(periods),
        unique_regime_count=len(
            regime_statistics
        ),
        average_confidence_score=(
            average_confidence_score
        ),
        average_conviction_score=(
            average_conviction_score
        ),
        most_common_regime=most_common_regime,
        most_persistent_regime=(
            most_persistent_regime
        ),
        current_regime=(
            history.latest.environment_label
        ),
        transitional_observation_count=(
            transitional_observation_count
        ),
        transitional_coverage_ratio=(
            transitional_coverage_ratio
        ),
        regime_statistics=regime_statistics,
    )
    
@dataclass(frozen=True)
class _CompletedTransition:
    """
    Internal representation of one observed regime change.
    """

    economy: str

    from_environment_label: str
    to_environment_label: str

    transition_date: date

    source_duration_observations: int

    source_confidence_score: float
    source_conviction_score: float

    pre_transition_activity_score: float
    pre_transition_inflation_score: float
    pre_transition_financial_score: float


def _extract_completed_transitions(
    history: MacroEnvironmentHistory,
) -> tuple[_CompletedTransition, ...]:
    """
    Extract transitions between consecutive completed regime periods.

    The final regime period may be current, but the transition into it is
    complete and observable. What is excluded is an imagined exit from the
    final current period.
    """

    periods = build_regime_periods(history)

    transitions: list[_CompletedTransition] = []

    for index in range(len(periods) - 1):
        source_period = periods[index]
        destination_period = periods[index + 1]

        transitions.append(
            _CompletedTransition(
                economy=history.economy,
                from_environment_label=(
                    source_period.environment_label
                ),
                to_environment_label=(
                    destination_period.environment_label
                ),
                transition_date=(
                    destination_period.start_date
                ),
                source_duration_observations=(
                    source_period.observation_count
                ),
                source_confidence_score=(
                    source_period.ending_snapshot.confidence_score
                ),
                source_conviction_score=(
                    source_period.ending_snapshot
                    .environment_conviction_score
                ),
                pre_transition_activity_score=(
                    source_period.ending_snapshot.activity_score
                ),
                pre_transition_inflation_score=(
                    source_period.ending_snapshot
                    .inflation_impulse_score
                ),
                pre_transition_financial_score=(
                    source_period.ending_snapshot
                    .financial_impulse_score
                ),
            )
        )

    return tuple(transitions)


def calculate_transition_statistics(
    history: MacroEnvironmentHistory,
) -> tuple[RegimeTransitionStatistics, ...]:
    """
    Calculate transition probabilities and pre-transition conditions.

    Probabilities are conditional on exiting the source regime:

        transition count
        -----------------
        all completed exits from source regime
    """

    completed_transitions = _extract_completed_transitions(
        history
    )

    if not completed_transitions:
        return ()

    grouped_transitions: dict[
        tuple[str, str],
        list[_CompletedTransition],
    ] = defaultdict(list)

    source_exit_counts: Counter[str] = Counter()

    for transition in completed_transitions:
        transition_key = (
            transition.from_environment_label,
            transition.to_environment_label,
        )

        grouped_transitions[transition_key].append(
            transition
        )

        source_exit_counts[
            transition.from_environment_label
        ] += 1

    statistics: list[RegimeTransitionStatistics] = []

    for (
        from_label,
        to_label,
    ), transitions in grouped_transitions.items():
        transition_dates = [
            transition.transition_date
            for transition in transitions
        ]

        duration_observations = [
            transition.source_duration_observations
            for transition in transitions
        ]

        source_confidence_scores = [
            transition.source_confidence_score
            for transition in transitions
        ]

        source_conviction_scores = [
            transition.source_conviction_score
            for transition in transitions
        ]

        activity_scores = [
            transition.pre_transition_activity_score
            for transition in transitions
        ]

        inflation_scores = [
            transition.pre_transition_inflation_score
            for transition in transitions
        ]

        financial_scores = [
            transition.pre_transition_financial_score
            for transition in transitions
        ]

        transition_count = len(transitions)
        source_exit_count = source_exit_counts[from_label]

        statistics.append(
            RegimeTransitionStatistics(
                economy=history.economy,
                from_environment_label=from_label,
                to_environment_label=to_label,
                transition_count=transition_count,
                source_exit_count=source_exit_count,
                transition_probability=round(
                    transition_count / source_exit_count,
                    4,
                ),
                first_transition_date=min(
                    transition_dates
                ),
                last_transition_date=max(
                    transition_dates
                ),
                average_source_duration_observations=(
                    _rounded_mean(
                        [
                            float(value)
                            for value
                            in duration_observations
                        ]
                    )
                ),
                median_source_duration_observations=(
                    _rounded_median(
                        [
                            float(value)
                            for value
                            in duration_observations
                        ]
                    )
                ),
                average_source_confidence_score=(
                    _rounded_mean(
                        source_confidence_scores
                    )
                ),
                average_source_conviction_score=(
                    _rounded_mean(
                        source_conviction_scores
                    )
                ),
                average_pre_transition_activity_score=(
                    _rounded_mean(
                        activity_scores
                    )
                ),
                average_pre_transition_inflation_score=(
                    _rounded_mean(
                        inflation_scores
                    )
                ),
                average_pre_transition_financial_score=(
                    _rounded_mean(
                        financial_scores
                    )
                ),
            )
        )

    return tuple(
        sorted(
            statistics,
            key=lambda result: (
                result.from_environment_label,
                -result.transition_probability,
                -result.transition_count,
                result.to_environment_label,
            ),
        )
    )


def calculate_regime_exit_statistics(
    history: MacroEnvironmentHistory,
) -> tuple[RegimeExitStatistics, ...]:
    """
    Summarize exit behavior for each regime with at least one completed exit.
    """

    transition_statistics = calculate_transition_statistics(
        history
    )

    if not transition_statistics:
        return ()

    transitions_by_source: dict[
        str,
        list[RegimeTransitionStatistics],
    ] = defaultdict(list)

    completed_transitions = _extract_completed_transitions(
        history
    )

    raw_transitions_by_source: dict[
        str,
        list[_CompletedTransition],
    ] = defaultdict(list)

    for result in transition_statistics:
        transitions_by_source[
            result.from_environment_label
        ].append(result)

    for transition in completed_transitions:
        raw_transitions_by_source[
            transition.from_environment_label
        ].append(transition)

    current_label = history.latest.environment_label

    exit_statistics: list[RegimeExitStatistics] = []

    for source_label, results in (
        transitions_by_source.items()
    ):
        raw_transitions = raw_transitions_by_source[
            source_label
        ]

        most_common = max(
            results,
            key=lambda result: (
                result.transition_count,
                result.transition_probability,
                result.to_environment_label,
            ),
        )

        exit_statistics.append(
            RegimeExitStatistics(
                economy=history.economy,
                environment_label=source_label,
                completed_exit_count=len(
                    raw_transitions
                ),
                destination_count=len(results),
                most_common_next_regime=(
                    most_common.to_environment_label
                ),
                most_common_transition_probability=(
                    most_common.transition_probability
                ),
                average_duration_before_exit_observations=(
                    _rounded_mean(
                        [
                            float(
                                transition
                                .source_duration_observations
                            )
                            for transition
                            in raw_transitions
                        ]
                    )
                ),
                average_confidence_before_exit=(
                    _rounded_mean(
                        [
                            transition
                            .source_confidence_score
                            for transition
                            in raw_transitions
                        ]
                    )
                ),
                average_conviction_before_exit=(
                    _rounded_mean(
                        [
                            transition
                            .source_conviction_score
                            for transition
                            in raw_transitions
                        ]
                    )
                ),
                current_regime=(
                    source_label == current_label
                ),
            )
        )

    return tuple(
        sorted(
            exit_statistics,
            key=lambda result: (
                -result.completed_exit_count,
                result.environment_label,
            ),
        )
    )


def build_regime_transition_summary(
    history: MacroEnvironmentHistory,
) -> RegimeTransitionSummary:
    """
    Build a complete transition summary for environment history.
    """

    periods = build_regime_periods(history)

    if len(periods) < 2:
        raise ValueError(
            "at least two regime periods are required "
            "to calculate transitions"
        )

    transition_statistics = calculate_transition_statistics(
        history
    )

    exit_statistics = calculate_regime_exit_statistics(
        history
    )

    completed_transition_count = len(periods) - 1

    most_common = max(
        transition_statistics,
        key=lambda result: (
            result.transition_count,
            result.transition_probability,
            result.from_environment_label,
            result.to_environment_label,
        ),
    )

    most_common_transition = (
        f"{most_common.from_environment_label} -> "
        f"{most_common.to_environment_label}"
    )

    return RegimeTransitionSummary(
        economy=history.economy,
        start_date=history.earliest.as_of_date,
        end_date=history.latest.as_of_date,
        regime_period_count=len(periods),
        completed_transition_count=(
            completed_transition_count
        ),
        unique_transition_count=len(
            transition_statistics
        ),
        source_regime_count=len(
            exit_statistics
        ),
        most_common_transition=(
            most_common_transition
        ),
        most_common_transition_count=(
            most_common.transition_count
        ),
        transition_statistics=(
            transition_statistics
        ),
        exit_statistics=exit_statistics,
    )