import pandas as pd

def calculate_yoy_from_index(df):
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    df["year_ago_date"] = df["date"] - pd.DateOffset(years=1)

    year_ago = df[["date", "value"]].rename(
        columns={"date": "year_ago_date", "value": "value_year_ago"}
    )

    df = df.merge(year_ago, on="year_ago_date", how="left")
    denominator = df["value_year_ago"].where(df["value_year_ago"] > 0)
    df["value"] = (df["value"].where(df["value"] > 0) / denominator - 1) * 100

    return df[["date", "value"]].dropna().reset_index(drop=True)

def calculate_mom_pct_change(df):
    """Calendar-month growth; a missing month is not silently bridged."""
    df = df[["date", "value"]].copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date")
    periods = df.date.dt.to_period("M")
    if periods.duplicated().any():
        raise ValueError("Monthly growth requires one observation per month.")
    if df.empty:
        return df
    values = pd.Series(df.value.to_numpy(), index=periods)
    values = values.reindex(pd.period_range(periods.min(), periods.max(), freq="M"))
    values = values.where(values > 0)
    growth = values.pct_change(fill_method=None) * 100
    df["value"] = growth.reindex(periods).to_numpy()
    return df.dropna().reset_index(drop=True)

def calculate_diff(df):
    df = df.copy()
    df["value"] = df["value"].diff()
    return df[["date", "value"]].dropna().reset_index(drop=True)
