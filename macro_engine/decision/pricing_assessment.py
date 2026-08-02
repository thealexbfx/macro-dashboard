from __future__ import annotations

from dataclasses import dataclass

from macro_engine.decision.alignment import EvidenceAlignment
from macro_engine.decision.market_context import MarketContext
from macro_engine.decision.models import ResearchIdea


@dataclass(frozen=True)
class MarketPricingAssessment:
    label: str
    price_behaviour: str
    interpretation: str
    conclusion: str


def build_market_pricing_assessment(
    *,
    idea: ResearchIdea,
    market: MarketContext,
    alignment: EvidenceAlignment,
) -> MarketPricingAssessment:
    if idea.model_direction == "Bearish":
        if market.trend_label == "Uptrend":
            return MarketPricingAssessment(
                label="Not Yet Confirmed",
                price_behaviour=(
                    f"{idea.asset} remains in an uptrend despite the "
                    "bearish macro backdrop."
                ),
                interpretation=(
                    "Price action suggests the market has not yet broadly "
                    "accepted the bearish macro thesis."
                ),
                conclusion=(
                    "The thesis may not yet be fully reflected in price, "
                    "but confirmation is required before taking risk."
                ),
            )

        if market.trend_label == "Downtrend":
            return MarketPricingAssessment(
                label="Partly Reflected",
                price_behaviour=(
                    f"{idea.asset} is trending lower in the same direction "
                    "as the macro thesis."
                ),
                interpretation=(
                    "The market has begun reflecting the bearish macro view."
                ),
                conclusion=(
                    "The idea has price confirmation, but the analyst should "
                    "judge whether too much of the move has already occurred."
                ),
            )

    if idea.model_direction == "Bullish":
        if market.trend_label == "Downtrend":
            return MarketPricingAssessment(
                label="Not Yet Confirmed",
                price_behaviour=(
                    f"{idea.asset} remains in a downtrend despite the "
                    "bullish macro backdrop."
                ),
                interpretation=(
                    "Price action suggests the market has not yet broadly "
                    "accepted the bullish macro thesis."
                ),
                conclusion=(
                    "The thesis may not yet be fully reflected in price, "
                    "but confirmation is required before taking risk."
                ),
            )

        if market.trend_label == "Uptrend":
            return MarketPricingAssessment(
                label="Partly Reflected",
                price_behaviour=(
                    f"{idea.asset} is trending higher in the same direction "
                    "as the macro thesis."
                ),
                interpretation=(
                    "The market has begun reflecting the bullish macro view."
                ),
                conclusion=(
                    "The idea has price confirmation, but the analyst should "
                    "judge whether too much of the move has already occurred."
                ),
            )

    return MarketPricingAssessment(
        label="Unclear",
        price_behaviour=(
            f"{idea.asset} currently shows mixed or range-bound price action."
        ),
        interpretation=(
            "The market is not providing a clear directional pricing signal."
        ),
        conclusion=(
            "More evidence is required before judging whether the macro "
            "thesis is reflected in price."
        ),
    )