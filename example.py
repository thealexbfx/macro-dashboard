import pandas as pd
import os
import re

import pandas as pd
import os

def get_usa_core_cpi_yoy_data():
    base_dir = os.path.dirname(__file__)
    file_path = os.path.join(base_dir, "USA_Core_CPI_YoY.txt")
    
    # Read file as single columndef get_usa_core_cpi_yoy_data():
    base_dir = os.path.dirname(__file__)
    file_path = os.path.join(base_dir, "USA_Core_CPI_YoY.txt")

    # Try reading with whitespace separator
    df = pd.read_csv(file_path, sep=r"\s{2,}", engine="python", header=0)

    # Debug: show first few rows and columns
    print("Raw read:")
    print(df.head())
    print("Columns:", df.columns.tolist())

    # Clean column names
    df.columns = df.columns.str.strip()

    # Case 1: File has "Date" and "Rate" already
    if "Date" in df.columns and "Rate" in df.columns:
        df.rename(columns={"Date": "date", "Rate": "value"}, inplace=True)

    # Case 2: File only has one messy column
    else:
        col = df.columns[0]
        df[col] = df[col].astype(str)  # ensure string for regex
        df[["date", "value"]] = df[col].str.extract(r"(.+?)\s+([0-9]*\.?[0-9]+)$")
        df.drop(columns=[col], inplace=True)

    # Convert value to float
    df["value"] = pd.to_numeric(df["value"], errors="coerce")

    # Drop invalid rows
    df = df.dropna(subset=["value", "date"])

    # Convert Month Year -> datetime
    df["date"] = pd.to_datetime(df["date"], format="%B %Y", errors="coerce")

    # Drop rows with invalid dates
    df = df.dropna(subset=["date"])

    # Sort
    df = df.sort_values("date").reset_index(drop=True)

    return df
