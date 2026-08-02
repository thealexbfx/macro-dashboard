from __future__ import annotations

from dataclasses import dataclass

from macro_engine.decision.historical_models import (
    HistoricalEvidence,
)


@dataclass(frozen=True)
class HistoricalContextItem:
    source: str
    environment: str
    observations: int
    confidence_label: str
    average_return: float | None
    median_return: float | None
    up_rate: float | None
    down_rate: float | None


@dataclass(frozen=True)
class HistoricalContext:
    horizon_months: int
    items: tuple[HistoricalContextItem, ...]
    assessment_label: str
    assessment: str

    def to_text(self) -> str:
        lines = [
            f"Historical Context — {self.horizon_months}M",
            "",
        ]

        for item in self.items:
            lines.extend(
                [
                    item.source,
                    f"Environment: {item.environment}",
                    f"Observations: {item.observations}",
                    f"Confidence: {item.confidence_label}",
                ]
            )

            if item.average_return is not None:
                lines.append(
                    f"Average return: {item.average_return:+.1%}"
                )

            if item.median_return is not None:
                lines.append(
                    f"Median return: {item.median_return:+.1%}"
                )

            if item.up_rate is not None:
                lines.append(
                    f"Positive rate: {item.up_rate:.0%}"
                )

            if item.down_rate is not None:
                lines.append(
                    f"Decline rate: {item.down_rate:.0%}"
                )

            lines.append("")

        lines.extend(
            [
                f"Assessment: {self.assessment_label}",
                self.assessment,
            ]
        )

        return "\n".join(lines)


def _confidence_label(observations: int) -> str:
    if observations >= 20:
        return "Stronger sample"

    if observations >= 10:
        return "Moderate sample"

    if observations >= 5:
        return "Limited sample"

    return "Very limited sample"


def build_historical_context(
    *,
    evidence: tuple[HistoricalEvidence, ...],
    model_direction: str,
    horizon_months: int,
    primary_name: str,
    secondary_name: str,
) -> HistoricalContext:
    items = tuple(
        HistoricalContextItem(
            source=item.source,
            environment=item.label,
            observations=item.observations,
            confidence_label=_confidence_label(
                item.observations
            ),
            average_return=item.average_return,
            median_return=item.median_return,
            up_rate=item.up_rate,
            down_rate=item.down_rate,
        )
        for item in evidence
    )

    usable_items = [
        item
        for item in evidence
        if item.observations >= 5
        and item.average_return is not None
    ]

    exact_pair = next(
        (
            item
            for item in evidence
            if item.source == "Exact environment pair history"
        ),
        None,
    )

    if exact_pair is not None and exact_pair.observations >= 5:
        assessment_label = "Direct historical evidence"
    elif usable_items:
        assessment_label = "Mixed historical evidence"
    else:
        assessment_label = "Insufficient historical evidence"

    if not usable_items:
        assessment = (
            "The available historical sample is too limited to provide "
            "meaningful support for the current macro thesis."
        )
    else:
        expected_sign = (
            -1
            if model_direction == "Bearish"
            else 1
            if model_direction == "Bullish"
            else 0
        )

        supportive = 0
        contradictory = 0

        for item in usable_items:
            historical_sign = (
                1
                if item.average_return > 0
                else -1
                if item.average_return < 0
                else 0
            )

            if historical_sign == expected_sign:
                supportive += 1
            elif (
                expected_sign != 0
                and historical_sign == -expected_sign
            ):
                contradictory += 1

        if supportive > contradictory:
            assessment = (
                "The usable historical evidence broadly supports the "
                "current macro direction, although the sample remains "
                "limited."
            )
        elif contradictory > supportive:
            assessment = (
                "The usable historical evidence modestly contradicts the "
                "current macro direction, while other samples remain too "
                "limited to draw a strong conclusion."
            )
        else:
            assessment = (
                "The usable historical evidence is mixed and does not "
                "provide a strong directional conclusion."
            )

    if exact_pair is None:
        assessment += (
            " No exact historical match is available for the current "
            f"{primary_name} and {secondary_name} environment combination."
        )

    return HistoricalContext(
        horizon_months=horizon_months,
        items=items,
        assessment_label=assessment_label,
        assessment=assessment,
    )