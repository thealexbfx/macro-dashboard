from __future__ import annotations

from html import escape


HELP_TEXT = {
    "confidence": (
        "How reliable the model considers the current classification "
        "based on the amount and agreement of the underlying data."
    ),
    "conviction": (
        "How strong and clear the model's current macro signals are. "
        "A lower score means the evidence is more mixed."
    ),
    "growth": (
        "Shows the current strength and direction of economic activity."
    ),
    "inflation": (
        "Shows the current strength and direction of inflation pressures."
    ),
    "labor": (
        "Shows the current strength of the jobs market."
    ),
    "liquidity": (
        "Shows whether money and financial conditions are becoming more "
        "supportive or restrictive for the economy and markets."
    ),
    "policy": (
        "Shows whether current central-bank interest-rate policy is "
        "supporting or restricting the economy."
    ),
    "liquidity_divergence": (
        "Liquidity is sending a different signal from other parts "
        "of the economy."
    ),
    "policy_inflation_gap": (
        "Inflation is changing faster than monetary policy, creating "
        "a gap between inflation conditions and the current policy stance."
    ),
    "low_conviction": (
        "The model has identified an environment, but the evidence "
        "supporting it is still mixed."
    ),
    "transitional_regime": (
        "The economy is moving between more clearly defined macro "
        "environments, so the current direction is less established."
    ),
        "policy_watch": (
        "Policy is one of the weaker parts of the current macro profile "
        "and deserves closer monitoring."
    ),
    "liquidity_watch": (
        "Liquidity is one of the weaker parts of the current macro profile "
        "and deserves closer monitoring."
    ),
    "growth_watch": (
        "Growth is one of the weaker parts of the current macro profile "
        "and deserves closer monitoring."
    ),
    "inflation_watch": (
        "Inflation conditions deserve closer monitoring because they are "
        "an important source of change in the current macro environment."
    ),
    "labor_watch": (
        "Labour conditions deserve closer monitoring because they are "
        "an important source of change in the current macro environment."
    ),
    "horizon": (
        "The period the model is looking ahead when evaluating "
        "the asset. For example, 3 Months means the research is "
        "focused on the next three months rather than today's price move."
    ),

    "macro_score": (
        "A summary of the model's directional macro view for an asset. "
        "Positive scores lean bullish, negative scores lean bearish, "
        "and scores near zero are more neutral."
    ),

    "alignment": (
        "Shows whether current market behaviour agrees with the "
        "model's macro view."
    ),

    "historical_support": (
        "Shows whether similar macro conditions in the past provide "
        "enough evidence to support the current view."
    ),

    "evidence_alignment": (
        "Shows whether the different pieces of evidence behind the "
        "research view are pointing in the same direction."
    ),

    "pricing_status": (
        "Shows whether the market appears to have already reflected "
        "the macro conditions identified by the model."
    ),

    "decision_stance": (
        "The system's current research status for an asset based on "
        "the combined macro, market and historical evidence."
    ),

    "review": (
        "Something in the evidence needs further review before the "
        "current research view should be treated as well established."
    ),

    "watch": (
        "The asset is worth monitoring, but the evidence is not yet "
        "strong enough to justify a stronger research stance."
    ),

    "ready_for_review": (
        "The available evidence is sufficiently developed for the "
        "current research idea to be reviewed in more detail."
    ),
    "model_conviction": (
        "Shows how strongly the underlying macro signals agree with "
        "one another. A lower score means the signals are more mixed."
    ),
    "overall_direction": (
        "Shows whether the combined macro environment is improving, "
        "weakening or remaining broadly stable."
    ),
    
    "current_state": (
        "Shows the current level or condition of this macro pillar "
        "based on the latest available data."
    ),

    "trend": (
        "Shows whether this pillar is improving, weakening or remaining "
        "broadly stable over time."
    ),

    "state_score": (
        "The pillar's current model score. Positive values indicate "
        "stronger or more supportive conditions, while negative values "
        "indicate weaker or more restrictive conditions."
    ),
    "primary_drivers": (
        "The macro pillars making the largest contribution to the "
        "current direction of the environment."
    ),

    "trend_score": (
        "Measures the direction and strength of recent movement in a "
        "macro pillar. Positive scores indicate improvement, while "
        "negative scores indicate deterioration."
    ),
    "regime": (
        "The macro environment classification assigned by the model "
        "for a particular observation."
    ),

    "consecutive_observations": (
        "The number of consecutive model observations that have remained "
        "in the current macro environment."
    ),

    "regime_changes": (
        "The number of times the model's macro environment classification "
        "changed across the displayed history."
    ),

    "flags": (
        "Model warnings that identify weaker, incomplete or potentially "
        "unstable evidence within a historical observation."
    ),

    "activity_impulse": (
        "The direction and strength of change in the economy's activity "
        "backdrop, primarily reflecting growth and labour conditions."
    ),

    "inflation_impulse": (
        "The direction and strength of change in inflation pressure "
        "identified by the model."
    ),

    "financial_impulse": (
        "The direction and strength of change in financial conditions, "
        "primarily reflecting liquidity and policy conditions."
    ),
    
    "regime_periods": (
        "Continuous stretches during which the model remained in the "
        "same macro environment before changing classification."
    ),

    "transitional_coverage": (
        "The share of historical observations classified as transitional "
        "rather than as a more clearly established macro environment."
    ),

    "most_persistent_regime": (
        "The macro environment that historically lasted the longest on "
        "average when it appeared."
    ),

    "annualized_transition_rate": (
        "An estimate of how many times per year the model changed from "
        "one macro environment to another."
    ),

    "churn_assessment": (
        "A summary of how frequently the model changes environment "
        "classification. Higher churn means less persistent regimes."
    ),

    "short_lived_regimes": (
        "The proportion of regime periods that ended after only a small "
        "number of model observations."
    ),

    "oscillation_ratio": (
        "The share of eligible transitions where the model moved away "
        "from a regime and then quickly returned to it."
    ),

    "confidence_before_transition": (
        "Average model confidence immediately before the environment "
        "classification changed."
    ),

    "conviction_before_transition": (
        "Average strength and agreement of the macro signals immediately "
        "before the environment classification changed."
    ),

    "confidence_drift": (
        "The average change in model confidence while a regime remained "
        "active. Positive values indicate rising confidence."
    ),

    "conviction_drift": (
        "The average change in model conviction while a regime remained "
        "active. Positive values indicate strengthening signal agreement."
    ),
    "macro_environment": (
        "The model's classification of the economic backdrop based on "
        "activity, inflation and financial conditions."
    ),

    "historical_episodes": (
        "Distinct periods in which the selected macro environment first "
        "appeared. Consecutive months in the same regime count as one episode."
    ),

    "completed_episodes": (
        "Historical episodes that subsequently ended and therefore have "
        "a recorded next macro environment."
    ),

    "best_historical_consistency": (
        "The forward horizon at which the asset produced the highest "
        "frequency of outcomes in the same direction."
    ),

    "average_outcome": (
        "The mean forward asset outcome across all distinct historical "
        "episodes for the selected horizon."
    ),

    "positive_return_frequency": (
        "The percentage of historical episodes in which the asset produced "
        "a positive forward return."
    ),

    "yield_rise_frequency": (
        "The percentage of historical episodes in which the US 10-year "
        "Treasury yield increased."
    ),

    "forward_horizon": (
        "The length of time after regime entry over which the asset outcome "
        "is measured."
    ),

    "activity_score": (
        "The model's activity reading when the historical regime first "
        "appeared. Positive values indicate stronger activity conditions."
    ),

    "inflation_score": (
        "The model's inflation reading when the historical regime first "
        "appeared. Positive values indicate stronger inflation pressure."
    ),

    "financial_score": (
        "The model's financial-conditions reading when the historical regime "
        "first appeared. Positive values indicate more supportive conditions."
    ),
}


ENVIRONMENT_HELP = {
    "Reflationary Expansion": (
        "The economy is growing while inflation is also beginning "
        "to rise."
    ),
    "Inflationary Transition": (
        "Inflation is rising, but the broader economic direction "
        "is still unclear."
    ),
    "Disinflationary Transition": (
        "Inflation is easing, but the economy has not yet moved into "
        "a clearly defined new environment."
    ),
    "Activity-Led Expansion": (
        "Economic growth is improving and is the main source of "
        "current momentum."
    ),
}


def help_text(key: str) -> str:
    normalized_key = (
        key.strip()
        .casefold()
        .replace("–", "_")
        .replace("-", "_")
        .replace(" ", "_")
    )

    return HELP_TEXT.get(
        normalized_key,
        "More information about this term will be added soon.",
    )


def environment_help(label: str) -> str:
    return ENVIRONMENT_HELP.get(
        label,
        "A summary of the current combination of growth, inflation "
        "and financial conditions.",
    )


def tooltip_html(
    label: str,
    explanation: str,
) -> str:
    return (
        '<span class="ml-help-label">'
        f'{escape(label)}'
        '</span>'
        '<span class="ml-help-anchor" tabindex="0">'
        '<span class="ml-help-icon">i</span>'
        f'<span class="ml-help-tooltip">{escape(explanation)}</span>'
        '</span>'
    )