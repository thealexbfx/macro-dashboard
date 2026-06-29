import datetime as dt
import pandas as pd
import streamlit as st

from data.yahoo import get_fx_data_yahoo


HOME_MARKET_ASSETS = {
    "DXY": "DX-Y.NYB",
    "S&P 500": "^GSPC",
    "10Y Yield": "^TNX",
    "Gold": "GC=F",
    "Bitcoin": "BTC-USD",
}


def _format_value(label, value):
    if pd.isna(value):
        return "N/A"

    if "Yield" in label:
        return f"{value:.2f}%"

    if label == "DXY":
        return f"{value:.2f}"

    if label in ["Bitcoin", "S&P 500", "Gold"]:
        return f"{value:,.0f}"

    return f"{value:,.2f}"


@st.cache_data(ttl=1800)
def get_home_market_snapshot():
    rows = []

    for label, ticker in HOME_MARKET_ASSETS.items():
        try:
            df = get_fx_data_yahoo(
                ticker,
                start_date=dt.date.today() - dt.timedelta(days=45),
                end_date=dt.date.today() + dt.timedelta(days=1),
            )

            df = df.dropna().sort_values("date")

            if len(df) < 2:
                continue

            latest = df["value"].iloc[-1]
            previous = df["value"].iloc[-2]
            first = df["value"].iloc[0]

            change_pct = ((latest / previous) - 1) * 100 if previous != 0 else 0
            trend_positive = latest >= first

            rows.append({
                "label": label,
                "value": _format_value(label, latest),
                "change_pct": change_pct,
                "trend_positive": trend_positive,
                "sparkline_df": df.tail(30),
            })

        except Exception:
            rows.append({
                "label": label,
                "value": "N/A",
                "change_pct": None,
                "trend_positive": True,
                "sparkline_df": pd.DataFrame(),
            })

    return rows


@st.cache_data(ttl=1800)
def get_biggest_movers(period="1D", lookback_days=90, top_n=8):
    period_days = {
        "1D": 1,
        "1W": 7,
        "1M": 30,
    }

    days = period_days.get(period, 1)
    rows = []

    for label, ticker in HOME_MARKET_ASSETS.items():
        try:
            df = get_fx_data_yahoo(
                ticker,
                start_date=dt.date.today() - dt.timedelta(days=lookback_days + 10),
                end_date=dt.date.today() + dt.timedelta(days=1),
            )

            df = df.dropna().sort_values("date")

            if len(df) < 35:
                continue

            latest = df["value"].iloc[-1]
            previous = df["value"].iloc[-(days + 1)]

            move_pct = ((latest / previous) - 1) * 100 if previous != 0 else 0

            df["daily_return"] = df["value"].pct_change() * 100
            recent_vol = df["daily_return"].tail(30).std()

            unusual_score = abs(move_pct / recent_vol) if recent_vol and recent_vol != 0 else 0

            rows.append({
                "Asset": label,
                "Period": period,
                "Move": move_pct,
                "Volatility Score": unusual_score,
                "Direction": "Up" if move_pct > 0 else "Down" if move_pct < 0 else "Flat",
            })

        except Exception:
            continue

    movers = pd.DataFrame(rows)

    if movers.empty:
        return movers

    return movers.sort_values("Volatility Score", ascending=False).head(top_n)