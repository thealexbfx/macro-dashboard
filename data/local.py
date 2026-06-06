import os
import pandas as pd
import streamlit as st

def load_local_macro_data(file_name, freq="monthly", value_col="Rate"):
    base_dir = os.path.dirname(__file__)
    file_path = os.path.join(base_dir, file_name)

    if freq == "daily":
        df = pd.read_csv(file_path, sep=r"\s+")
    else:
        df = pd.read_csv(file_path, sep=r"\s{2,}", engine="python")

    df.columns = df.columns.str.strip()

    if freq == "quarterly":
        df.rename(columns={"Date": "quarter", value_col: "value"}, inplace=True)

        def parse_quarter(q):
            q = str(q).strip()
            if "Q" not in q:
                return pd.NaT
            quarter, year = q.split()
            month_map = {"Q1": 3, "Q2": 6, "Q3": 9, "Q4": 12}
            month = month_map.get(quarter, 3)
            return pd.Timestamp(year=int(year), month=month, day=1) + pd.offsets.MonthEnd(0)

        df["date"] = df["quarter"].apply(parse_quarter)
        df = df[["date", "value"]]

    else:
        df.rename(columns={"Date": "date", value_col: "value"}, inplace=True)
        df["date"] = pd.to_datetime(
            df["date"],
            format="%B %Y" if freq == "monthly" else None,
            errors="coerce"
        )

    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df = df.dropna(subset=["date", "value"])
    df = df.sort_values("date").reset_index(drop=True)

    return df

def load_usa_data(file_name: str, freq: str = "monthly", date_format: str = "%B %Y"):
    """
    Generic function to load USA macro data from text files.
    
    Args:
        file_name (str): Name of the file inside project folder (e.g. 'USA_CPI_YoY.txt').
        freq (str): Frequency of the data ('daily', 'monthly', 'quarterly').
        date_format (str): Format to parse date column (default '%B %Y' for 'January 2008').
    """
    base_dir = os.path.dirname(__file__)
    file_path = os.path.join(base_dir, file_name)

    # Detect delimiter type
    if freq == "daily":
        df = pd.read_csv(file_path, sep=r"\s+")
    else:
        df = pd.read_csv(file_path, sep=r"\s{2,}", engine="python")

    # Clean column names
    df.columns = df.columns.str.strip()

    # Rename columns for consistency
    if "Rate" in df.columns:
        df.rename(columns={"Date": "date", "Rate": "value"}, inplace=True)
    else:
        df.rename(columns={"Date": "date"}, inplace=True)

    # Convert value column to float if present
    if "value" in df.columns:
        df["value"] = pd.to_numeric(df["value"], errors="coerce")

    # Handle date parsing
    if freq == "monthly":
        df["date"] = pd.to_datetime(df["date"], format=date_format, errors="coerce")
    elif freq == "quarterly":
        def parse_quarter(q):
            q = str(q).strip()
            if "Q" not in q:
                return pd.NaT
            quarter, year = q.split()
            month_map = {"Q1": 3, "Q2": 6, "Q3": 9, "Q4": 12}
            month = month_map.get(quarter, 3)
            return pd.Timestamp(year=int(year), month=month, day=1) + pd.offsets.MonthEnd(0)
        df["date"] = df["date"].apply(parse_quarter)
    else:  # daily
        df["date"] = pd.to_datetime(df["date"], errors="coerce")

    # Drop invalid rows and sort
    df = df.dropna(subset=["date"])
    if "value" in df.columns:
        df = df.dropna(subset=["value"])
    df = df.sort_values("date").reset_index(drop=True)

    return df
