from __future__ import annotations

from macro_engine.decision.fx_config import get_fx_config

from dataclasses import dataclass
from datetime import date, timedelta

from macro_engine.decision.cross_asset.config import (
    get_cross_asset_config,
)

import numpy as np
import pandas as pd

from data.yahoo import get_fx_data_yahoo


TRADING_DAYS_PER_YEAR = 252


@dataclass(frozen=True)
class MarketContext:
    asset: str
    ticker: str
    as_of_date: date
    current_price: float

    daily_return: float | None
    weekly_return: float | None
    monthly_return: float | None
    quarterly_return: float | None

    moving_average_20d: float | None
    moving_average_50d: float | None
    moving_average_200d: float | None

    trend_label: str
    momentum_label: str

    high_52w: float
    low_52w: float
    range_percentile_52w: float
    distance_from_high_52w: float
    distance_from_low_52w: float

    realized_volatility_20d: float | None
    volatility_label: str

    def to_text(self) -> str:
        def pct(value: float | None) -> str:
            return "N/A" if value is None else f"{value:+.2%}"

        def number(value: float | None) -> str:
            return "N/A" if value is None else f"{value:.4f}"

        return "\n".join(
            [
                f"Asset: {self.asset}",
                f"As of: {self.as_of_date}",
                f"Current price: {self.current_price:.4f}",
                "",
                "Recent performance",
                f"- Daily: {pct(self.daily_return)}",
                f"- Weekly: {pct(self.weekly_return)}",
                f"- Monthly: {pct(self.monthly_return)}",
                f"- Quarterly: {pct(self.quarterly_return)}",
                "",
                "Trend",
                f"- Trend: {self.trend_label}",
                f"- Momentum: {self.momentum_label}",
                f"- 20-day average: {number(self.moving_average_20d)}",
                f"- 50-day average: {number(self.moving_average_50d)}",
                f"- 200-day average: {number(self.moving_average_200d)}",
                "",
                "52-week position",
                f"- High: {self.high_52w:.4f}",
                f"- Low: {self.low_52w:.4f}",
                f"- Range percentile: {self.range_percentile_52w:.1%}",
                f"- Distance from high: {self.distance_from_high_52w:.2%}",
                f"- Distance from low: {self.distance_from_low_52w:.2%}",
                "",
                "Volatility",
                (
                    "- 20-day annualized volatility: "
                    f"{pct(self.realized_volatility_20d)}"
                ),
                f"- Volatility state: {self.volatility_label}",
            ]
        )


def _safe_return(
    prices: pd.Series,
    periods: int,
) -> float | None:
    if len(prices) <= periods:
        return None

    previous = float(prices.iloc[-periods - 1])
    latest = float(prices.iloc[-1])

    if previous == 0:
        return None

    return latest / previous - 1.0


def _safe_average(
    prices: pd.Series,
    window: int,
) -> float | None:
    if len(prices) < window:
        return None

    return float(prices.iloc[-window:].mean())


def _classify_trend(
    current_price: float,
    ma20: float | None,
    ma50: float | None,
    ma200: float | None,
) -> str:
    if ma20 is None or ma50 is None:
        return "Insufficient data"

    if (
        current_price > ma20
        and current_price > ma50
        and (ma200 is None or current_price > ma200)
        and ma20 > ma50
    ):
        return "Uptrend"

    if (
        current_price < ma20
        and current_price < ma50
        and (ma200 is None or current_price < ma200)
        and ma20 < ma50
    ):
        return "Downtrend"

    return "Range-bound / Mixed"


def _classify_momentum(
    monthly_return: float | None,
    quarterly_return: float | None,
) -> str:
    if monthly_return is None:
        return "Insufficient data"

    if monthly_return > 0.01 and (
        quarterly_return is None or quarterly_return > 0
    ):
        return "Bullish"

    if monthly_return < -0.01 and (
        quarterly_return is None or quarterly_return < 0
    ):
        return "Bearish"

    return "Neutral"


def _classify_volatility(
    returns: pd.Series,
    current_volatility: float | None,
) -> str:
    if current_volatility is None or len(returns) < 60:
        return "Insufficient data"

    rolling_volatility = (
        returns.rolling(20).std()
        * np.sqrt(TRADING_DAYS_PER_YEAR)
    ).dropna()

    if rolling_volatility.empty:
        return "Insufficient data"

    percentile = (
        rolling_volatility <= current_volatility
    ).mean()

    if percentile >= 0.75:
        return "High"

    if percentile <= 0.25:
        return "Low"

    return "Normal"


def build_market_context(
    *,
    asset: str,
    ticker: str,
    lookback_years: int = 3,
) -> MarketContext:
    end_date = date.today() + timedelta(days=1)
    start_date = end_date - timedelta(
        days=365 * lookback_years
    )

    data = get_fx_data_yahoo(
        ticker=ticker,
        start_date=start_date,
        end_date=end_date,
    )

    if data.empty:
        raise ValueError(
            f"No market data was returned for {asset} ({ticker})."
        )

    data = data.copy()
    data["date"] = pd.to_datetime(data["date"])
    data["value"] = pd.to_numeric(
        data["value"],
        errors="coerce",
    )

    data = (
        data.dropna(subset=["date", "value"])
        .drop_duplicates(subset=["date"], keep="last")
        .sort_values("date")
        .reset_index(drop=True)
    )

    prices = data["value"]

    if len(prices) < 30:
        raise ValueError(
            f"Not enough market history is available for {asset}."
        )

    current_price = float(prices.iloc[-1])

    daily_return = _safe_return(prices, 1)
    weekly_return = _safe_return(prices, 5)
    monthly_return = _safe_return(prices, 21)
    quarterly_return = _safe_return(prices, 63)

    ma20 = _safe_average(prices, 20)
    ma50 = _safe_average(prices, 50)
    ma200 = _safe_average(prices, 200)

    trailing_52w = prices.iloc[-252:]
    high_52w = float(trailing_52w.max())
    low_52w = float(trailing_52w.min())

    range_size = high_52w - low_52w

    if range_size == 0:
        range_percentile = 0.5
    else:
        range_percentile = (
            current_price - low_52w
        ) / range_size

    distance_from_high = (
        current_price / high_52w - 1.0
    )

    distance_from_low = (
        current_price / low_52w - 1.0
    )

    daily_returns = prices.pct_change().dropna()

    realized_volatility_20d = None

    if len(daily_returns) >= 20:
        realized_volatility_20d = float(
            daily_returns.iloc[-20:].std()
            * np.sqrt(TRADING_DAYS_PER_YEAR)
        )

    trend_label = _classify_trend(
        current_price=current_price,
        ma20=ma20,
        ma50=ma50,
        ma200=ma200,
    )

    momentum_label = _classify_momentum(
        monthly_return=monthly_return,
        quarterly_return=quarterly_return,
    )

    volatility_label = _classify_volatility(
        returns=daily_returns,
        current_volatility=realized_volatility_20d,
    )

    return MarketContext(
        asset=asset,
        ticker=ticker,
        as_of_date=data["date"].iloc[-1].date(),
        current_price=current_price,
        daily_return=daily_return,
        weekly_return=weekly_return,
        monthly_return=monthly_return,
        quarterly_return=quarterly_return,
        moving_average_20d=ma20,
        moving_average_50d=ma50,
        moving_average_200d=ma200,
        trend_label=trend_label,
        momentum_label=momentum_label,
        high_52w=high_52w,
        low_52w=low_52w,
        range_percentile_52w=float(range_percentile),
        distance_from_high_52w=float(distance_from_high),
        distance_from_low_52w=float(distance_from_low),
        realized_volatility_20d=realized_volatility_20d,
        volatility_label=volatility_label,
    )


def build_fx_market_context_for_asset(
    asset_key: str,
) -> MarketContext:
    config = get_fx_config(asset_key)

    return build_market_context(
        asset=config.display_name,
        ticker=config.ticker,
    )


def build_cross_asset_market_context(
    asset_key: str,
) -> MarketContext:
    config = get_cross_asset_config(asset_key)

    return build_market_context(
        asset=config.display_name,
        ticker=config.ticker,
    )


def build_gbpusd_market_context() -> MarketContext:
    return build_fx_market_context_for_asset(
        "gbpusd"
    )


def build_eurusd_market_context() -> MarketContext:
    return build_fx_market_context_for_asset(
        "eurusd"
    )