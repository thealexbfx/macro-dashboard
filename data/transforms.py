import pandas as pd

def calculate_yoy_from_index(df):
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    df["year_ago_date"] = df["date"] - pd.DateOffset(years=1)

    year_ago = df[["date", "value"]].rename(
        columns={"date": "year_ago_date", "value": "value_year_ago"}
    )

    df = df.merge(year_ago, on="year_ago_date", how="left")
    df["value"] = (df["value"] / df["value_year_ago"] - 1) * 100

    return df[["date", "value"]].dropna().reset_index(drop=True)

def calculate_mom_pct_change(df):
    df = df.copy()
    df["value"] = df["value"].pct_change() * 100
    return df[["date", "value"]].dropna().reset_index(drop=True)

def calculate_diff(df):
    df = df.copy()
    df["value"] = df["value"].diff()
    return df[["date", "value"]].dropna().reset_index(drop=True)
