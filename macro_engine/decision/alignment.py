from __future__ import annotations

from dataclasses import dataclass

from macro_engine.decision.market_context import MarketContext
from macro_engine.decision.models import ResearchIdea


@dataclass(frozen=True)
class EvidenceAlignment:
    label: str
    score: float
    macro_direction: str
    price_trend: str
    momentum: str
    summary: str


def build_evidence_alignment(
    *,
    idea: ResearchIdea,
    market: MarketContext,
) -> EvidenceAlignment:
    macro_sign = {
        "Bullish": 1,
        "Bearish": -1,
        "Neutral": 0,
    }[idea.model_direction]

    trend_sign = {
        "Uptrend": 1,
        "Downtrend": -1,
        "Range-bound / Mixed": 0,
        "Insufficient data": 0,
    }.get(market.trend_label, 0)

    momentum_sign = {
        "Bullish": 1,
        "Bearish": -1,
        "Neutral": 0,
        "Insufficient data": 0,
    }.get(market.momentum_label, 0)

    components = [
        macro_sign,
        trend_sign,
        momentum_sign,
    ]

    directional_components = [
        value for value in components if value != 0
    ]

    if not directional_components:
        return EvidenceAlignment(
            label="Insufficient",
            score=0.0,
            macro_direction=idea.model_direction,
            price_trend=market.trend_label,
            momentum=market.momentum_label,
            summary="There is not enough directional evidence to assess alignment.",
        )

    agreement_count = sum(
        value == macro_sign
        for value in directional_components
    )

    score = agreement_count / len(directional_components)

    if macro_sign == 0:
        label = "Neutral"
        summary = (
            "The macro model is neutral, so price action is not being "
            "treated as confirming or contradicting a directional thesis."
        )
    elif trend_sign == macro_sign and (
        momentum_sign in {0, macro_sign}
    ):
        label = "Confirmed"
        summary = (
            "Price trend broadly confirms the current macro direction."
        )
    elif trend_sign == -macro_sign:
        label = "Divergent"
        summary = (
            "Price trend currently moves against the macro thesis."
        )
    else:
        label = "Mixed"
        summary = (
            "Price action provides only partial confirmation of the macro thesis."
        )

    return EvidenceAlignment(
        label=label,
        score=score,
        macro_direction=idea.model_direction,
        price_trend=market.trend_label,
        momentum=market.momentum_label,
        summary=summary,
    )