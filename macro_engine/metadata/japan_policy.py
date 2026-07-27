"""Indicator metadata for the Japan Policy pillar."""

from macro_engine.models.indicator import IndicatorConfig


JAPAN_POLICY_RATE = IndicatorConfig(
    indicator_id="japan_policy_rate",
    name="BOJ Policy Rate",
    economy="Japan",
    pillar="policy",
    bucket="current_policy_stance",
    frequency="monthly",
    economic_direction="negative",
    state_window=3,
    trend_window=3,
    minimum_history=36,
    source="Bank of Japan",
    unit="percent",
    description=(
        "Measures the Bank of Japan policy-rate stance. Higher rates "
        "represent tighter and less supportive monetary policy."
    ),
)