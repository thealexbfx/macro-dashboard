import numpy as np
import pandas as pd
import requests
import streamlit as st
from config import BEA_API_KEY

def get_bea_nipa_series(table_name: str, line_number: int, frequency: str = "Q"):
    """Fetch a BEA NIPA series and return date/value columns."""
    url = "https://apps.bea.gov/api/data/"

    params = {
        "UserID": BEA_API_KEY,
        "method": "GetData",
        "DataSetName": "NIPA",
        "TableName": table_name,
        "Frequency": frequency,
        "Year": "ALL",
        "ResultFormat": "JSON",
    }

    r = requests.get(url, params=params)
    r.raise_for_status()
    data = r.json()

    rows = data["BEAAPI"]["Results"]["Data"]

    df = pd.DataFrame(rows)

    df = df[df["LineNumber"].astype(int) == line_number].copy()

    df["value"] = (
        df["DataValue"]
        .astype(str)
        .str.replace(",", "", regex=False)
        .replace("(NA)", np.nan)
    )
    df["value"] = pd.to_numeric(df["value"], errors="coerce")

    def parse_bea_period(p):
        p = str(p)

        if "Q" in p:
            year = int(p[:4])
            quarter = int(p[-1])
            month = {1: 3, 2: 6, 3: 9, 4: 12}[quarter]
            return pd.Timestamp(year=year, month=month, day=1) + pd.offsets.MonthEnd(0)

        if "M" in p:
            year = int(p[:4])
            month = int(p[-2:])
            return pd.Timestamp(year=year, month=month, day=1) + pd.offsets.MonthEnd(0)

        year = int(p[:4])
        return pd.Timestamp(year=year, month=12, day=31)

    df["date"] = df["TimePeriod"].apply(parse_bea_period)

    df = df[["date", "value"]].dropna()
    df = df.sort_values("date").reset_index(drop=True)

    return df
