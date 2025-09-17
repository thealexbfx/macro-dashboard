import streamlit as st
import pandas as pd
import plotly.express as px
import datetime as dt
import requests
import io
import numpy as np
import csv
from urllib.parse import urljoin
from io import BytesIO
from datetime import datetime
from dateutil.parser import parse
import gzip
import yfinance as yf
from dotenv import load_dotenv
import os
import plotly.graph_objects as go
import streamlit.components.v1 as components
import calendar


def analyze_series(df: pd.DataFrame, window: int = 12):
    """
    Compute statistical, trend, and regime metrics for a macro series.

    Args:
        df (pd.DataFrame): Must contain 'date' and 'value'.
        window (int): Rolling window for slope/trend (default 12 for 1 year if monthly).

    Returns:
        dict: Dictionary of key metrics
    """
    if df.empty or "value" not in df.columns:
        return {}

    latest_value = df["value"].iloc[-1]
    hist_mean = df["value"].mean()
    hist_std = df["value"].std()
    z_score = (latest_value - hist_mean) / hist_std if hist_std != 0 else np.nan
    percentile = (df["value"] <= latest_value).mean() * 100  # percentile rank

    # Rolling slope (trend)
    if len(df) >= window:
        y = df["value"].iloc[-window:]
        x = np.arange(len(y))
        slope = np.polyfit(x, y, 1)[0]  # slope of linear regression
        rolling_vol = y.pct_change().rolling(window=window).std().iloc[-1] * 100  # % vol
    else:
        slope = np.nan
        rolling_vol = np.nan

    # YoY or MoM change (last period vs previous same period)
    if len(df) > 1:
        yoy_change = latest_value - df["value"].iloc[-2]
    else:
        yoy_change = np.nan

    # Regime classification based on z-score
    if abs(z_score) < 1:
        regime = "Normal"
    elif abs(z_score) < 2:
        regime = "Elevated"
    else:
        regime = "Extreme"

    return {
        "latest_value": latest_value,
        "hist_mean": hist_mean,
        "hist_std": hist_std,
        "z_score": z_score,
        "percentile": percentile,
        "trend_slope": slope,
        "yoy_change": yoy_change,
        "rolling_vol": rolling_vol,
        "regime": regime,
        "obs_count": len(df)
    }

def simulate_scenario(df: pd.DataFrame, shock_value: float, shock_type: str = "absolute", periods: int = 12):
    """
    Simulate a macro scenario by applying a shock to the last value of a series
    and projecting it forward.

    Args:
        df (pd.DataFrame): Must contain 'date' and 'value' columns.
        shock_value (float): Amount of shock (absolute or percent).
        shock_type (str): "absolute" or "percent".
        periods (int): Number of periods to project forward.

    Returns:
        pd.DataFrame: Projected series with dates extended.
    """
    if df.empty or "value" not in df.columns:
        return pd.DataFrame(columns=["date", "value"])

    last_value = df["value"].iloc[-1]

    # Determine projected values
    proj_values = []
    for i in range(periods):
        if shock_type == "absolute":
            last_value = last_value + shock_value
        elif shock_type == "percent":
            last_value = last_value * (1 + shock_value / 100)
        proj_values.append(last_value)

    # Create projected dates
    last_date = df["date"].iloc[-1]
    # Determine frequency (monthly or quarterly)
    if df["date"].diff().median().days >= 80:  # approx quarterly
        freq = 'Q'
    else:
        freq = 'M'
    proj_dates = pd.date_range(start=last_date + pd.offsets.MonthBegin(1), periods=periods, freq=freq)

    df_proj = pd.DataFrame({"date": proj_dates, "value": proj_values})
    return df_proj


# -------- Helper Functions --------
def plot_chart(df, title, chart_type, height=450, date_format="daily",
               yaxis_suffix='', reference_lines=None, shaded_regions=None,
               tickformat_override=None, hover_style="delta", delta_type="cumulative", show_markers=False):

    df = df.copy()
    chart_color = '#1f77b4'

    # -------------------- Hover Formatting --------------------
    if date_format == "daily":
        hover_date_format = "%d %B %Y"
    elif date_format == "monthly":
        hover_date_format = "%B %Y"
    elif date_format == "quarterly":
        # handled separately inside hover_style
        hover_date_format = None
    else:
        hover_date_format = "%Y-%m-%d"

    # -------------------- Chart Type --------------------
    mode = 'lines+markers' if show_markers else 'lines'
    if chart_type == "Line":
        fig = px.line(df, x='date', y='value', title=title, labels={'date': '', 'value': ''}, height=height)
        fig.update_traces(line=dict(width=2, color=chart_color), mode=mode)
    elif chart_type == "Step":
        fig = px.line(df, x='date', y='value', title=title, labels={'date': '', 'value': ''}, height=height)
        fig.update_traces(line_shape='hv', line=dict(width=2, color=chart_color), mode=mode)
    elif chart_type == "Area":
        fig = px.area(df, x='date', y='value', title=title, labels={'date': '', 'value': ''}, height=height)
        fig.update_traces(line_color=chart_color, fillcolor='rgba(31,119,180,0.3)')
    elif chart_type == "Bar":
        fig = px.bar(df, x='date', y='value', title=title, labels={'date': '', 'value': ''}, height=height)
        fig.update_traces(marker_color=chart_color, marker_line_color='black', marker_line_width=1)
    else:
        raise ValueError(f"Unsupported chart_type: {chart_type}")

    # -------------------- Layout --------------------
    fig.update_layout(
        margin=dict(l=40, r=30, t=60, b=20),
        hovermode='closest',
        dragmode=False,
        title=dict(font=dict(size=20, family="Arial Bold"), x=0.5, xanchor='center'),
        xaxis=dict(
            showgrid=False,
            showline=True,
            linecolor='black',
            linewidth=2,
            ticks='outside',
            ticklen=10,
            tickwidth=2,
            tickfont=dict(size=14, family="Arial Bold", color="black")
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor='LightGrey',
            gridwidth=0.3,
            showline=True,
            linecolor='black',
            linewidth=2,
            ticks='outside',
            tickfont=dict(size=14, family="Arial Bold", color="black"),
            tickformat=f',.2f{yaxis_suffix}'
        ),
        hoverlabel=dict(
            font_size=16,
            bgcolor="#F9F9F9",  # Updated hover box color
            bordercolor="black",
            align="left",
            namelength=0
        )
    )

    # -------------------- Reference Lines --------------------
    if reference_lines:
        for ref in reference_lines:
            fig.add_hline(y=ref['value'], line_dash='dash', line_color='red',
                          annotation_text=ref.get('label', ''),
                          annotation_position="top left",
                          annotation_font=dict(size=12, color='red'))

    # -------------------- Shaded Regions --------------------
    if shaded_regions:
        for region in shaded_regions:
            fig.add_vrect(x0=region['start'], x1=region['end'],
                          fillcolor=region.get('color', 'LightGrey'),
                          opacity=region.get('opacity', 0.3),
                          layer="below",
                          line_width=0)

    # -------------------- Hover Styles --------------------
    if hover_style == "delta":
        if delta_type == "daily":
            df['delta'] = df['value'].pct_change() * 100
        else:  # cumulative
            df['delta'] = (df['value'] / df['value'].iloc[0] - 1) * 100

        df['delta_str'] = df['delta'].apply(
            lambda x: f"▲ {x:.2f}%" if x > 0 else (
                f"▼ {abs(x):.2f}%" if pd.notnull(x) and x < 0 else "— 0.00%"
            )
        )
        df['delta_color'] = df['delta'].apply(
            lambda x: "green" if x > 0 else ("red" if x < 0 else "gray")
        )

        if date_format == "quarterly":
            # Quarterly: use custom Q labels
            df['hover_label'] = df['date'].dt.to_period('Q').apply(lambda x: f"Q{x.quarter} {x.year}")
            fig.update_traces(
                customdata=df[['hover_label', 'delta_str', 'delta_color']],
                hovertemplate=(
                    "<span style='color:black'><b>%{customdata[0]}</b></span><br>"   # Quarter
                    "<span style='color:black'>%{y:,.2f}" + yaxis_suffix + "</span><br>"  # Value
                    "<span style='color:%{customdata[2]}; font-weight:bold'>%{customdata[1]}</span>"
                    "<extra></extra>"
                )
            )
        else:
            # Daily/Monthly/Yearly
            fig.update_traces(
                customdata=df[['delta_str', 'delta_color']],
                hovertemplate=(
                    "<span style='color:black'><b>%{x|" + hover_date_format + "}</b></span><br>"
                    "<span style='color:black'>%{y:,.2f}" + yaxis_suffix + "</span><br>"
                    "<span style='color:%{customdata[1]}; font-weight:bold'>%{customdata[0]}</span>"
                    "<extra></extra>"
                )
            )

    else:
        if date_format == "quarterly":
            df['hover_label'] = df['date'].dt.to_period('Q').apply(lambda x: f"Q{x.quarter} {x.year}")
            fig.update_traces(
                customdata=df['hover_label'],
                hovertemplate="<b>%{customdata}</b><br>%{y:,.2f}" + yaxis_suffix + "<extra></extra>"
            )
            tickvals = df[df['date'].dt.quarter == 4]['date']
            ticktext = df[df['date'].dt.quarter == 4]['hover_label']
            fig.update_xaxes(tickmode='array', tickvals=tickvals, ticktext=ticktext)
        else:
            hovertemplate = (
                "<b>%{x|" + hover_date_format + "}</b><br>"
                "%{y:,.2f}" + yaxis_suffix + "<extra></extra>"
            )
            fig.update_traces(hovertemplate=hovertemplate)

            if tickformat_override:
                df['tick_label'] = df['date'].dt.strftime(tickformat_override)
                fig.update_xaxes(
                    tickmode='array',
                    tickvals=df['date'],
                    ticktext=df['tick_label']
                )

    return fig
    
@st.cache_data
def get_japan_interest_rate_data():
    base_dir = os.path.dirname(__file__)
    file_path = os.path.join(base_dir, "Japan_Interest_Rate.txt")
    
    # Use whitespace delimiter for space/tab-separated file
    df = pd.read_csv(file_path, delim_whitespace=True)

    # Strip column names to remove hidden spaces
    df.columns = df.columns.str.strip()

    # Rename for consistency
    df.rename(columns={"Date": "date", "Rate": "value"}, inplace=True)

    # Convert date column to datetime
    df['date'] = pd.to_datetime(df['date'], errors='coerce')

    # Drop any rows where date could not be parsed
    df = df.dropna(subset=['date'])

    # Sort by date
    df = df.sort_values("date").reset_index(drop=True)

    return df

@st.cache_data    
def get_japan_cpi_yoy_data():
    base_dir = os.path.dirname(__file__)
    file_path = os.path.join(base_dir, "Japan_CPI_YoY.txt")
    
    # Read using regex for 2+ spaces
    df = pd.read_csv(file_path, sep=r"\s{2,}", engine="python")

    # Clean column names
    df.columns = df.columns.str.strip()

    # Rename columns for consistency
    df.rename(columns={"Date": "date", "Rate": "value"}, inplace=True)

    # Convert value to float
    df['value'] = pd.to_numeric(df['value'], errors='coerce')

    # Drop invalid rows
    df = df.dropna(subset=['value'])

    # Convert Month Year to datetime
    df['date'] = pd.to_datetime(df['date'], format="%B %Y", errors='coerce')

    # Drop rows with invalid dates
    df = df.dropna(subset=['date'])

    # Sort by date
    df = df.sort_values("date").reset_index(drop=True)

    return df
    
@st.cache_data    
def get_japan_gdp_qoq_data():
    base_dir = os.path.dirname(__file__)
    file_path = os.path.join(base_dir, "Japan_GDP_Growth_Rate_QoQ.txt")
    
    # Read the file (split on 2+ spaces, so "Q1 2008" stays together)
    df = pd.read_csv(file_path, sep=r"\s{2,}", engine="python")

    # Clean up column names
    df.columns = df.columns.str.strip()

    # Rename for consistency
    df.rename(columns={"Date": "quarter", "Rate": "value"}, inplace=True)

    # Function to convert "Q1 2008" -> datetime (end of quarter)
    def parse_quarter(q):
        q = str(q).strip()
        if "Q" not in q:
            return pd.NaT
        quarter, year = q.split()
        month_map = {"Q1": 3, "Q2": 6, "Q3": 9, "Q4": 12}
        month = month_map.get(quarter, 3)
        return pd.Timestamp(year=int(year), month=month, day=1) + pd.offsets.MonthEnd(0)

    df["date"] = df["quarter"].apply(parse_quarter)

    # Keep only relevant columns
    df = df[["date", "value"]]

    # Convert value to numeric
    df["value"] = pd.to_numeric(df["value"], errors="coerce")

    # Drop invalid rows
    df = df.dropna(subset=["date", "value"]).sort_values("date").reset_index(drop=True)

    return df
    
@st.cache_data    
def get_japan_unemployment_rate_data():
    base_dir = os.path.dirname(__file__)
    file_path = os.path.join(base_dir, "Japan_Unemployment_Rate.txt")
    
    # Read using regex for 2+ spaces
    df = pd.read_csv(file_path, sep=r"\s{2,}", engine="python")

    # Clean column names
    df.columns = df.columns.str.strip()

    # Rename columns for consistency
    df.rename(columns={"Date": "date", "Rate": "value"}, inplace=True)

    # Convert value to float
    df['value'] = pd.to_numeric(df['value'], errors='coerce')

    # Drop invalid rows
    df = df.dropna(subset=['value'])

    # Convert Month Year to datetime
    df['date'] = pd.to_datetime(df['date'], format="%B %Y", errors='coerce')

    # Drop rows with invalid dates
    df = df.dropna(subset=['date'])

    # Sort by date
    df = df.sort_values("date").reset_index(drop=True)

    return df

@st.cache_data    
def get_japan_10yr_yield_data():
    base_dir = os.path.dirname(__file__)
    file_path = os.path.join(base_dir, "Japan_10_Year_Yield.txt")
        
    # Read tab or whitespace-delimited file
    df = pd.read_csv(file_path, delim_whitespace=True)

    # Strip column names
    df.columns = df.columns.str.strip()

    # Rename for consistency
    df.rename(columns={"Date": "date", "Price": "value"}, inplace=True)

    # Convert date to datetime
    df["date"] = pd.to_datetime(df["date"], errors="coerce")

    # Drop invalid dates
    df = df.dropna(subset=["date"])

    # Ensure value is numeric
    df["value"] = pd.to_numeric(df["value"], errors="coerce")

    # Drop rows with missing values
    df = df.dropna(subset=["value"])

    # Sort by date
    df = df.sort_values("date").reset_index(drop=True)

    return df

@st.cache_data    
def get_japan_2yr_yield_data():
    base_dir = os.path.dirname(__file__)
    file_path = os.path.join(base_dir, "Japan_2_Year_Yield.txt")
        
    # Read tab or whitespace-delimited file
    df = pd.read_csv(file_path, delim_whitespace=True)

    # Strip column names
    df.columns = df.columns.str.strip()

    # Rename for consistency
    df.rename(columns={"Date": "date", "Price": "value"}, inplace=True)

    # Convert date to datetime
    df["date"] = pd.to_datetime(df["date"], errors="coerce")

    # Drop invalid dates
    df = df.dropna(subset=["date"])

    # Ensure value is numeric
    df["value"] = pd.to_numeric(df["value"], errors="coerce")

    # Drop rows with missing values
    df = df.dropna(subset=["value"])

    # Sort by date
    df = df.sort_values("date").reset_index(drop=True)

    return df

@st.cache_data
def get_uk_interest_rate_data():
    base_dir = os.path.dirname(__file__)
    file_path = os.path.join(base_dir, "UK_Interest_Rate.txt")
    
    # Use whitespace delimiter for space/tab-separated file
    df = pd.read_csv(file_path, delim_whitespace=True)

    # Strip column names to remove hidden spaces
    df.columns = df.columns.str.strip()

    # Rename for consistency
    df.rename(columns={"Date": "date", "Rate": "value"}, inplace=True)

    # Convert date column to datetime
    df['date'] = pd.to_datetime(df['date'], errors='coerce')

    # Drop any rows where date could not be parsed
    df = df.dropna(subset=['date'])

    # Sort by date
    df = df.sort_values("date").reset_index(drop=True)

    return df

@st.cache_data    
def get_uk_cpi_yoy_data():
    base_dir = os.path.dirname(__file__)
    file_path = os.path.join(base_dir, "UK_CPI_YoY.txt")
    
    # Read using regex for 2+ spaces
    df = pd.read_csv(file_path, sep=r"\s{2,}", engine="python")

    # Clean column names
    df.columns = df.columns.str.strip()

    # Rename columns for consistency
    df.rename(columns={"Date": "date", "Rate": "value"}, inplace=True)

    # Convert value to float
    df['value'] = pd.to_numeric(df['value'], errors='coerce')

    # Drop invalid rows
    df = df.dropna(subset=['value'])

    # Convert Month Year to datetime
    df['date'] = pd.to_datetime(df['date'], format="%B %Y", errors='coerce')

    # Drop rows with invalid dates
    df = df.dropna(subset=['date'])

    # Sort by date
    df = df.sort_values("date").reset_index(drop=True)

    return df

@st.cache_data    
def get_uk_gdp_qoq_data():
    base_dir = os.path.dirname(__file__)
    file_path = os.path.join(base_dir, "UK_GDP_Growth_Rate_QoQ.txt")
    
    # Read the file (split on 2+ spaces, so "Q1 2008" stays together)
    df = pd.read_csv(file_path, sep=r"\s{2,}", engine="python")

    # Clean up column names
    df.columns = df.columns.str.strip()

    # Rename for consistency
    df.rename(columns={"Date": "quarter", "Rate": "value"}, inplace=True)

    # Function to convert "Q1 2008" -> datetime (end of quarter)
    def parse_quarter(q):
        q = str(q).strip()
        if "Q" not in q:
            return pd.NaT
        quarter, year = q.split()
        month_map = {"Q1": 3, "Q2": 6, "Q3": 9, "Q4": 12}
        month = month_map.get(quarter, 3)
        return pd.Timestamp(year=int(year), month=month, day=1) + pd.offsets.MonthEnd(0)

    df["date"] = df["quarter"].apply(parse_quarter)

    # Keep only relevant columns
    df = df[["date", "value"]]

    # Convert value to numeric
    df["value"] = pd.to_numeric(df["value"], errors="coerce")

    # Drop invalid rows
    df = df.dropna(subset=["date", "value"]).sort_values("date").reset_index(drop=True)

    return df

@st.cache_data    
def get_uk_unemployment_rate_data():
    base_dir = os.path.dirname(__file__)
    file_path = os.path.join(base_dir, "UK_Unemployment_Rate.txt")
    
    # Read using regex for 2+ spaces
    df = pd.read_csv(file_path, sep=r"\s{2,}", engine="python")

    # Clean column names
    df.columns = df.columns.str.strip()

    # Rename columns for consistency
    df.rename(columns={"Date": "date", "Rate": "value"}, inplace=True)

    # Convert value to float
    df['value'] = pd.to_numeric(df['value'], errors='coerce')

    # Drop invalid rows
    df = df.dropna(subset=['value'])

    # Convert Month Year to datetime
    df['date'] = pd.to_datetime(df['date'], format="%B %Y", errors='coerce')

    # Drop rows with invalid dates
    df = df.dropna(subset=['date'])

    # Sort by date
    df = df.sort_values("date").reset_index(drop=True)

    return df

@st.cache_data    
def get_uk_10yr_yield_data():
    base_dir = os.path.dirname(__file__)
    file_path = os.path.join(base_dir, "UK_10_Year_Yield.txt")
        
    # Read tab or whitespace-delimited file
    df = pd.read_csv(file_path, delim_whitespace=True)

    # Strip column names
    df.columns = df.columns.str.strip()

    # Rename for consistency
    df.rename(columns={"Date": "date", "Price": "value"}, inplace=True)

    # Convert date to datetime
    df["date"] = pd.to_datetime(df["date"], errors="coerce")

    # Drop invalid dates
    df = df.dropna(subset=["date"])

    # Ensure value is numeric
    df["value"] = pd.to_numeric(df["value"], errors="coerce")

    # Drop rows with missing values
    df = df.dropna(subset=["value"])

    # Sort by date
    df = df.sort_values("date").reset_index(drop=True)

    return df

@st.cache_data    
def get_uk_2yr_yield_data():
    base_dir = os.path.dirname(__file__)
    file_path = os.path.join(base_dir, "UK_2_Year_Yield.txt")
        
    # Read tab or whitespace-delimited file
    df = pd.read_csv(file_path, delim_whitespace=True)

    # Strip column names
    df.columns = df.columns.str.strip()

    # Rename for consistency
    df.rename(columns={"Date": "date", "Price": "value"}, inplace=True)

    # Convert date to datetime
    df["date"] = pd.to_datetime(df["date"], errors="coerce")

    # Drop invalid dates
    df = df.dropna(subset=["date"])

    # Ensure value is numeric
    df["value"] = pd.to_numeric(df["value"], errors="coerce")

    # Drop rows with missing values
    df = df.dropna(subset=["value"])

    # Sort by date
    df = df.sort_values("date").reset_index(drop=True)

    return df

@st.cache_data    
def get_euro_interest_rate_data():
    base_dir = os.path.dirname(__file__)
    file_path = os.path.join(base_dir, "EURO_Interest_Rate.txt")
    
    # Use whitespace delimiter for space/tab-separated file
    df = pd.read_csv(file_path, delim_whitespace=True)

    # Strip column names to remove hidden spaces
    df.columns = df.columns.str.strip()

    # Rename for consistency
    df.rename(columns={"Date": "date", "Rate": "value"}, inplace=True)

    # Convert date column to datetime
    df['date'] = pd.to_datetime(df['date'], errors='coerce')

    # Drop any rows where date could not be parsed
    df = df.dropna(subset=['date'])

    # Sort by date
    df = df.sort_values("date").reset_index(drop=True)

    return df

@st.cache_data    
def get_euro_cpi_yoy_data():
    base_dir = os.path.dirname(__file__)
    file_path = os.path.join(base_dir, "EURO_CPI_YoY.txt")
    
    # Read using regex for 2+ spaces
    df = pd.read_csv(file_path, sep=r"\s{2,}", engine="python")

    # Clean column names
    df.columns = df.columns.str.strip()

    # Rename columns for consistency
    df.rename(columns={"Date": "date", "Rate": "value"}, inplace=True)

    # Convert value to float
    df['value'] = pd.to_numeric(df['value'], errors='coerce')

    # Drop invalid rows
    df = df.dropna(subset=['value'])

    # Convert Month Year to datetime
    df['date'] = pd.to_datetime(df['date'], format="%B %Y", errors='coerce')

    # Drop rows with invalid dates
    df = df.dropna(subset=['date'])

    # Sort by date
    df = df.sort_values("date").reset_index(drop=True)

    return df

@st.cache_data    
def get_euro_gdp_qoq_data():
    base_dir = os.path.dirname(__file__)
    file_path = os.path.join(base_dir, "EURO_GDP_Growth_Rate_QoQ.txt")
    
    # Read the file (split on 2+ spaces, so "Q1 2008" stays together)
    df = pd.read_csv(file_path, sep=r"\s{2,}", engine="python")

    # Clean up column names
    df.columns = df.columns.str.strip()

    # Rename for consistency
    df.rename(columns={"Date": "quarter", "Rate": "value"}, inplace=True)

    # Function to convert "Q1 2008" -> datetime (end of quarter)
    def parse_quarter(q):
        q = str(q).strip()
        if "Q" not in q:
            return pd.NaT
        quarter, year = q.split()
        month_map = {"Q1": 3, "Q2": 6, "Q3": 9, "Q4": 12}
        month = month_map.get(quarter, 3)
        return pd.Timestamp(year=int(year), month=month, day=1) + pd.offsets.MonthEnd(0)

    df["date"] = df["quarter"].apply(parse_quarter)

    # Keep only relevant columns
    df = df[["date", "value"]]

    # Convert value to numeric
    df["value"] = pd.to_numeric(df["value"], errors="coerce")

    # Drop invalid rows
    df = df.dropna(subset=["date", "value"]).sort_values("date").reset_index(drop=True)

    return df

@st.cache_data    
def get_euro_unemployment_rate_data():
    base_dir = os.path.dirname(__file__)
    file_path = os.path.join(base_dir, "EURO_Unemployment_Rate.txt")
    
    # Read using regex for 2+ spaces
    df = pd.read_csv(file_path, sep=r"\s{2,}", engine="python")

    # Clean column names
    df.columns = df.columns.str.strip()

    # Rename columns for consistency
    df.rename(columns={"Date": "date", "Rate": "value"}, inplace=True)

    # Convert value to float
    df['value'] = pd.to_numeric(df['value'], errors='coerce')

    # Drop invalid rows
    df = df.dropna(subset=['value'])

    # Convert Month Year to datetime
    df['date'] = pd.to_datetime(df['date'], format="%B %Y", errors='coerce')

    # Drop rows with invalid dates
    df = df.dropna(subset=['date'])

    # Sort by date
    df = df.sort_values("date").reset_index(drop=True)

    return df

@st.cache_data   
def get_euro_10yr_yield_data():
    base_dir = os.path.dirname(__file__)
    file_path = os.path.join(base_dir, "EURO_10_Year_Yield.txt")
        
    # Read tab or whitespace-delimited file
    df = pd.read_csv(file_path, delim_whitespace=True)

    # Strip column names
    df.columns = df.columns.str.strip()

    # Rename for consistency
    df.rename(columns={"Date": "date", "Price": "value"}, inplace=True)

    # Convert date to datetime
    df["date"] = pd.to_datetime(df["date"], errors="coerce")

    # Drop invalid dates
    df = df.dropna(subset=["date"])

    # Ensure value is numeric
    df["value"] = pd.to_numeric(df["value"], errors="coerce")

    # Drop rows with missing values
    df = df.dropna(subset=["value"])

    # Sort by date
    df = df.sort_values("date").reset_index(drop=True)

    return df

@st.cache_data    
def get_euro_2yr_yield_data():
    base_dir = os.path.dirname(__file__)
    file_path = os.path.join(base_dir, "EURO_2_Year_Yield.txt")
        
    # Read tab or whitespace-delimited file
    df = pd.read_csv(file_path, delim_whitespace=True)

    # Strip column names
    df.columns = df.columns.str.strip()

    # Rename for consistency
    df.rename(columns={"Date": "date", "Price": "value"}, inplace=True)

    # Convert date to datetime
    df["date"] = pd.to_datetime(df["date"], errors="coerce")

    # Drop invalid dates
    df = df.dropna(subset=["date"])

    # Ensure value is numeric
    df["value"] = pd.to_numeric(df["value"], errors="coerce")

    # Drop rows with missing values
    df = df.dropna(subset=["value"])

    # Sort by date
    df = df.sort_values("date").reset_index(drop=True)

    return df
    
# ---------------------------
# Generic USA Data Loader
# ---------------------------
@st.cache_data
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
        df = pd.read_csv(file_path, delim_whitespace=True)
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


# ---------------------------
# Indicator-Specific Wrappers
# ---------------------------
@st.cache_data
def get_usa_interest_rate_data():
    return load_usa_data("USA_Interest_Rate.txt", freq="daily")
@st.cache_data
def get_usa_cpi_yoy_data():
    return load_usa_data("USA_CPI_YoY.txt", freq="monthly", date_format="%B %Y")
@st.cache_data
def get_usa_gdp_qoq_data():
    return load_usa_data("USA_GDP_Growth_Rate_QoQ.txt", freq="quarterly")
@st.cache_data
def get_usa_unemployment_rate_data():
    return load_usa_data("USA_Unemployment_Rate.txt", freq="monthly", date_format="%B %Y")
@st.cache_data
def get_usa_core_cpi_yoy_data():
    return load_usa_data("USA_Core_CPI_YoY.txt", freq="monthly", date_format="%B %Y")
@st.cache_data
def get_usa_average_hourly_earnings_yoy_data():
    return load_usa_data("USA_Average_Hourly_Earnings_YoY.txt", freq="monthly", date_format="%B %Y")
@st.cache_data
def get_usa_core_pce_yoy_data():
    return load_usa_data("USA_Core_PCE_YoY.txt", freq="monthly", date_format="%B %Y")
@st.cache_data
def get_usa_core_ppi_yoy_data():
    return load_usa_data("USA_Core_PPI_YoY.txt", freq="monthly", date_format="%B %Y")
@st.cache_data
def get_usa_housing_starts_mom_data():
    return load_usa_data("USA_Housing_Starts_MoM.txt", freq="monthly", date_format="%B %Y")
@st.cache_data
def get_usa_ism_manufacturing_pmi_data():
    return load_usa_data("USA_ISM_Manufacturing_PMI.txt", freq="monthly", date_format="%B %Y")
@st.cache_data    
def get_usa_ism_services_pmi_data():
    return load_usa_data("USA_ISM_Services_PMI.txt", freq="monthly", date_format="%B %Y")
@st.cache_data
def get_usa_jolts_job_openings_data():
    return load_usa_data("USA_JOLTS_Job_Openings.txt", freq="monthly", date_format="%B %Y")
@st.cache_data
def get_usa_michigan_consumer_sentiment_data():
    return load_usa_data("USA_Michigan_Consumer_Sentiment_Index.txt", freq="monthly", date_format="%B %Y")
@st.cache_data    
def get_usa_nfp_data():
    return load_usa_data("USA_NFP.txt", freq="monthly", date_format="%B %Y")
@st.cache_data    
def get_usa_pce_yoy_data():
    return load_usa_data("USA_PCE_YoY.txt", freq="monthly", date_format="%B %Y")
@st.cache_data    
def get_usa_ppi_yoy_data():
    return load_usa_data("USA_PPI_YoY.txt", freq="monthly", date_format="%B %Y")    
@st.cache_data   
def get_usa_retail_sales_mom_data():
    return load_usa_data("USA_Retail_Sales_MoM.txt", freq="monthly", date_format="%B %Y")
@st.cache_data   
def get_usa_trade_balance_data():
    return load_usa_data("USA_Trade_Balance.txt", freq="monthly", date_format="%B %Y")
    
# ---------------------------
# FRED API Setup
# ---------------------------
FRED_API_KEY = "3be1b836ee6f78badf0f0a5a4905ab73"   # <- put your key here once

# ---------------------------
# Yield Data Functions
# ---------------------------

@st.cache_data
def get_usa_yield_data(series_id: str):
    """Generic function to fetch US Treasury yields from FRED by series_id."""
    url = "https://api.stlouisfed.org/fred/series/observations"
    params = {
        "series_id": series_id,
        "api_key": FRED_API_KEY,
        "file_type": "json",
    }
    r = requests.get(url, params=params)
    r.raise_for_status()
    data = r.json()

    df = pd.DataFrame(data["observations"])
    df = df[["date", "value"]]
    df["date"] = pd.to_datetime(df["date"])
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df = df.dropna().sort_values("date").reset_index(drop=True)
    return df

# ---------------------------
# Specific US Treasury Yields
# ---------------------------
@st.cache_data
def get_usa_1mo_yield_data():
    return get_usa_yield_data("DGS1MO")
@st.cache_data
def get_usa_3mo_yield_data():
    return get_usa_yield_data("DGS3MO")
@st.cache_data
def get_usa_6mo_yield_data():
    return get_usa_yield_data("DGS6MO")
@st.cache_data
def get_usa_1yr_yield_data():
    return get_usa_yield_data("DGS1")
@st.cache_data
def get_usa_2yr_yield_data():
    return get_usa_yield_data("DGS2")
@st.cache_data
def get_usa_3yr_yield_data():
    return get_usa_yield_data("DGS3")
@st.cache_data
def get_usa_5yr_yield_data():
    return get_usa_yield_data("DGS5")
@st.cache_data
def get_usa_7yr_yield_data():
    return get_usa_yield_data("DGS7")
@st.cache_data
def get_usa_10yr_yield_data():
    return get_usa_yield_data("DGS10")
@st.cache_data
def get_usa_20yr_yield_data():
    return get_usa_yield_data("DGS20")
@st.cache_data
def get_usa_30yr_yield_data():
    return get_usa_yield_data("DGS30")

@st.cache_data
def get_fx_data_yahoo(ticker="GBPUSD=X", start_date=None, end_date=None):
    # Download historical daily data from yfinance
    data = yf.download(ticker, start=start_date, end=end_date, interval="1d", auto_adjust=False)

    if data.empty:
        return pd.DataFrame()  # Return empty DF on failure

    # If multi-index columns, select 'Close' price properly
    if isinstance(data.columns, pd.MultiIndex):
        close_data = data['Close'][ticker]
    else:
        close_data = data['Close']

    # Prepare dataframe with date and close price
    df = pd.DataFrame({
        'date': close_data.index,
        'value': close_data.values
    })

    df = df.sort_values('date').reset_index(drop=True)
    return df
    
@st.cache_data
def prepare_df(df: pd.DataFrame, label: str) -> pd.DataFrame:
    """Standardize DataFrame for Compare tab by ensuring 'Date' and 'Value_label'."""
    df = df.copy()

    # Detect date column
    date_col = None
    for candidate in ["Date", "date", "Quarter", "Time", "Datetime", "Index"]:
        if candidate in df.columns:
            date_col = candidate
            break
    if date_col is None:
        raise ValueError(f"No date-like column found in dataset {label}")

    # Detect numeric column (first non-date)
    value_col = None
    for col in df.columns:
        if col != date_col and pd.api.types.is_numeric_dtype(df[col]):
            value_col = col
            break
    if value_col is None:
        raise ValueError(f"No numeric value column found in dataset {label}")

    # Rename for Compare
    df = df.rename(columns={date_col: "Date", value_col: f"Value_{label}"})
    return df[["Date", f"Value_{label}"]]

#####-----Streamlit App-----#####

st.set_page_config(page_title="Macro Dashboard", layout="wide")

# --- Global Styles ---
st.markdown("""
<style>
/* Mobile responsiveness adjustments */
@media only screen and (max-width: 768px) {
    .block-container {
        padding: 0.5rem 0.5rem !important;
    }

    .stSelectbox label, .stDateInput label {
        font-size: 0.9rem !important;
    }

    .stSelectbox div[data-baseweb="select"] {
        font-size: 0.9rem !important;
    }

    .stButton > button {
        width: 100% !important;
    }

    h1, h2, h3 {
        font-size: 1.2rem !important;
    }

    .stPlotlyChart {
        width: 100% !important;
        height: auto !important;
    }
}

/* Prevent horizontal scrollbars */
html, body {
    overflow-x: hidden;
    margin: 0;
    padding: 0;
}

/* Hide default Streamlit UI */
#MainMenu, header, footer {visibility: hidden;}
.block-container {padding-top: 0rem !important;}

/* Fixed Top Bar */
.custom-header {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    z-index: 9999;
    background-color: #F9F9F9;
    width: 100%;
    padding: 1rem 2rem;
    display: flex;
    justify-content: space-between;
    align-items: center;

    /* Default = thin border */
    border-bottom: 1px solid #e5e5e5;
    transition: box-shadow 0.2s ease, border-bottom 0.2s ease;
}

/* When page is scrolled */
.custom-header.scrolled {
    border-bottom: none;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}

.custom-header .logo {
    font-weight: bold;
    font-size: 1.2rem;
}

.custom-header .menu {
    display: flex;
    justify-content: center;
    flex-grow: 1;
    gap: 2rem;
}

.custom-header .menu a {
    text-decoration: none;
    font-size: 1rem;
    color: black;
    font-weight: 500;
}

.custom-header .menu a:hover {
    color: #007bff;
}

/* Dropdown menu for countries */
.dropdown {
    position: relative;
    display: inline-block;
}

.dropdown-btn {
    background: none;
    border: none;
    font-size: 1rem;
    font-weight: 500;
    cursor: pointer;
    color: black;

    display: flex;
    align-items: center;
    height: 100%;
    padding: 0;
    line-height: 1;
}

.dropdown-content {
    display: none;
    position: absolute;
    background-color: #f9f9f9;
    min-width: 160px;
    box-shadow: 0px 8px 16px rgba(0,0,0,0.2);
    z-index: 1;
}

.dropdown-content a {
    color: black;
    padding: 10px 14px;
    text-decoration: none;
    display: block;
}

.dropdown-content a:hover {
    background-color: #f1f1f1;
}

.dropdown:hover .dropdown-content {display: block;}
.dropdown:hover .dropdown-btn {color: #007bff;}

/* Main content starts below fixed top bar */
.main-content {
    margin-top: 80px;  /* same height as .custom-header */
    padding: 0 1rem;
}

/* Hero section */
.hero {
    padding: 0;
    margin: 0 0 2rem 0;
    text-align: center;
}

.hero h1 {
    font-size: 2.5rem;
    font-weight: bold;
    margin: 0.2rem 0 0.5rem 0;
    color: #111;
    line-height: 1.2;
}

.hero p {
    font-size: 1.15rem;
    color: #444;
    margin-bottom: 1.8rem;
}
</style>
""", unsafe_allow_html=True)

# --- Fixed Top Bar (HTML block) ---
st.markdown("""
<div class="custom-header">
    <div class="logo">THEALEXBFX</div>
    <div class="menu">
        <a href="?page=Home" target="_self">Home</a>
        <div class="dropdown">
            <button class="dropdown-btn">Countries ▾</button>
            <div class="dropdown-content">
                <a href="?page=USA" target="_self">USA</a>
                <a href="?page=Japan" target="_self">Japan</a>
                <a href="?page=UK" target="_self">UK</a>
                <a href="?page=EURO" target="_self">Euro Area</a>
            </div>
        </div>
        <div class="dropdown">
            <button class="dropdown-btn">Asset Classes ▾</button>
            <div class="dropdown-content">
                <a href="?page=Equities" target="_self">Equities</a>
                <a href="?page=Stocks" target="_self">Stocks</a>
                <a href="?page=Commodities" target="_self">Commodities</a>
                <a href="?page=Bonds" target="_self">Bonds</a>
                <a href="?page=FX%20Rates" target="_self">FX Rates</a>
                <a href="?page=Crypto" target="_self">Crypto</a>
            </div>
        </div>
        <div class="dropdown">
            <button class="dropdown-btn">Yield Curve & Regimes ▾</button>
            <div class="dropdown-content">
                <a href="?page=Yield Curve" target="_self">Yield Curve</a>
                <a href="?page=Curve Regimes" target="_self">Curve Regimes</a>
            </div>
        </div>
        <a href="?page=Compare" target="_self">Compare</a>
        <a href="?page=Calendar" target="_self">Calendar</a>
        <a href="?page=Cycle" target="_self">Cycle</a>
    </div>
</div>
""", unsafe_allow_html=True)

# --- JS to toggle shadow on scroll ---
st.markdown("""
<script>
window.addEventListener('scroll', function() {
    const header = document.querySelector('.custom-header');
    if (window.scrollY > 10) {
        header.classList.add('scrolled');
    } else {
        header.classList.remove('scrolled');
    }
});
</script>
""", unsafe_allow_html=True)

query_params = st.query_params
page = query_params.get("page", "Home")  # default to Home if not specified

# --- Main content wrapper to start scroll below header ---
st.markdown('<div class="main-content">', unsafe_allow_html=True)

st.markdown("""
<style>
/* --------- Select Box Labels --------- */
label[data-baseweb="select"] {
    font-weight: 700 !important;   /* Bold */
    font-size: 18px !important;    /* Larger font */
    color: #1a1a1a !important;
}
label[data-baseweb="select"]::after {
    content: ":";   /* Colon stuck to word */
}

/* --------- Select Box --------- */
div[data-baseweb="select"] {
    border: 1.5px solid #000000 !important;  /* Black border */
    border-radius: 6px !important;
    font-size: 15px !important;
    background-color: #f5f5f5 !important;   /* Grey background */
}
div[data-baseweb="select"] > div {
    font-size: 15px !important;
    font-weight: 500 !important;
    color: #1a1a1a !important;
}
div[data-baseweb="select"]:hover {
    border-color: #000000 !important;       /* Black on hover */
}

/* --------- Date Input Labels --------- */
label[data-baseweb="input"] {
    font-weight: 700 !important;   /* Bold */
    font-size: 18px !important;    /* Larger font */
    color: #1a1a1a !important;
}
label[data-baseweb="input"]::after {
    content: ":";   /* Colon stuck to word */
}

/* --------- Date Input --------- */
div[data-baseweb="input"] {
    border: 1.5px solid #000000 !important;  /* Black border */
    border-radius: 6px !important;
    font-size: 15px !important;
    /* No background override → keeps Streamlit default */
}
div[data-baseweb="input"] input {
    font-size: 15px !important;
    font-weight: 500 !important;
    color: #1a1a1a !important;
}
div[data-baseweb="input"]:hover {
    border-color: #000000 !important;       /* Black on hover */
}
</style>
""", unsafe_allow_html=True)

# --- Main Content Below Header ---

if page == "Home":

    st.markdown("""
        <style>
                /* Reset page spacing */
        html, body {
            margin: 0;
            padding: 0;
        }

        /* Sticky top navigation bar */
        .navbar {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            z-index: 1000;
            margin: 0;
            padding: 0.75rem 1rem;  /* adjust to taste */
            background-color: #fff; /* or your theme color */
            border-bottom: 1px solid #eee;
        }

        /* Push content down so it doesn’t overlap navbar */
        .main-content {
            margin-top: 4rem;  /* same height as navbar */
        }

        /* Hero section (dashboard title) */
        .hero {
            padding: 0;
            border: none;
            border-radius: 0;
            box-shadow: none;
            background: none;
            text-align: center;
            margin: 0 0 2rem 0; /* remove top margin */
        }

        .hero h1 {
            font-size: 2.5rem;
            font-weight: bold;
            margin: 0.2rem 0 0.5rem 0;  /* kill default top gap */
            color: #111;
            line-height: 1.2;
        }


        .hero p {
            font-size: 1.15rem;
            color: #444;
            margin-bottom: 1.8rem;
        }

        .section {
            margin-top: 3rem;
        }

        .section h2 {
            font-size: 1.6rem;
            border-bottom: 2px solid #eee;
            padding-bottom: 0.4rem;
            margin-bottom: 1.2rem;
            color: #222;
        }

        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
            gap: 1.5rem;
        }

        .feature-box {
            background-color: #ffffff;
            border: 1px solid #ddd;
            padding: 1.2rem 1.5rem;
            border-radius: 0.75rem;
            box-shadow: 0 1px 5px rgba(0,0,0,0.03);
        }

        .feature-box h3 {
            margin-top: 0;
            margin-bottom: 0.5rem;
            font-size: 1.1rem;
            color: #000;
        }

        .feature-box p {
            font-size: 0.95rem;
            color: #555;
        }

        .hr-separator {
            margin: 3rem 0;
            border: none;
            border-top: 2px solid #eee;
        }

        .chart-title {
            font-size: 1.25rem;
            font-weight: 600;
            text-align: center;
            margin: 1rem 0 0.5rem;
        }

        .footer {
            margin-top: 4rem;
            padding-top: 2rem;
            border-top: 1px solid #eee;
            font-size: 0.9rem;
            color: #666;
            text-align: center;
        }

        .footer a {
            color: #007bff;
            text-decoration: none;
        }

        .footer a:hover {
            text-decoration: underline;
        }

        .calendar-snippet-container {
            max-width: 700px;
            margin: 0 auto 2rem auto;
            background: none;
            border: none;
            border-radius: 0;
        padding: 0;
            box-shadow: none;
            text-align: center;
        }


        .calendar-snippet-container h3 {
            font-weight: 700;
            font-size: 1.5rem;
            margin-bottom: 1rem;
            color: #222;
            border-bottom: 2px solid #ddd;
            padding-bottom: 0.5rem;
        }

        .calendar-event {
            display: inline-block;
            white-space: nowrap;
            font-size: 1rem;
            margin: 0.25rem 0;
            padding: 6px 12px;
            border-radius: 6px;
            background-color: transparent;
            ##border: 1px solid #ccc;
            ##box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        }

        .calendar-event > span {
            margin: 0 6px;
        }

        .impact-high {
            color: #ff4d4d;
            font-weight: 700;
        }

        .impact-medium {
            color: #ffa500;
            font-weight: 700;
        }

        .impact-low {
            color: #32cd32;
            font-weight: 700;
        }
        </style>
        
        <div class="hero">
            <h1>thealexbfx Macro Dashboard</h1>
            <p>Track global macroeconomic trends and FX markets—daily updated, interactive, and analyst-ready.</p>
        </div>
        <hr class="hr-separator"/>
    """, unsafe_allow_html=True)

    # Load and show today's economic events
    try:
        cal_df = pd.read_csv("economic_calendar.csv", parse_dates=["Date"])
    except Exception as e:
        st.error(f"Error loading economic calendar data: {e}")
        cal_df = pd.DataFrame()

    if not cal_df.empty:
        today = pd.to_datetime(dt.date.today())
        todays_events = cal_df[cal_df['Date'] == today]

        if not todays_events.empty:
            calendar_html = (
                '<div class="calendar-snippet-container">'
                '<h3>📅 Today\'s Economic Events</h3>'
            )

            for _, row in todays_events.iterrows():
                impact_class = {
                    "🔴 High": "impact-high",
                    "🟠 Medium": "impact-medium",
                    "🟢 Low": "impact-low"
                }.get(row['Impact'], "")

                calendar_html += (
                    f'<div class="calendar-event">'
                    f'<b>Date:</b> {row["Date"].strftime("%A %d %B")}'
                    f'<span>|</span><b>Time:</b> {row["Time"]}'
                    f'<span>|</span><b>Country:</b> {row["Country"]}'
                    f'<span>|</span><b>Event:</b> {row["Event"]}'
                    f'<span>|</span><span class="{impact_class}">{row["Impact"]}</span>'
                    f'</div>'
                )

            calendar_html += '</div>'
            st.markdown(calendar_html, unsafe_allow_html=True)
        else:
            st.info("No economic events scheduled for today.")

    # Show DXY chart below the calendar snippet
    dxy_df = get_fx_data_yahoo("DX-Y.NYB", start_date=dt.date.today() - dt.timedelta(days=365), end_date=dt.date.today())
    dxy_chart = plot_chart(dxy_df, "DXY (US Dollar Index)", chart_type="Line")

    
    st.plotly_chart(dxy_chart, use_container_width=True)

    # Features and footer
    st.markdown("""
        <div class="section">
            <h2>🔍 What You Can Explore</h2>
            <div class="grid">
                <div class="feature-box">
                    <h3>🌍 Countries</h3>
                    <p>Dive into economic data for the USA, Japan, UK, and Euro Area — interest rates, GDP, inflation, jobs, and more.</p>
                </div>
                <div class="feature-box">
                    <h3>💹 Asset Classes</h3>
                    <p>Track Equities, Bonds, Commodities, FX Rates, and Crypto — all in one place, with charts and comparisons.</p>
                </div>
                <div class="feature-box">
                    <h3>📈 Yield Curve & Regimes</h3>
                    <p>Visualize yield curves across countries, spot steepening/inverting regimes, and analyze market signals.</p>
                </div>
                <div class="feature-box">
                    <h3>⚖️ Compare</h3>
                    <p>Overlay any two indicators (e.g., U.S. CPI vs EUR/USD, 10Y yields vs GDP) with dual axes for deeper analysis.</p>
                </div>
                <div class="feature-box">
                    <h3>📅 Calendar</h3>
                    <p>Stay on top of daily global economic events — with impact levels clearly highlighted.</p>
                </div>
                <div class="feature-box">
                    <h3>🧠 Analysis</h3>
                    <p>Scenario simulations and commentary tools help you generate insights like an analyst, not just a chart watcher.</p>
                </div>
            </div>
        </div>


        <div class="section">
            <h2>🚀 How to Use This Dashboard</h2>
            <ul>
                <li><b>Navigate using the top bar</b> — choose a <b>Country</b> (USA, Japan, UK, Euro Area) or an <b>Asset Class</b> (Equities, Bonds, Commodities, FX, Crypto).</li>
                <li><b>Explore Yield Curves & Regimes</b> to analyze steepening, flattening, and inversion cycles across markets.</li>
                <li><b>Use Compare</b> to overlay any two indicators with dual y-axes for deeper macro insights.</li>
                <li><b>Check the Calendar</b> daily for upcoming economic events, sorted by impact level.</li>
                <li><b>Dive into Analysis</b> for scenario simulations and commentary to support your trading or research ideas.</li>
                <li><b>Adjust chart types and timeframes</b> as needed — everything updates instantly and interactively.</li>
            </ul>
        </div>


        <div class="section">
            <h2>📡 Data Sources</h2>
            <ul>
                <li><b>Asset Classes (Equities, Bonds, Commodities, FX, Crypto):</b> Yahoo Finance</li>
                <li><b>U.S. Yield Curve Data:</b> Federal Reserve Economic Data (FRED)</li>
                <li><b>Economic Indicators (USA, Japan, UK, Euro Area):</b> FXStreet + manually maintained datasets (updated daily)</li>
            </ul>
            <p style="font-size:0.9rem; color:#555; margin-top:0.5rem;">
                <i>Note: All data is updated daily. Some indicators are manually curated for accuracy and completeness.</i>
            </p>
        </div>


        <div class="footer">
            <p>Built by <b>thealexbfx</b> • All data updates daily</p>
            <p>
                Contact: <a href="https://www.linkedin.com/in/alex-ballinger-059919302/" target="_blank">LinkedIn</a> |
                <a href="https://youtube.com/@thealexbfx" target="_blank">YouTube</a> |
                <a href="https://www.instagram.com/thealexbfx/" target="_blank">Instagram</a>
            </p>
            <p>&copy; 2025 thealexbfx. All rights reserved.</p>
        </div>
    """, unsafe_allow_html=True)

# -------- USA Tab --------
if page == "USA":
    col1, col2 = st.columns([1.5, 5])

    with col1:
        st.markdown("<div style='margin-top:-40px;'>", unsafe_allow_html=True)

        # -------- Indicator Groups --------
        indicator_groups = {
            "Labor Market": [
                "Unemployment Rate",
                "Average Hourly Earnings YoY",
                "Jolts Job Openings",
                "Non Farm Payrolls"
            ],
            "Growth": [
                "GDP Growth Rate",
                "Retail Sales MoM",
                "Housing Starts MoM",
                "Trade Balance"
            ],
            "Inflation": [
                "CPI YoY",
                "Core CPI YoY",
                "PCE YoY",
                "Core PCE YoY",
                "PPI YoY",
                "Core PPI YoY"
            ],
            "Surveys": [
                "ISM Manufacturing PMI",
                "ISM Services PMI",
                "Michigan Consumer Sentiment"
            ],
            "Monetary Policy": [
                "Interest Rate"
            ]
        }

        # Category dropdown
        category = st.selectbox("Select Category", list(indicator_groups.keys()))

        # Indicator dropdown based on category
        indicator = st.selectbox("Select Indicator", indicator_groups[category])

        # -------- Chart Type + Timeframe side by side --------
        ct_col, tf_col = st.columns(2)
        with ct_col:
            chart_type = st.selectbox("Chart Type", ["Line", "Area", "Bar", "Step"])
        with tf_col:
            timeframe = st.selectbox("Time Frame", ["1Y", "3Y", "5Y", "10Y", "MAX"])

        # Delta Type (allow turning it off)
        delta_type = st.selectbox("Delta Type", ["Off", "Cumulative", "Daily"])

        # -------- Indicator Function Mapping --------
        indicator_map = {
            "Interest Rate": (get_usa_interest_rate_data, "daily", "%b %Y"),
            "CPI YoY": (get_usa_cpi_yoy_data, "monthly", None),
            "GDP Growth Rate": (get_usa_gdp_qoq_data, "quarterly", None),
            "Unemployment Rate": (get_usa_unemployment_rate_data, "monthly", None),
            "Core CPI YoY": (get_usa_core_cpi_yoy_data, "monthly", None),
            "Average Hourly Earnings YoY": (get_usa_average_hourly_earnings_yoy_data, "monthly", None),
            "Core PCE YoY": (get_usa_core_pce_yoy_data, "monthly", None),
            "Core PPI YoY": (get_usa_core_ppi_yoy_data, "monthly", None),
            "Housing Starts MoM": (get_usa_housing_starts_mom_data, "monthly", None),
            "ISM Manufacturing PMI": (get_usa_ism_manufacturing_pmi_data, "monthly", None),
            "ISM Services PMI": (get_usa_ism_services_pmi_data, "monthly", None),
            "Jolts Job Openings": (get_usa_jolts_job_openings_data, "monthly", None),
            "Michigan Consumer Sentiment": (get_usa_michigan_consumer_sentiment_data, "monthly", None),
            "Non Farm Payrolls": (get_usa_nfp_data, "monthly", None),
            "PCE YoY": (get_usa_pce_yoy_data, "monthly", None),
            "PPI YoY": (get_usa_ppi_yoy_data, "monthly", None),
            "Retail Sales MoM": (get_usa_retail_sales_mom_data, "monthly", None),
            "Trade Balance": (get_usa_trade_balance_data, "monthly", None),
        }

        # Load data dynamically
        func, date_format, tickformat_override = indicator_map[indicator]
        df = func()
        df = df.dropna()
        if df.empty:
            st.error("No data available.")
            st.stop()

        # -------- Time Frame Logic --------
        earliest_date = df['date'].min().date()
        latest_date = df['date'].max().date()
        if timeframe != "MAX":
            years = int(timeframe.replace("Y", ""))
            default_start_date = max(earliest_date, latest_date - dt.timedelta(days=365*years))
        else:
            default_start_date = earliest_date

        # -------- Start & End Dates side by side --------
        date_col1, date_col2 = st.columns(2)
        with date_col1:
            start_date = st.date_input("Start Date", default_start_date, min_value=earliest_date, max_value=latest_date)
        with date_col2:
            end_date = st.date_input("End Date", latest_date, min_value=earliest_date, max_value=latest_date)

        if start_date > end_date:
            st.warning("Start date cannot be after end date.")
            st.stop()

        st.markdown("</div>", unsafe_allow_html=True)

    with col2:
        # -------- Commentary --------
        commentary = {
            # Monetary Policy
            "Interest Rate": (
                "The Federal Funds Rate is the benchmark interest rate set by the Federal Reserve. "
                "It directly influences short-term borrowing costs for banks, which affects mortgages, loans, and business investment. "
                "Changes in the Fed’s rate are closely watched by global markets as signals of monetary tightening or easing."
            ),

            # Inflation
            "CPI YoY": (
                "The Consumer Price Index (CPI YoY) tracks the annual percentage change in the cost of a basket of goods and services. "
                "It is a key measure of inflation and influences interest rate decisions, wages, and investment strategies."
            ),
            "Core CPI YoY": (
                "Core CPI excludes volatile food and energy prices, providing a clearer view of underlying inflation trends. "
                "Policymakers use it to assess persistent price pressures in the economy."
            ),
            "PCE YoY": (
                "The Personal Consumption Expenditures Price Index (PCE YoY) measures the annual change in consumer prices based on actual spending patterns. "
                "It is the Fed’s preferred inflation gauge, reflecting household consumption costs more accurately than CPI."
            ),
            "Core PCE YoY": (
                "Core PCE excludes food and energy prices to highlight underlying inflation trends. "
                "It is closely monitored by the Fed when making monetary policy decisions."
            ),
            "PPI YoY": (
                "The Producer Price Index (PPI YoY) measures annual changes in prices received by producers of goods and services. "
                "Rising producer prices can indicate future increases in consumer prices."
            ),
            "Core PPI YoY": (
                "Core PPI excludes food and energy prices to focus on underlying producer price trends. "
                "It helps identify inflationary pressures before they reach consumers."
            ),

            # Growth
            "GDP Growth Rate": (
                "The GDP Growth Rate measures the pace at which the U.S. economy is expanding or contracting. "
                "It reflects trends in production, investment, government spending, and trade."
            ),
            "Retail Sales MoM": (
                "Retail Sales MoM tracks monthly changes in consumer spending. "
                "It is a key driver of economic growth, as consumer spending accounts for roughly two-thirds of U.S. GDP."
            ),
            "Housing Starts": (
                "Housing Starts measure the number of new residential construction projects that have begun during the month, reported as a seasonally adjusted annual rate (SAAR) in millions. "
                "It includes single-family homes and multi-unit buildings, providing insight into housing demand, construction employment, and overall economic momentum."
            ),
            "Trade Balance": (
                "The U.S. Trade Balance shows the difference between exports and imports of goods and services. "
                "A deficit occurs when imports exceed exports, and a surplus when exports exceed imports, reflecting global demand and competitiveness."
            ),

            # Labor Market
            "Unemployment Rate": (
                "The unemployment rate measures the percentage of the labor force that is actively seeking work but is jobless. "
                "It is a primary indicator of labor market health, influencing consumer spending and economic policy."
            ),
            "Average Hourly Earnings YoY": (
                "Average Hourly Earnings YoY tracks annual growth in workers’ wages. "
                "Rising wages support consumer spending but may contribute to inflation if growth exceeds productivity."
            ),
            "Jolts Job Openings": (
                "The JOLTS Job Openings report measures the number of unfilled positions across the economy. "
                "High job openings relative to unemployed workers signal a tight labor market and potential upward pressure on wages."
            ),
            "Non Farm Payrolls": (
                "Non-Farm Payrolls measure the monthly change in employment across most sectors, excluding farming. "
                "It is closely watched as a timely indicator of labor market strength and economic activity."
            ),

            # Surveys
            "ISM Manufacturing PMI": (
                "The ISM Manufacturing PMI surveys purchasing managers in the manufacturing sector. "
                "A reading above 50 signals expansion, while below 50 signals contraction, offering insight into economic trends."
            ),
            "ISM Services PMI": (
                "The ISM Services PMI tracks activity in the services sector, the largest component of the U.S. economy. "
                "Values above 50 indicate growth, and below 50 indicate contraction."
            ),
            "Michigan Consumer Sentiment": (
                "The Michigan Consumer Sentiment Index measures household confidence in the economy, financial conditions, and expectations. "
                "Shifts in sentiment can foreshadow changes in consumer spending and economic activity."
            )
        }

        st.markdown(
            f"""
            <div style="
                position: relative;
                top: -10px;
                margin-left: 30px;
                font-size:19px;
                font-family: 'Arial Bold';
                font-weight:normal;
                color:#333;
            ">
                {commentary.get(indicator, "")}
            </div>
            """,
            unsafe_allow_html=True
        )

        # -------- Filter Data by Date --------
        df_filtered = df[(df['date'] >= pd.to_datetime(start_date)) &
                         (df['date'] <= pd.to_datetime(end_date))]

        # -------- Dynamic Titles --------
        titles = {
            # Monetary Policy
            "Interest Rate": "Federal Funds Rate (%)",

            # Inflation
            "CPI YoY": "Consumer Price Index (CPI YoY, %)",
            "Core CPI YoY": "Core Consumer Price Index (YoY, %)",
            "PCE YoY": "Personal Consumption Expenditures (PCE YoY, %)",
            "Core PCE YoY": "Core Personal Consumption Expenditures (YoY, %)",
            "PPI YoY": "Producer Price Index (PPI YoY, %)",
            "Core PPI YoY": "Core Producer Price Index (YoY, %)",

            # Growth
            "GDP Growth Rate": "GDP Growth Rate (%)",
            "Retail Sales MoM": "Retail Sales (MoM, %)",
            "Housing Starts": "Housing Starts (Millions)",
            "Trade Balance": "Trade Balance (Billions USD)",

            # Labor Market
            "Unemployment Rate": "Unemployment Rate (%)",
            "Average Hourly Earnings YoY": "Average Hourly Earnings (YoY, %)",
            "Jolts Job Openings": "Job Openings (JOLTS, Millions)",
            "Non Farm Payrolls": "Non-Farm Payrolls (Change, Thousands)",

            # Surveys
            "ISM Manufacturing PMI": "ISM Manufacturing PMI (Index)",
            "ISM Services PMI": "ISM Services PMI (Index)",
            "Michigan Consumer Sentiment": "Michigan Consumer Sentiment (Index)"
        }

        # Detect quarterly data
        quarterly = (date_format == "quarterly")

        # -------- Plot Chart --------
        # Convert "Off" to None for plot_chart
        delta_type_arg = None if delta_type == "Off" else delta_type.lower()

        # If delta_type is Off, disable hover delta
        hover_style = "delta" if delta_type_arg is not None else "none"

        fig = plot_chart(
            df_filtered,
            titles[indicator],
            chart_type,
            hover_style=hover_style,   # conditional hover
            delta_type=delta_type_arg,  # None if Off
            date_format="quarterly" if quarterly else date_format,
            tickformat_override=tickformat_override,
            show_markers=False
        )



        # For quarterly, show only Q4 labels
        if quarterly:
            tickvals = df_filtered.loc[df_filtered['date'].dt.quarter == 4, 'date']
            ticktext = df_filtered.loc[df_filtered['date'].dt.quarter == 4, 'date'] \
                .dt.to_period('Q').apply(lambda x: f"Q{x.quarter} {x.year}")
            fig.update_xaxes(tickmode='array', tickvals=tickvals, ticktext=ticktext)
            
        fig.update_layout(
            hoverlabel=dict(
                font_size=13,       # optional
                font_color="black", # change text color to black
                font_family="Arial" # optional
            )
        )
            

        # -------- Display Chart --------
        st.plotly_chart(
            fig,
            use_container_width=True,
            config={
                "displayModeBar": True,
                "displaylogo": False,
                "modeBarButtonsToAdd": ["toImage", "resetScale2d", "zoom2d", "pan2d"],
                "modeBarButtonsToRemove": ["lasso2d", "select2d"]
            }
        )

        # -------- CSV Download --------
        csv_data = df_filtered.to_csv(index=False)
        st.download_button(
            label="📥 Download CSV",
            data=csv_data,
            file_name=f"USA_{indicator.replace(' ', '_')}_data.csv",
            mime="text/csv"
        )

# -------- Japan Tab --------
if page == "Japan":
    col1, col2 = st.columns([1.5, 5])

    with col1:
        st.markdown("<div style='margin-top:-40px;'>", unsafe_allow_html=True)

        # -------- Indicator Groups --------
        indicator_groups = {
            "Labor Market": ["Unemployment Rate"],
            "Growth": ["GDP Growth Rate"],
            "Inflation": ["CPI YoY"],
            "Monetary Policy": ["Interest Rate"]
        }

        # Category dropdown
        category = st.selectbox("Select Category", list(indicator_groups.keys()))

        # Indicator dropdown based on category
        indicator = st.selectbox("Select Indicator", indicator_groups[category])

        # -------- Chart Type + Timeframe side by side --------
        ct_col, tf_col = st.columns(2)
        with ct_col:
            chart_type = st.selectbox("Chart Type", ["Line", "Area", "Bar", "Step"])
        with tf_col:
            timeframe = st.selectbox("Time Frame", ["1Y", "3Y", "5Y", "10Y", "MAX"])

        # Delta Type (allow turning it off)
        delta_type = st.selectbox("Delta Type", ["Off", "Cumulative", "Daily"])

        # -------- Indicator Function Mapping --------
        indicator_map = {
            "Interest Rate": (get_japan_interest_rate_data, "daily", "%b %Y"),
            "CPI YoY": (get_japan_cpi_yoy_data, "monthly", None),
            "GDP Growth Rate": (get_japan_gdp_qoq_data, "quarterly", None),
            "Unemployment Rate": (get_japan_unemployment_rate_data, "monthly", None)
        }

        # Load data dynamically
        func, date_format, tickformat_override = indicator_map[indicator]
        df = func()
        df = df.dropna()
        if df.empty:
            st.error("No data available.")
            st.stop()

        # -------- Time Frame Logic --------
        earliest_date = df['date'].min().date()
        latest_date = df['date'].max().date()
        if timeframe != "MAX":
            years = int(timeframe.replace("Y", ""))
            default_start_date = max(earliest_date, latest_date - dt.timedelta(days=365*years))
        else:
            default_start_date = earliest_date

        # -------- Start & End Dates side by side --------
        date_col1, date_col2 = st.columns(2)
        with date_col1:
            start_date = st.date_input("Start Date", default_start_date, min_value=earliest_date, max_value=latest_date)
        with date_col2:
            end_date = st.date_input("End Date", latest_date, min_value=earliest_date, max_value=latest_date)

        if start_date > end_date:
            st.warning("Start date cannot be after end date.")
            st.stop()

        st.markdown("</div>", unsafe_allow_html=True)

    with col2:
        # -------- Commentary --------
        commentary = {
            # Monetary Policy
            "Interest Rate": (
                "The Bank of Japan (BoJ) policy rate is the benchmark interest rate set by the BoJ. "
                "It directly influences short-term borrowing costs for banks, which affects mortgages, loans, and business investment. "
                "Changes in the BoJ’s rate are closely watched by global markets as signals of monetary tightening or easing."
            ),

            # Inflation
            "CPI YoY": (
                "The Consumer Price Index (CPI YoY) tracks the annual percentage change in the cost of a basket of goods and services in Japan. "
                "It is a key measure of inflation and influences BoJ interest rate decisions, wages, and investment strategies."
            ),

            # Growth
            "GDP Growth Rate": (
                "The GDP Growth Rate measures the pace at which the Japanese economy is expanding or contracting. "
                "It reflects trends in production, investment, government spending, and trade."
            ),

            # Labor Market
            "Unemployment Rate": (
                "The unemployment rate measures the percentage of the labor force that is actively seeking work but is jobless. "
                "It is a primary indicator of labor market health, influencing consumer spending and economic policy."
            )
        }


        st.markdown(
            f"""
            <div style="
                position: relative;
                top: -10px;
                margin-left: 30px;
                font-size:19px;
                font-family: 'Arial Bold';
                font-weight:normal;
                color:#333;
            ">
                {commentary.get(indicator, "")}
            </div>
            """,
            unsafe_allow_html=True
        )

        # -------- Filter Data by Date --------
        df_filtered = df[(df['date'] >= pd.to_datetime(start_date)) &
                         (df['date'] <= pd.to_datetime(end_date))]

        # -------- Dynamic Titles --------
        titles = {
            "Interest Rate": "Bank of Japan Policy Rate (%)",
            "CPI YoY": "Consumer Price Index (YoY, %)",
            "GDP Growth Rate": "GDP Growth Rate (QoQ Annualized %)",
            "Unemployment Rate": "Unemployment Rate (%)"
        }

        # Detect quarterly data
        quarterly = (date_format == "quarterly")

        # -------- Plot Chart --------
        delta_type_arg = None if delta_type == "Off" else delta_type.lower()
        hover_style = "delta" if delta_type_arg is not None else "none"

        fig = plot_chart(
            df_filtered,
            titles[indicator],
            chart_type,
            hover_style=hover_style,
            delta_type=delta_type_arg,
            date_format="quarterly" if quarterly else date_format,
            tickformat_override=tickformat_override,
            show_markers=False
        )

        if quarterly:
            tickvals = df_filtered.loc[df_filtered['date'].dt.quarter == 4, 'date']
            ticktext = df_filtered.loc[df_filtered['date'].dt.quarter == 4, 'date'] \
                .dt.to_period('Q').apply(lambda x: f"Q{x.quarter} {x.year}")
            fig.update_xaxes(tickmode='array', tickvals=tickvals, ticktext=ticktext)

        fig.update_layout(
            hoverlabel=dict(
                font_size=13,
                font_color="black",
                font_family="Arial"
            )
        )

        # -------- Display Chart --------
        st.plotly_chart(
            fig,
            use_container_width=True,
            config={
                "displayModeBar": True,
                "displaylogo": False,
                "modeBarButtonsToAdd": ["toImage", "resetScale2d", "zoom2d", "pan2d"],
                "modeBarButtonsToRemove": ["lasso2d", "select2d"]
            }
        )

        # -------- CSV Download --------
        csv_data = df_filtered.to_csv(index=False)
        st.download_button(
            label="📥 Download CSV",
            data=csv_data,
            file_name=f"Japan_{indicator.replace(' ', '_')}_data.csv",
            mime="text/csv"
        )

       
# -------- UK Tab --------
if page == "UK":
    col1, col2 = st.columns([1.5, 5])

    with col1:
        st.markdown("<div style='margin-top:-40px;'>", unsafe_allow_html=True)

        # -------- Indicator Groups --------
        indicator_groups = {
            "Labor Market": ["Unemployment Rate"],
            "Growth": ["GDP Growth Rate"],
            "Inflation": ["CPI YoY"],
            "Monetary Policy": ["Interest Rate"]
        }

        # Category dropdown
        category = st.selectbox("Select Category", list(indicator_groups.keys()))

        # Indicator dropdown based on category
        indicator = st.selectbox("Select Indicator", indicator_groups[category])

        # -------- Chart Type + Timeframe side by side --------
        ct_col, tf_col = st.columns(2)
        with ct_col:
            chart_type = st.selectbox("Chart Type", ["Line", "Area", "Bar", "Step"])
        with tf_col:
            timeframe = st.selectbox("Time Frame", ["1Y", "3Y", "5Y", "10Y", "MAX"])

        # Delta Type (allow turning it off)
        delta_type = st.selectbox("Delta Type", ["Off", "Cumulative", "Daily"])

        # -------- Indicator Function Mapping --------
        indicator_map = {
            "Interest Rate": (get_uk_interest_rate_data, "daily", "%b %Y"),
            "CPI YoY": (get_uk_cpi_yoy_data, "monthly", None),
            "GDP Growth Rate": (get_uk_gdp_qoq_data, "quarterly", None),
            "Unemployment Rate": (get_uk_unemployment_rate_data, "monthly", None)
        }

        # Load data dynamically
        func, date_format, tickformat_override = indicator_map[indicator]
        df = func()
        df = df.dropna()
        if df.empty:
            st.error("No data available.")
            st.stop()

        # -------- Time Frame Logic --------
        earliest_date = df['date'].min().date()
        latest_date = df['date'].max().date()
        if timeframe != "MAX":
            years = int(timeframe.replace("Y", ""))
            default_start_date = max(earliest_date, latest_date - dt.timedelta(days=365*years))
        else:
            default_start_date = earliest_date

        # -------- Start & End Dates side by side --------
        date_col1, date_col2 = st.columns(2)
        with date_col1:
            start_date = st.date_input("Start Date", default_start_date, min_value=earliest_date, max_value=latest_date)
        with date_col2:
            end_date = st.date_input("End Date", latest_date, min_value=earliest_date, max_value=latest_date)

        if start_date > end_date:
            st.warning("Start date cannot be after end date.")
            st.stop()

        st.markdown("</div>", unsafe_allow_html=True)

    with col2:
        # -------- Commentary --------
        commentary = {
            # Monetary Policy
            "Interest Rate": (
                "The Bank of England (BoE) policy rate is the benchmark interest rate set by the BoE. "
                "It directly affects short-term borrowing costs for banks, which in turn influence mortgages, loans, and business investment. "
                "Changes in the BoE rate are closely monitored by global markets as signals of monetary tightening or easing."
            ),

            # Inflation
            "CPI YoY": (
                "The Consumer Price Index (CPI YoY) measures the annual percentage change in the cost of a typical basket of goods and services in the UK. "
                "It is a key gauge of inflation and informs BoE interest rate decisions, wage adjustments, and investment strategies."
            ),

            # Growth
            "GDP Growth Rate": (
                "The GDP Growth Rate captures the pace at which the UK economy is expanding or contracting. "
                "It reflects trends in consumption, investment, government spending, and trade, providing insight into overall economic health."
            ),

            # Labor Market
            "Unemployment Rate": (
                "The unemployment rate measures the percentage of the UK labor force that is actively seeking work but is currently jobless. "
                "It is a primary indicator of labor market conditions and has implications for consumer spending and economic policy."
            )
        }


        st.markdown(
            f"""
            <div style="
                position: relative;
                top: -10px;
                margin-left: 30px;
                font-size:19px;
                font-family: 'Arial Bold';
                font-weight:normal;
                color:#333;
            ">
                {commentary.get(indicator, "")}
            </div>
            """,
            unsafe_allow_html=True
        )

        # -------- Filter Data by Date --------
        df_filtered = df[(df['date'] >= pd.to_datetime(start_date)) &
                         (df['date'] <= pd.to_datetime(end_date))]

        # -------- Dynamic Titles --------
        titles = {
            "Interest Rate": "Bank of England Policy Rate (%)",
            "CPI YoY": "Consumer Price Index (YoY, %)",
            "GDP Growth Rate": "GDP Growth Rate (QoQ Annualized %)",
            "Unemployment Rate": "Unemployment Rate (%)"
        }

        # Detect quarterly data
        quarterly = (date_format == "quarterly")

        # -------- Plot Chart --------
        delta_type_arg = None if delta_type == "Off" else delta_type.lower()
        hover_style = "delta" if delta_type_arg is not None else "none"

        fig = plot_chart(
            df_filtered,
            titles[indicator],
            chart_type,
            hover_style=hover_style,
            delta_type=delta_type_arg,
            date_format="quarterly" if quarterly else date_format,
            tickformat_override=tickformat_override,
            show_markers=False
        )

        if quarterly:
            tickvals = df_filtered.loc[df_filtered['date'].dt.quarter == 4, 'date']
            ticktext = df_filtered.loc[df_filtered['date'].dt.quarter == 4, 'date'] \
                .dt.to_period('Q').apply(lambda x: f"Q{x.quarter} {x.year}")
            fig.update_xaxes(tickmode='array', tickvals=tickvals, ticktext=ticktext)

        fig.update_layout(
            hoverlabel=dict(
                font_size=13,
                font_color="black",
                font_family="Arial"
            )
        )

        # -------- Display Chart --------
        st.plotly_chart(
            fig,
            use_container_width=True,
            config={
                "displayModeBar": True,
                "displaylogo": False,
                "modeBarButtonsToAdd": ["toImage", "resetScale2d", "zoom2d", "pan2d"],
                "modeBarButtonsToRemove": ["lasso2d", "select2d"]
            }
        )

        # -------- CSV Download --------
        csv_data = df_filtered.to_csv(index=False)
        st.download_button(
            label="📥 Download CSV",
            data=csv_data,
            file_name=f"UK_{indicator.replace(' ', '_')}_data.csv",
            mime="text/csv"
        )

        
# -------- EURO Tab --------
if page == "EURO":
    col1, col2 = st.columns([1.5, 5])

    with col1:
        st.markdown("<div style='margin-top:-40px;'>", unsafe_allow_html=True)

        # -------- Indicator Groups --------
        indicator_groups = {
            "Labor Market": ["Unemployment Rate"],
            "Growth": ["GDP Growth Rate"],
            "Inflation": ["CPI YoY"],
            "Monetary Policy": ["Interest Rate"]
        }

        # Category dropdown
        category = st.selectbox("Select Category", list(indicator_groups.keys()))

        # Indicator dropdown based on category
        indicator = st.selectbox("Select Indicator", indicator_groups[category])

        # -------- Chart Type + Timeframe side by side --------
        ct_col, tf_col = st.columns(2)
        with ct_col:
            chart_type = st.selectbox("Chart Type", ["Line", "Area", "Bar", "Step"])
        with tf_col:
            timeframe = st.selectbox("Time Frame", ["1Y", "3Y", "5Y", "10Y", "MAX"])

        # Delta Type (allow turning it off)
        delta_type = st.selectbox("Delta Type", ["Off", "Cumulative", "Daily"])

        # -------- Indicator Function Mapping --------
        indicator_map = {
            "Interest Rate": (get_euro_interest_rate_data, "daily", "%b %Y"),
            "CPI YoY": (get_euro_cpi_yoy_data, "monthly", None),
            "GDP Growth Rate": (get_euro_gdp_qoq_data, "quarterly", None),
            "Unemployment Rate": (get_euro_unemployment_rate_data, "monthly", None)
        }

        # Load data dynamically
        func, date_format, tickformat_override = indicator_map[indicator]
        df = func()
        df = df.dropna()
        if df.empty:
            st.error("No data available.")
            st.stop()

        # -------- Time Frame Logic --------
        earliest_date = df['date'].min().date()
        latest_date = df['date'].max().date()
        if timeframe != "MAX":
            years = int(timeframe.replace("Y", ""))
            default_start_date = max(earliest_date, latest_date - dt.timedelta(days=365*years))
        else:
            default_start_date = earliest_date

        # -------- Start & End Dates side by side --------
        date_col1, date_col2 = st.columns(2)
        with date_col1:
            start_date = st.date_input("Start Date", default_start_date, min_value=earliest_date, max_value=latest_date)
        with date_col2:
            end_date = st.date_input("End Date", latest_date, min_value=earliest_date, max_value=latest_date)

        if start_date > end_date:
            st.warning("Start date cannot be after end date.")
            st.stop()

        st.markdown("</div>", unsafe_allow_html=True)

    with col2:
        # -------- Commentary --------
        commentary = {
            # Monetary Policy
            "Interest Rate": (
                "The European Central Bank (ECB) policy rate is the benchmark interest rate set by the ECB. "
                "It directly affects short-term borrowing costs for banks, which influences loans, mortgages, and business investment across the Eurozone. "
                "Changes in the ECB rate are closely watched by global markets as signals of monetary tightening or easing."
            ),

            # Inflation
            "CPI YoY": (
                "The Consumer Price Index (CPI YoY) tracks the annual percentage change in the cost of a representative basket of goods and services in the Euro area. "
                "It is a primary measure of inflation and informs ECB monetary policy, wage negotiations, and investment strategies."
            ),

            # Growth
            "GDP Growth Rate": (
                "The GDP Growth Rate measures how fast the Eurozone economy is expanding or contracting. "
                "It reflects trends in consumption, investment, government spending, and trade among member countries."
            ),

            # Labor Market
            "Unemployment Rate": (
                "The unemployment rate represents the percentage of the labor force in the Eurozone actively seeking work but currently without a job. "
                "It is a key indicator of labor market health, affecting consumer spending, social policies, and economic planning."
            )
        }

        st.markdown(
            f"""
            <div style="
                position: relative;
                top: -10px;
                margin-left: 30px;
                font-size:19px;
                font-family: 'Arial Bold';
                font-weight:normal;
                color:#333;
            ">
                {commentary.get(indicator, "")}
            </div>
            """,
            unsafe_allow_html=True
        )

        # -------- Filter Data by Date --------
        df_filtered = df[(df['date'] >= pd.to_datetime(start_date)) &
                         (df['date'] <= pd.to_datetime(end_date))]

        # -------- Dynamic Titles --------
        titles = {
            "Interest Rate": "ECB Policy Rate (%)",
            "CPI YoY": "Consumer Price Index (YoY, %)",
            "GDP Growth Rate": "GDP Growth Rate (QoQ Annualized %)",
            "Unemployment Rate": "Unemployment Rate (%)"
        }

        # Detect quarterly data
        quarterly = (date_format == "quarterly")

        # -------- Plot Chart --------
        delta_type_arg = None if delta_type == "Off" else delta_type.lower()
        hover_style = "delta" if delta_type_arg is not None else "none"

        fig = plot_chart(
            df_filtered,
            titles[indicator],
            chart_type,
            hover_style=hover_style,
            delta_type=delta_type_arg,
            date_format="quarterly" if quarterly else date_format,
            tickformat_override=tickformat_override,
            show_markers=False
        )

        if quarterly:
            tickvals = df_filtered.loc[df_filtered['date'].dt.quarter == 4, 'date']
            ticktext = df_filtered.loc[df_filtered['date'].dt.quarter == 4, 'date'] \
                .dt.to_period('Q').apply(lambda x: f"Q{x.quarter} {x.year}")
            fig.update_xaxes(tickmode='array', tickvals=tickvals, ticktext=ticktext)

        fig.update_layout(
            hoverlabel=dict(
                font_size=13,
                font_color="black",
                font_family="Arial"
            )
        )

        # -------- Display Chart --------
        st.plotly_chart(
            fig,
            use_container_width=True,
            config={
                "displayModeBar": True,
                "displaylogo": False,
                "modeBarButtonsToAdd": ["toImage", "resetScale2d", "zoom2d", "pan2d"],
                "modeBarButtonsToRemove": ["lasso2d", "select2d"]
            }
        )

        # -------- CSV Download --------
        csv_data = df_filtered.to_csv(index=False)
        st.download_button(
            label="📥 Download CSV",
            data=csv_data,
            file_name=f"Euro_{indicator.replace(' ', '_')}_data.csv",
            mime="text/csv"
        )

        
# -------- FX Rates Tab --------
if page == "FX Rates":

    col1, col2 = st.columns([1.5, 5])

    with col1:
        st.markdown("<div style='margin-top:-40px;'>", unsafe_allow_html=True)

        # -------- Indicator Groups (Major vs Minor FX) --------
        indicator_groups = {
            "Major Pairs": ["EUR/USD", "GBP/USD", "USD/JPY", "DXY"],
            "Cross Pairs": ["EUR/GBP", "EUR/JPY", "GBP/JPY"]
        }

        # Category dropdown
        category = st.selectbox("Select Category", list(indicator_groups.keys()))

        # Indicator dropdown based on category
        indicator = st.selectbox("Select Currency Pair", indicator_groups[category])

        # -------- Chart Type + Timeframe side by side --------
        ct_col, tf_col = st.columns(2)
        with ct_col:
            chart_type = st.selectbox("Chart Type", ["Line", "Area", "Bar", "Step"])
        with tf_col:
            timeframe = st.selectbox("Time Frame", ["1Y", "3Y", "5Y", "10Y", "MAX"])

        # Delta Type (allow turning it off)
        delta_type = st.selectbox("Delta Type", ["Off", "Cumulative", "Daily"])

        # -------- FX Mapping --------
        fx_tickers = {
            "EUR/USD": "EURUSD=X",
            "GBP/USD": "GBPUSD=X",
            "USD/JPY": "USDJPY=X",
            "EUR/GBP": "EURGBP=X",
            "EUR/JPY": "EURJPY=X",
            "GBP/JPY": "GBPJPY=X",
            "DXY": "DX-Y.NYB"
        }
        title_map = {
            "EUR/USD": "EUR/USD",
            "GBP/USD": "GBP/USD",
            "USD/JPY": "USD/JPY",
            "EUR/GBP": "EUR/GBP",
            "EUR/JPY": "EUR/JPY",
            "GBP/JPY": "GBP/JPY",
            "DXY": "DXY"
        }

        ticker = fx_tickers[indicator]
        title = title_map[indicator]

        # Load FX data
        df = get_fx_data_yahoo(ticker, start_date=dt.date(1980, 1, 1), end_date=dt.date.today())
        df = df.dropna()
        if df.empty:
            st.error("No data available.")
            st.stop()

        # -------- Time Frame Logic --------
        earliest_date = df['date'].min().date()
        latest_date = df['date'].max().date()
        if timeframe != "MAX":
            years = int(timeframe.replace("Y", ""))
            default_start_date = max(earliest_date, latest_date - dt.timedelta(days=365*years))
        else:
            default_start_date = earliest_date

        # Start & End Dates side by side
        date_col1, date_col2 = st.columns(2)
        with date_col1:
            start_date = st.date_input("Start Date", default_start_date, min_value=earliest_date, max_value=latest_date)
        with date_col2:
            end_date = st.date_input("End Date", latest_date, min_value=earliest_date, max_value=latest_date)

        if start_date > end_date:
            st.warning("Start date cannot be after end date.")
            st.stop()

        st.markdown("</div>", unsafe_allow_html=True)

    with col2:
        # -------- Commentary --------
        commentary = {
            # Major FX Pairs
            "EUR/USD": (
                "The EUR/USD currency pair reflects the relative economic performance, interest rate expectations, and monetary policy outlooks of the Eurozone versus the U.S. "
                "Movements are influenced by ECB and Federal Reserve decisions, economic data releases, and global risk sentiment."
            ),

            "GBP/USD": (
                "The GBP/USD pair is influenced by UK economic indicators, Bank of England policy decisions, and U.S. economic conditions. "
                "It often reacts to interest rate differentials, inflation data, and political developments in both regions."
            ),

            "USD/JPY": (
                "The USD/JPY pair is sensitive to U.S. Treasury yields, Bank of Japan policy, and global risk sentiment. "
                "It is often used as a proxy for risk appetite, with the yen typically strengthening in periods of market uncertainty."
            ),

            "EUR/GBP": (
                "The EUR/GBP reflects diverging economic conditions and monetary policy outlooks between the Eurozone and the UK. "
                "It is influenced by interest rate expectations, trade developments, and relative growth trends."
            ),

            "EUR/JPY": (
                "The EUR/JPY pair is driven by differences in ECB and BoJ monetary policy, as well as global risk appetite. "
                "It tends to rise when the euro strengthens or global risk sentiment improves, and fall during market uncertainty."
            ),

            "GBP/JPY": (
                "The GBP/JPY is highly sensitive to global risk sentiment and monetary policy differences between the UK and Japan. "
                "It is often used as a barometer for risk-on or risk-off market conditions."
            ),

            "DXY": (
                "The DXY (U.S. Dollar Index) measures the overall strength of the USD against a basket of major currencies. "
                "It reacts to U.S. interest rate expectations, economic data, geopolitical developments, and global risk sentiment."
            )
        }


        st.markdown(
            f"""
            <div style="
                position: relative;
                top: -10px;
                margin-left: 30px;
                font-size:19px;
                font-family: 'Arial Bold';
                font-weight:normal;
                color:#333';
            ">
                {commentary.get(indicator, "")}
            </div>
            """,
            unsafe_allow_html=True
        )

        # Filter by selected dates
        df_filtered = df[(df['date'] >= pd.to_datetime(start_date)) &
                         (df['date'] <= pd.to_datetime(end_date))]

        # Detect quarterly data
        quarterly = False
        if df_filtered.shape[0] > 1:
            avg_days = (df_filtered['date'].diff().dropna().dt.days.mean())
            if avg_days >= 80:
                quarterly = True

        # Plot chart
        delta_type_arg = None if delta_type == "Off" else delta_type.lower()
        hover_style = "delta" if delta_type_arg is not None else "none"

        fig = plot_chart(
            df_filtered,
            title,
            chart_type,
            hover_style=hover_style,
            delta_type=delta_type_arg,
            date_format="quarterly" if quarterly else "daily",
            show_markers=False
        )

        if quarterly:
            tickvals = df_filtered[df_filtered['date'].dt.quarter == 4]['date']
            ticktext = df_filtered[df_filtered['date'].dt.quarter == 4].dt.to_period('Q').apply(lambda x: f"Q{x.quarter} {x.year}")
            fig.update_xaxes(tickmode='array', tickvals=tickvals, ticktext=ticktext)

        fig.update_layout(
            hoverlabel=dict(
                font_size=13,
                font_color="black",
                font_family="Arial"
            )
        )

        # -------- Display Chart --------
        st.plotly_chart(
            fig,
            use_container_width=True,
            config={
                "displayModeBar": True,
                "displaylogo": False,
                "modeBarButtonsToAdd": ["toImage", "resetScale2d", "zoom2d", "pan2d"],
                "modeBarButtonsToRemove": ["lasso2d", "select2d"]
            }
        )

        # -------- CSV Download --------
        csv_data = df_filtered.to_csv(index=False)
        st.download_button(
            label="📥 Download CSV",
            data=csv_data,
            file_name=f"{indicator.replace('/', '-')}_data.csv",
            mime="text/csv"
        )


# ==============================
# 📊 COMPARE TAB (Enhanced Hover + Delta Type + Bold Axis + Black Lines)
# ==============================
if page == "Compare":
    col1, col2 = st.columns([1, 5])

    with col1:
        # --------------------------
        # Organize indicator options by group
        # --------------------------
        indicator_groups = {
            "USA": {
                "Interest Rate": "usa_rate",
                "CPI YoY %": "usa_cpi",
                "Core CPI YoY": "usa_core_cpi",
                "GDP QoQ %": "usa_gdp",
                "Unemployment Rate": "usa_unemp",
                "Average Hourly Earnings YoY": "usa_ahe",
                "Core PCE YoY": "usa_core_pce",
                "Core PPI YoY": "usa_core_ppi",
                "Housing Starts MoM": "usa_housing",
                "ISM Manufacturing PMI": "usa_ism_manu",
                "ISM Services PMI": "usa_ism_serv",
                "JOLTS Job Openings": "usa_jolts",
                "Michigan Consumer Sentiment": "usa_michigan",
                "Non Farm Payrolls": "usa_nfp",
                "PCE YoY": "usa_pce",
                "PPI YoY": "usa_ppi",
                "Retail Sales MoM": "usa_retail",
                "Trade Balance": "usa_trade"
            },
            "UK": {
                "Interest Rate": "uk_rate",
                "CPI YoY %": "uk_cpi",
                "GDP QoQ %": "uk_gdp",
                "Unemployment Rate": "uk_unemp"
                
            },
            "Japan": {
                "Interest Rate": "jp_rate",
                "CPI YoY %": "jp_cpi",
                "GDP QoQ %": "jp_gdp",
                "Unemployment Rate": "jp_unemp"
                
            },
            "Euro": {
                "Interest Rate": "eu_rate",
                "CPI YoY %": "eu_cpi",
                "GDP QoQ %": "eu_gdp",
                "Unemployment Rate": "eu_unemp"
                
            },

            "FX": {"EUR/USD": "eurusd", "GBP/USD": "gbpusd", "USD/JPY": "usdjpy", "DXY": "dxy"},
            
            "Equities": {
                "S&P 500": "eq_sp500",
                "NASDAQ": "eq_nasdaq",
                "Dow Jones": "eq_dow",
                "FTSE 100": "eq_ftse",
                "Nikkei 225": "eq_nikkei",
                "DAX": "eq_dax",
                "MSCI Emerging Markets ETF": "eq_msci_em",
                "VIX": "eq_vix"
            },
            "Stocks": {
                "Apple": "st_aapl",
                "Amazon": "st_amzn",
                "Meta": "st_meta",
                "Alphabet (Google)": "st_googl",
                "Nvidia": "st_nvda",
                "Microsoft": "st_msft",
                "Tesla": "st_tsla"
            },
            "Commodities": {
                "Gold": "cmd_gold",
                "Silver": "cmd_silver",
                "Crude Oil (WTI)": "cmd_wti",
                "Brent Oil": "cmd_brent",
                "Natural Gas": "cmd_ng",
                "Wheat": "cmd_wheat",
                "Copper": "cmd_copper",
                "Corn": "cmd_corn",
                "Soybeans": "cmd_soy"
            },
            "Bonds": {
                # U.S. Treasuries
                "US 1M Yield": "usa_1m",
                "US 3M Yield": "usa_3m",
                "US 6M Yield": "usa_6m",
                "US 1Y Yield": "usa_1y",
                "US 2Y Yield": "usa_2y",
                "US 3Y Yield": "usa_3y",
                "US 5Y Yield": "usa_5y",
                "US 7Y Yield": "usa_7y",
                "US 10Y Yield": "usa_10y",
                "US 20Y Yield": "usa_20y",
                "US 30Y Yield": "usa_30y",

                # UK Gilts
                "UK 2Y Gilt Yield": "uk_2y",
                "UK 10Y Gilt Yield": "uk_10y",

                # Japan JGBs
                "Japan 2Y JGB Yield": "jp_2y",
                "Japan 10Y JGB Yield": "jp_10y",

                # Euro Area Bonds
                "Euro 2Y Bond Yield": "eu_2y",
                "Euro 10Y Bond Yield": "eu_10y"
            },
            "Crypto": {
                "Bitcoin": "crypto_btc",
                "Ethereum": "crypto_eth"
            }
        }
           
        # --------------------------
        # Indicator selection
        # --------------------------
        group1 = st.selectbox("Select Group for Indicator 1", list(indicator_groups.keys()), key="group1")
        indicator1_label = st.selectbox("Select Indicator 1", list(indicator_groups[group1].keys()), key="indicator1")
        indicator1_code = indicator_groups[group1][indicator1_label]

        group2 = st.selectbox("Select Group for Indicator 2", list(indicator_groups.keys()), key="group2")
        indicator2_options = list(indicator_groups[group2].keys())
        if group1 == group2:
            indicator2_options = [opt for opt in indicator2_options if opt != indicator1_label]
        indicator2_label = st.selectbox("Select Indicator 2", indicator2_options, key="indicator2")
        indicator2_code = indicator_groups[group2][indicator2_label]

        # --------------------------
        # Delta type selection
        # --------------------------
        delta_type_option = st.selectbox("Delta Type", ["Daily % Change", "Cumulative % Change"], index=1)

        # --------------------------
        # Function loader
        # --------------------------
        def load_indicator_data(code):
            # USA
            if code == "usa_rate": return get_usa_interest_rate_data()
            if code == "usa_cpi": return get_usa_cpi_yoy_data()
            if code == "usa_core_cpi": return get_usa_core_cpi_yoy_data()
            if code == "usa_gdp": return get_usa_gdp_qoq_data()
            if code == "usa_unemp": return get_usa_unemployment_rate_data()
            if code == "usa_ahe": return get_usa_average_hourly_earnings_yoy_data()
            if code == "usa_core_pce": return get_usa_core_pce_yoy_data()
            if code == "usa_core_ppi": return get_usa_core_ppi_yoy_data()
            if code == "usa_housing": return get_usa_housing_starts_mom_data()
            if code == "usa_ism_manu": return get_usa_ism_manufacturing_pmi_data()
            if code == "usa_ism_serv": return get_usa_ism_services_pmi_data()
            if code == "usa_jolts": return get_usa_jolts_job_openings_data()
            if code == "usa_michigan": return get_usa_michigan_consumer_sentiment_data()
            if code == "usa_nfp": return get_usa_nfp_data()
            if code == "usa_pce": return get_usa_pce_yoy_data()
            if code == "usa_ppi": return get_usa_ppi_yoy_data()
            if code == "usa_retail": return get_usa_retail_sales_mom_data()
            if code == "usa_trade": return get_usa_trade_balance_data()

            # Yields
            if code == "usa_1m": return get_usa_1mo_yield_data()
            if code == "usa_3m": return get_usa_3mo_yield_data()
            if code == "usa_6m": return get_usa_6mo_yield_data()
            if code == "usa_1y": return get_usa_1yr_yield_data()
            if code == "usa_2y": return get_usa_2yr_yield_data()
            if code == "usa_3y": return get_usa_3yr_yield_data()
            if code == "usa_5y": return get_usa_5yr_yield_data()
            if code == "usa_7y": return get_usa_7yr_yield_data()
            if code == "usa_10y": return get_usa_10yr_yield_data()
            if code == "usa_20y": return get_usa_20yr_yield_data()
            if code == "usa_30y": return get_usa_30yr_yield_data()


            # UK
            if code == "uk_rate": return get_uk_interest_rate_data()
            if code == "uk_cpi": return get_uk_cpi_yoy_data()
            if code == "uk_gdp": return get_uk_gdp_qoq_data()
            if code == "uk_unemp": return get_uk_unemployment_rate_data()
            if code == "uk_10y": return get_uk_10yr_yield_data()
            if code == "uk_2y": return get_uk_2yr_yield_data()

            # Japan
            if code == "jp_rate": return get_japan_interest_rate_data()
            if code == "jp_cpi": return get_japan_cpi_yoy_data()
            if code == "jp_gdp": return get_japan_gdp_qoq_data()
            if code == "jp_unemp": return get_japan_unemployment_rate_data()
            if code == "jp_10y": return get_japan_10yr_yield_data()
            if code == "jp_2y": return get_japan_2yr_yield_data()

            # Euro
            if code == "eu_rate": return get_euro_interest_rate_data()
            if code == "eu_cpi": return get_euro_cpi_yoy_data()
            if code == "eu_gdp": return get_euro_gdp_qoq_data()
            if code == "eu_unemp": return get_euro_unemployment_rate_data()
            if code == "eu_10y": return get_euro_10yr_yield_data()
            if code == "eu_2y": return get_euro_2yr_yield_data()

            # FX
            if code == "eurusd": return get_fx_data_yahoo("EURUSD=X", start_date=dt.date(1980,1,1), end_date=dt.date.today())
            if code == "gbpusd": return get_fx_data_yahoo("GBPUSD=X", start_date=dt.date(1980,1,1), end_date=dt.date.today())
            if code == "usdjpy": return get_fx_data_yahoo("USDJPY=X", start_date=dt.date(1980,1,1), end_date=dt.date.today())
            if code == "dxy": return get_fx_data_yahoo("DX-Y.NYB", start_date=dt.date(1980,1,1), end_date=dt.date.today())
            
            # Equities
            if code == "eq_sp500": return get_fx_data_yahoo("^GSPC", start_date=dt.date(1980,1,1), end_date=dt.date.today())
            if code == "eq_nasdaq": return get_fx_data_yahoo("^IXIC", start_date=dt.date(1980,1,1), end_date=dt.date.today())
            if code == "eq_dow": return get_fx_data_yahoo("^DJI", start_date=dt.date(1980,1,1), end_date=dt.date.today())
            if code == "eq_ftse": return get_fx_data_yahoo("^FTSE", start_date=dt.date(1980,1,1), end_date=dt.date.today())
            if code == "eq_nikkei": return get_fx_data_yahoo("^N225", start_date=dt.date(1980,1,1), end_date=dt.date.today())
            if code == "eq_dax": return get_fx_data_yahoo("^GDAXI", start_date=dt.date(1980,1,1), end_date=dt.date.today())
            if code == "eq_msci_em": return get_fx_data_yahoo("EEM", start_date=dt.date(1980,1,1), end_date=dt.date.today())
            if code == "eq_vix": return get_fx_data_yahoo("^VIX", start_date=dt.date(1980,1,1), end_date=dt.date.today())

            # Stocks
            if code == "st_aapl": return get_fx_data_yahoo("AAPL", start_date=dt.date(1980,1,1), end_date=dt.date.today())
            if code == "st_amzn": return get_fx_data_yahoo("AMZN", start_date=dt.date(1980,1,1), end_date=dt.date.today())
            if code == "st_meta": return get_fx_data_yahoo("META", start_date=dt.date(1980,1,1), end_date=dt.date.today())
            if code == "st_googl": return get_fx_data_yahoo("GOOGL", start_date=dt.date(1980,1,1), end_date=dt.date.today())
            if code == "st_nvda": return get_fx_data_yahoo("NVDA", start_date=dt.date(1980,1,1), end_date=dt.date.today())
            if code == "st_msft": return get_fx_data_yahoo("MSFT", start_date=dt.date(1980,1,1), end_date=dt.date.today())
            if code == "st_tsla": return get_fx_data_yahoo("TSLA", start_date=dt.date(1980,1,1), end_date=dt.date.today())

            # Commodities
            if code == "cmd_gold": return get_fx_data_yahoo("GC=F", start_date=dt.date(1980,1,1), end_date=dt.date.today())
            if code == "cmd_silver": return get_fx_data_yahoo("SI=F", start_date=dt.date(1980,1,1), end_date=dt.date.today())
            if code == "cmd_wti": return get_fx_data_yahoo("CL=F", start_date=dt.date(1980,1,1), end_date=dt.date.today())
            if code == "cmd_brent": return get_fx_data_yahoo("BZ=F", start_date=dt.date(1980,1,1), end_date=dt.date.today())
            if code == "cmd_ng": return get_fx_data_yahoo("NG=F", start_date=dt.date(1980,1,1), end_date=dt.date.today())
            if code == "cmd_wheat": return get_fx_data_yahoo("ZW=F", start_date=dt.date(1980,1,1), end_date=dt.date.today())
            if code == "cmd_copper": return get_fx_data_yahoo("HG=F", start_date=dt.date(1980,1,1), end_date=dt.date.today())
            if code == "cmd_corn": return get_fx_data_yahoo("ZC=F", start_date=dt.date(1980,1,1), end_date=dt.date.today())
            if code == "cmd_soy": return get_fx_data_yahoo("ZS=F", start_date=dt.date(1980,1,1), end_date=dt.date.today())
            
            # Crypto
            if code == "crypto_btc": return get_fx_data_yahoo("BTC-USD", start_date=dt.date(1980,1,1), end_date=dt.date.today())
            if code == "crypto_eth": return get_fx_data_yahoo("ETH-USD", start_date=dt.date(1980,1,1), end_date=dt.date.today())


            return pd.DataFrame()

        # --------------------------
        # Load & clean data
        # --------------------------
        df1 = load_indicator_data(indicator1_code).dropna()
        df2 = load_indicator_data(indicator2_code).dropna()
        df1 = df1.rename(columns={df1.columns[0]: "date", df1.columns[1]: "value"})
        df2 = df2.rename(columns={df2.columns[0]: "date", df2.columns[1]: "value"})
        df1['date'] = pd.to_datetime(df1['date'], errors='coerce')
        df2['date'] = pd.to_datetime(df2['date'], errors='coerce')
        df1 = df1.dropna(subset=['date'])
        df2 = df2.dropna(subset=['date'])

        # --------------------------
        # Timeframe & date selection
        # --------------------------
        df1_min, df1_max = df1['date'].min().date(), df1['date'].max().date()
        df2_min, df2_max = df2['date'].min().date(), df2['date'].max().date()
        latest_date = max(df1_max, df2_max)
        earliest_start = min(df1_min, df2_min)

        timeframe = st.selectbox("Select Timeframe", ["1Y", "3Y", "5Y", "10Y", "Max"], index=2)
        if timeframe == "1Y": default_start_date = latest_date - dt.timedelta(days=365)
        elif timeframe == "3Y": default_start_date = latest_date - dt.timedelta(days=365*3)
        elif timeframe == "5Y": default_start_date = latest_date - dt.timedelta(days=365*5)
        elif timeframe == "10Y": default_start_date = latest_date - dt.timedelta(days=365*10)
        else: default_start_date = earliest_start
        default_start_date = max(earliest_start, default_start_date)

        start_date = st.date_input("Start Date", default_start_date, min_value=earliest_start, max_value=latest_date)
        end_date = st.date_input("End Date", latest_date, min_value=earliest_start, max_value=latest_date)
        if start_date > end_date:
            st.warning("Start date cannot be after end date.")
            st.stop()

    with col2:
        # --------------------------
        # Filter by date
        # --------------------------
        df1_filtered = df1[(df1['date'] >= pd.to_datetime(start_date)) & (df1['date'] <= pd.to_datetime(end_date))]
        df2_filtered = df2[(df2['date'] >= pd.to_datetime(start_date)) & (df2['date'] <= pd.to_datetime(end_date))]
        if df1_filtered.empty or df2_filtered.empty:
            st.warning("Not enough data for this date range.")
            st.stop()

        latest_val_1 = df1_filtered.iloc[-1]['value']
        latest_val_2 = df2_filtered.iloc[-1]['value']
        def format_val(v): return f"{v:.4f}" if isinstance(v, float) else str(v)
        title_str = (f"{group1}: {indicator1_label} (Latest: {format_val(latest_val_1)}) "
                     f"vs {group2}: {indicator2_label} (Latest: {format_val(latest_val_2)})")

        # --------------------------
        # Detect quarterly/monthly/daily
        # --------------------------
        def is_quarterly(df):
            if df.shape[0] > 1:
                avg_days = df['date'].diff().dropna().dt.days.mean()
                return avg_days >= 80
            return False
        quarterly = is_quarterly(df1_filtered) or is_quarterly(df2_filtered)

        def is_monthly(df):
            if df.shape[0] > 1:
                avg_days = df['date'].diff().dropna().dt.days.mean()
                return 27 <= avg_days <= 32
            return False
        monthly = is_monthly(df1_filtered) or is_monthly(df2_filtered)

        # --------------------------
        # Detect if indicators are same type
        # --------------------------
        def same_type(ind1, ind2): return ind1.split()[1:] == ind2.split()[1:]
        same_group = group1 == group2
        unify_axis = same_group and group1 not in ["FX", "Equities", "Stocks", "Commodities", "Crypto"]


        # --------------------------
        # Calculate delta safely
        # --------------------------

        if delta_type_option == "Daily % Change":
            for df_ in [df1_filtered, df2_filtered]:
                df_['delta'] = df_['value'].pct_change() * 100
                df_['delta_str'] = df_['delta'].apply(lambda x: f"▲ {x:.2f}%" if x > 0 else (f"▼ {abs(x):.2f}%" if pd.notnull(x) and x < 0 else "— 0.00%"))
                df_['delta_color'] = df_['delta'].apply(lambda x: "green" if x > 0 else ("red" if x < 0 else "gray"))
        elif delta_type_option == "Cumulative % Change":
            for df_ in [df1_filtered, df2_filtered]:
                df_['delta'] = np.where(df_['value'].iloc[0] == 0, 0, (df_['value'] / df_['value'].iloc[0] - 1) * 100)
                df_['delta_str'] = df_['delta'].apply(lambda x: f"▲ {x:.2f}%" if x > 0 else (f"▼ {abs(x):.2f}%" if pd.notnull(x) and x < 0 else "— 0.00%"))
                df_['delta_color'] = df_['delta'].apply(lambda x: "green" if x > 0 else ("red" if x < 0 else "gray"))

        # --------------------------
        # Hover label formatting
        # --------------------------
        for df_ in [df1_filtered, df2_filtered]:
            if 'hover_label' not in df_:
                df_['hover_label'] = df_['date'].dt.strftime("%d %b %Y")

        # --------------------------
        # Plotting
        # --------------------------
        

        fig = go.Figure()

        # Decide if dual-axis needed
        same_group = group1 == group2
        unify_axis = same_group and group1 not in ["FX", "Equities", "Stocks", "Commodities", "Crypto"]

        # Plot traces
        if delta_type_option == "Daily Delta Spread":
            # Only one trace needed
            fig.add_trace(go.Scatter(
                x=df1_filtered['date'],
                y=df1_filtered['value'],
                mode="lines",
                name=f"{group1}: {indicator1_label} - {group2}: {indicator2_label} (Spread)",
                customdata=df1_filtered[['hover_label', 'delta_str', 'delta_color']],
                hovertemplate=(
                    "<span style='color:black; font-size:16px'><b>%{customdata[0]}</b></span><br>"
                    "<span style='color:black; font-size:16px'>%{y:.2f}</span><br>"
                    "<span style='color:%{customdata[2]}; font-weight:bold; font-size:16px'>%{customdata[1]}</span>"
                    "<extra></extra>"
                )
            ))
        else:
            # Two normal traces
            for idx, (df_, name, axis) in enumerate([
                (df1_filtered, f"{group1}: {indicator1_label}", "y1"),
                (df2_filtered, f"{group2}: {indicator2_label}", "y1" if unify_axis else "y2")
            ]):
                fig.add_trace(go.Scatter(
                    x=df_['date'],
                    y=df_['value'],
                    mode="lines",
                    name=name,
                    yaxis=axis,
                    customdata=df_[['hover_label', 'delta_str', 'delta_color']],
                    hovertemplate=(
                        "<span style='color:black; font-size:16px'><b>%{customdata[0]}</b></span><br>"
                        "<span style='color:black; font-size:16px'>%{y:.2f}</span><br>"
                        "<span style='color:%{customdata[2]}; font-weight:bold; font-size:16px'>%{customdata[1]}</span>"
                        "<extra></extra>"
                    )
                ))

        # --------------------------
        # Layout
        # --------------------------
        axis_tickfont = dict(size=14, family="Arial Bold", color="black")
        axis_title_font = dict(size=16, family="Arial Bold", color="black")

        if unify_axis or delta_type_option == "Daily Delta Spread":
            fig.update_layout(
                title=f"{group1}: {indicator1_label} vs {group2}: {indicator2_label}",
                xaxis=dict(title="", tickfont=axis_tickfont, linecolor='black', linewidth=2, showline=True, title_font=axis_title_font),
                yaxis=dict(title="Value / Spread", side="left", tickfont=axis_tickfont, title_font=axis_title_font),
                template="plotly_white",
                font=dict(color="black"),
                legend=dict(x=0.01, y=1.1, orientation="h"),
                height=600
            )
        else:
            fig.update_layout(
                title=f"{group1}: {indicator1_label} vs {group2}: {indicator2_label}",
                xaxis=dict(title="", tickfont=axis_tickfont, linecolor='black', linewidth=2, showline=True, title_font=axis_title_font),
                yaxis=dict(title=f"{group1}: {indicator1_label}", side="left", tickfont=axis_tickfont, title_font=axis_title_font),
                yaxis2=dict(title=f"{group2}: {indicator2_label}", overlaying="y", side="right",
                            showgrid=False, tickfont=axis_tickfont, title_font=axis_title_font),
                template="plotly_white",
                font=dict(color="black"),
                legend=dict(x=0.01, y=1.1, orientation="h"),
                height=600
            )

        st.plotly_chart(
            fig,
            use_container_width=True,
            config={
                "displayModeBar": True,
                "displaylogo": False,
                "modeBarButtonsToAdd": ["toImage", "resetScale2d", "zoom2d", "pan2d"],
                "modeBarButtonsToRemove": ["lasso2d", "select2d"]
            }
        )


# -------- Economic Calendar Tab --------
if page == "Calendar":

    st.header("📅 Economic Calendar")

    # Load CSV
    df = pd.read_csv("economic_calendar.csv", parse_dates=["Date"])

    # Convert Country and Impact to string if not already
    df['Country'] = df['Country'].astype(str)
    df['Impact'] = df['Impact'].astype(str)

    # Extract months available for filtering
    df['Month'] = df['Date'].dt.strftime("%B %Y")
    months = df['Month'].unique().tolist()

    # Filter widgets
    selected_month = st.selectbox("Select Month", options=["All"] + months, index=0)
    selected_country = st.multiselect("Filter by Country", options=sorted(df['Country'].unique()), default=sorted(df['Country'].unique()))
    selected_impact = st.multiselect("Filter by Impact Level", options=sorted(df['Impact'].unique()), default=sorted(df['Impact'].unique()))
    view_mode = st.selectbox("View Mode", ["Daily", "Weekly", "Monthly"])

    # Filter dataframe based on selections
    filtered_df = df.copy()
    if selected_month != "All":
        filtered_df = filtered_df[filtered_df['Month'] == selected_month]

    filtered_df = filtered_df[
        (filtered_df['Country'].isin(selected_country)) &
        (filtered_df['Impact'].isin(selected_impact))
    ]

    if filtered_df.empty:
        st.warning("No events found for the selected filters.")
        st.stop()

    # Function to render event card
    def render_event_card(row):
        date_str = row['Date'].strftime("%A %d %B")
        time_str = row['Time']
        country_str = row['Country']
        event_str = row['Event']
        impact_str = row['Impact']
        forecast = row['Forecast']
        previous = row['Previous']
        notes = row['Notes']

        impact_color = {
            "🔴 High": "#ff4d4d",
            "🟠 Medium": "#ffa500",
            "🟢 Low": "#32cd32"
        }.get(impact_str, "#888")

        card_html = f"""
        <div style="
            border: 1px solid #ddd;
            border-left: 6px solid {impact_color};
            padding: 15px 20px;
            margin-bottom: 15px;
            border-radius: 6px;
            box-shadow: 0 1px 4px rgba(0,0,0,0.1);
            background-color: #fafafa;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            ">
            <div style="font-weight: 600; font-size: 1.05rem; margin-bottom: 10px; color: #222; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
                <span style="margin-right: 12px;"><b>Date:</b> {date_str}</span> |
                <span style="margin: 0 12px;"><b>Time:</b> {time_str}</span> |
                <span style="margin: 0 12px;"><b>Country:</b> {country_str}</span> |
                <span style="margin: 0 12px; max-width: 300px; display: inline-block; vertical-align: middle; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" title="{event_str}"><b>Event:</b> {event_str}</span> |
                <span style="margin-left: 12px; color:{impact_color}; font-weight:bold;"><b>Impact:</b> {impact_str}</span>
            </div>
            <div style="font-size: 0.9rem; color: #444; margin-bottom: 4px;">
                <b>Forecast:</b> {forecast} &nbsp;&nbsp; <b>Previous:</b> {previous}
            </div>
            <div style="font-size: 0.9rem; color: #555;">
                <b>Notes:</b> {notes}
            </div>
        </div>
        """
        st.markdown(card_html, unsafe_allow_html=True)

    # Group and display by view mode
    if view_mode == "Daily":
        grouped = filtered_df.sort_values("Date").groupby("Date")

        for date, group in grouped:
            st.subheader(date.strftime("%A, %d %B %Y"))
            for _, row in group.iterrows():
                render_event_card(row)

    elif view_mode == "Weekly":
        filtered_df['YearWeek'] = filtered_df['Date'].dt.strftime('%Y-%U')
        grouped = filtered_df.sort_values("Date").groupby("YearWeek")

        for yearweek, group in grouped:
            year, week_num = map(int, yearweek.split('-'))
            first_day = pd.to_datetime(f'{year}-W{week_num}-1', format='%Y-W%U-%w')
            last_day = first_day + pd.Timedelta(days=6)
            st.subheader(f"Week {week_num}, {year} ({first_day.strftime('%d %b')} - {last_day.strftime('%d %b')})")
            for _, row in group.iterrows():
                render_event_card(row)

    elif view_mode == "Monthly":
        grouped = filtered_df.sort_values("Date").groupby("Month")

        for month, group in grouped:
            st.subheader(month)
            for _, row in group.iterrows():
                render_event_card(row)
 
# -------- Equities Tab --------
if page == "Equities":
    col1, col2 = st.columns([1.5, 5])

    with col1:
        st.markdown("<div style='margin-top:-40px;'>", unsafe_allow_html=True)

        # -------- Indicator Groups --------
        indicator_groups = {
            "US": ["S&P 500", "NASDAQ", "Dow Jones", "VIX"],
            "Europe": ["FTSE 100", "DAX"],
            "Asia": ["Nikkei 225"],
            "ETFs": ["MSCI Emerging Markets ETF"]
        }

        # Category dropdown
        category = st.selectbox("Select Category", list(indicator_groups.keys()))

        # Indicator dropdown based on category
        indicator = st.selectbox("Select Indicator", indicator_groups[category])

        # -------- Chart Type + Timeframe side by side --------
        ct_col, tf_col = st.columns(2)
        with ct_col:
            chart_type = st.selectbox("Chart Type", ["Line", "Area", "Bar", "Step"])
        with tf_col:
            timeframe = st.selectbox("Time Frame", ["1Y", "3Y", "5Y", "10Y", "MAX"])

        # Delta Type (allow turning it off)
        delta_type = st.selectbox("Delta Type", ["Off", "Cumulative", "Daily"])

        # -------- Indicator Mapping --------
        equities_tickers = {
            "S&P 500": ("^GSPC", "S&P 500"),
            "NASDAQ": ("^IXIC", "NASDAQ"),
            "Dow Jones": ("^DJI", "Dow Jones"),
            "FTSE 100": ("^FTSE", "FTSE 100"),
            "Nikkei 225": ("^N225", "Nikkei 225"),
            "DAX": ("^GDAXI", "DAX"),
            "MSCI Emerging Markets ETF": ("EEM", "MSCI Emerging Markets ETF"),
            "VIX": ("^VIX", "VIX")
        }
        ticker, title = equities_tickers[indicator]

        # Load data
        df = get_fx_data_yahoo(ticker, start_date=dt.date(1980, 1, 1), end_date=dt.date.today())
        df = df.dropna()
        if df.empty:
            st.error("No data available.")
            st.stop()

        # -------- Time Frame Logic --------
        earliest_date = df['date'].min().date()
        latest_date = df['date'].max().date()
        if timeframe != "MAX":
            years = int(timeframe.replace("Y", ""))
            default_start_date = max(earliest_date, latest_date - dt.timedelta(days=365*years))
        else:
            default_start_date = earliest_date

        # -------- Start & End Dates side by side --------
        date_col1, date_col2 = st.columns(2)
        with date_col1:
            start_date = st.date_input("Start Date", default_start_date, min_value=earliest_date, max_value=latest_date)
        with date_col2:
            end_date = st.date_input("End Date", latest_date, min_value=earliest_date, max_value=latest_date)
        if start_date > end_date:
            st.warning("Start date must be before end date.")
            st.stop()

        st.markdown("</div>", unsafe_allow_html=True)

    with col2:
        # -------- Commentary --------
        commentary = {
            # U.S. Equities
            "S&P 500": (
                "The S&P 500 tracks the performance of 500 large-cap U.S. companies across various sectors. "
                "It is a key benchmark for the overall health of the U.S. equity market and is widely used for portfolio performance comparison."
            ),

            "NASDAQ": (
                "The NASDAQ Composite is a tech-heavy index representing stocks listed on the NASDAQ exchange. "
                "It is sensitive to technology sector trends, innovation cycles, and growth-oriented investor sentiment."
            ),

            "Dow Jones": (
                "The Dow Jones Industrial Average tracks 30 large U.S. industrial and blue-chip companies. "
                "It is often used as a barometer of U.S. corporate and economic performance, particularly for established firms."
            ),

            # UK Equities
            "FTSE 100": (
                "The FTSE 100 represents the 100 largest UK companies by market capitalization. "
                "It provides insight into the performance of the UK’s blue-chip sector and is influenced by domestic economic data and global market trends."
            ),

            # Japan & Europe Equities
            "Nikkei 225": (
                "The Nikkei 225 tracks 225 leading Japanese companies listed on the Tokyo Stock Exchange. "
                "It reflects Japan’s equity market performance and is influenced by domestic economic conditions, corporate earnings, and global trade."
            ),

            "DAX": (
                "The DAX tracks 40 major German companies listed on the Frankfurt Stock Exchange. "
                "It serves as a key indicator of German corporate and economic health and is sensitive to Eurozone economic developments."
            ),

            # Emerging Markets
            "MSCI Emerging Markets ETF": (
                "This ETF tracks equities in emerging market countries, providing broad exposure to developing economies. "
                "Performance is influenced by global growth trends, commodity prices, and investor risk appetite."
            ),

            # Volatility
            "VIX": (
                "The VIX, or Volatility Index, measures the market’s expectations of near-term volatility in the S&P 500. "
                "It is often referred to as the 'fear gauge,' rising during periods of uncertainty or market stress."
            )
        }


        st.markdown(
            f"""
            <div style="
                position: relative;
                top: -10px;
                margin-left: 30px;
                font-size:19px;
                font-family: 'Arial Bold';
                font-weight:normal;
                color:#333;
            ">
                {commentary.get(indicator, "")}
            </div>
            """,
            unsafe_allow_html=True
        )

        # -------- Filter Data by Date --------
        df_filtered = df[(df['date'] >= pd.to_datetime(start_date)) &
                         (df['date'] <= pd.to_datetime(end_date))]

        # Detect quarterly data
        quarterly = False
        if df_filtered.shape[0] > 1:
            avg_days = (df_filtered['date'].diff().dropna().dt.days.mean())
            if avg_days >= 80:  # ~quarter
                quarterly = True

        # -------- Plot Chart --------
        delta_type_arg = None if delta_type == "Off" else delta_type.lower()
        hover_style = "delta" if delta_type_arg is not None else "none"

        fig = plot_chart(
            df_filtered,
            title,
            chart_type,
            hover_style=hover_style,
            delta_type=delta_type_arg,
            date_format="quarterly" if quarterly else "daily",
            show_markers=False
        )

        if quarterly:
            tickvals = df_filtered[df_filtered['date'].dt.quarter == 4]['date']
            ticktext = df_filtered[df_filtered['date'].dt.quarter == 4].dt.to_period('Q').apply(lambda x: f"Q{x.quarter} {x.year}")
            fig.update_xaxes(tickmode='array', tickvals=tickvals, ticktext=ticktext)

        fig.update_layout(
            hoverlabel=dict(
                font_size=13,
                font_color="black",
                font_family="Arial"
            )
        )

        # -------- Display Chart --------
        st.plotly_chart(
            fig,
            use_container_width=True,
            config={
                "displayModeBar": True,
                "displaylogo": False,
                "modeBarButtonsToAdd": ["toImage", "resetScale2d", "zoom2d", "pan2d"],
                "modeBarButtonsToRemove": ["lasso2d", "select2d"]
            }
        )

        # -------- CSV Download --------
        csv_data = df_filtered.to_csv(index=False)
        st.download_button(
            label="📥 Download CSV",
            data=csv_data,
            file_name=f"{indicator.replace('/', '-')}_data.csv",
            mime="text/csv"
        )

        
# -------- Stocks Tab --------
if page == "Stocks":
    
    col1, col2 = st.columns([1, 5])

    with col1:
        st.markdown("<div style='margin-top:-40px;'>", unsafe_allow_html=True)

        # Select indicator and chart type
        indicator = st.selectbox("Select Indicator", [
            "Apple", "Amazon", "Meta", "Alphabet (Google)", "Nvidia", "Microsoft", "Tesla"
        ])
        chart_type = st.selectbox("Chart Type", ["Line", "Area", "Bar", "Step"])

        # Toggle for delta type
        delta_type = st.selectbox("Delta Type", ["Cumulative", "Daily"])

        # Map indicator to Yahoo ticker and chart title
        stock_tickers = {
            "Apple": ("AAPL", "Apple"),
            "Amazon": ("AMZN", "Amazon"),
            "Meta": ("META", "Meta"),
            "Alphabet (Google)": ("GOOGL", "Alphabet (Google)"),
            "Nvidia": ("NVDA", "Nvidia"),
            "Microsoft": ("MSFT", "Microsoft"),
            "Tesla":     ("TSLA", "Tesla")    
        }
        ticker, title = stock_tickers[indicator]

        # Load FX data
        df = get_fx_data_yahoo(ticker, start_date=dt.date(1980, 1, 1), end_date=dt.date.today())
        df = df.dropna()
        if df.empty:
            st.error("No data available.")
            st.stop()

        # Time frame selector
        earliest_date = df['date'].min().date()
        latest_date = df['date'].max().date()
        timeframe = st.selectbox("Time Frame", ["1Y", "3Y", "5Y", "10Y", "MAX"])
        if timeframe != "MAX":
            years = int(timeframe.replace("Y", ""))
            default_start_date = max(earliest_date, latest_date - dt.timedelta(days=365*years))
        else:
            default_start_date = earliest_date

        # Date inputs
        start_date = st.date_input("Start Date", default_start_date, min_value=earliest_date, max_value=latest_date)
        end_date = st.date_input("End Date", latest_date, min_value=earliest_date, max_value=latest_date)
        if start_date > end_date:
            st.warning("Start date must be before end date.")
            st.stop()

        st.markdown("</div>", unsafe_allow_html=True)

    with col2:
        # Commentary for each indicator
        commentary = {
            "Apple": (
                "Apple Inc. is a leading technology company known for its consumer electronics, software, and services, including the iPhone, Mac, and App Store. "
                "Its stock performance is influenced by product launches, innovation cycles, global consumer demand, and supply chain dynamics."
            ),

            "Amazon": (
                "Amazon.com Inc. is a global e-commerce and cloud computing leader. "
                "Its equity is sensitive to online retail trends, Amazon Web Services growth, consumer spending, and regulatory developments."
            ),

            "Meta": (
                "Meta Platforms Inc. (formerly Facebook) operates leading social media platforms, including Facebook, Instagram, and WhatsApp. "
                "Its performance is driven by advertising revenue, user engagement metrics, and developments in virtual/augmented reality."
            ),

            "Alphabet (Google)": (
                "Alphabet Inc., the parent company of Google, dominates global online search, digital advertising, and cloud computing. "
                "Its stock reacts to ad revenue trends, regulatory scrutiny, innovation in AI and cloud services, and overall internet usage growth."
            ),

            "Nvidia": (
                "Nvidia Corporation specializes in graphics processing units (GPUs) and AI computing technologies. "
                "Its stock is highly influenced by demand in gaming, AI, data centers, and broader semiconductor industry trends."
            ),

            "Microsoft": (
                "Microsoft Corporation is a leading technology company offering software, cloud computing, and hardware products. "
                "Key drivers include Windows and Office adoption, Azure cloud growth, enterprise demand, and AI integration."
            ),

            "Tesla": (
                "Tesla Inc. is a leading electric vehicle and clean energy company. "
                "Its stock performance is influenced by EV production and deliveries, technological innovation, regulatory incentives, and global adoption of sustainable energy solutions."
            )
        }

        # Display commentary above chart
        st.markdown(
            f"""
            <div style="
                position: relative;
                top: -20px;
                margin-left: 30px;
                font-size:22px;
                font-family: 'Arial Bold';
                font-weight:normal;
                color:#333;
            ">
                {commentary.get(indicator, "")}
            </div>
            """,
            unsafe_allow_html=True
        )

        # Filter data by selected date range
        df_filtered = df[(df['date'] >= pd.to_datetime(start_date)) & 
                         (df['date'] <= pd.to_datetime(end_date))]

        # Detect if quarterly data
        quarterly = False
        if df_filtered.shape[0] > 1:
            avg_days = (df_filtered['date'].diff().dropna().dt.days.mean())
            if avg_days >= 80:  # ~quarter
                quarterly = True

        # Plot chart with Bloomberg-style delta hover, no markers
        fig = plot_chart(
            df_filtered,
            title,
            chart_type,
            hover_style="delta",
            delta_type=delta_type.lower(),
            date_format="quarterly" if quarterly else "daily",
            show_markers=False
        )

        # For quarterly charts, show only Q4 labels
        if quarterly:
            tickvals = df_filtered[df_filtered['date'].dt.quarter == 4]['date']
            ticktext = df_filtered[df_filtered['date'].dt.quarter == 4].dt.to_period('Q').apply(lambda x: f"Q{x.quarter} {x.year}")
            fig.update_xaxes(tickmode='array', tickvals=tickvals, ticktext=ticktext)

        # Display chart with clean modebar
        st.plotly_chart(
            fig,
            use_container_width=True,
            config={
                "displayModeBar": True,
                "displaylogo": False,
                "modeBarButtonsToAdd": ["toImage", "resetScale2d", "zoom2d", "pan2d"],
                "modeBarButtonsToRemove": ["lasso2d", "select2d"]
            }
        )

        # --------------------- CSV Download (original) ---------------------
        csv_data = df_filtered.to_csv(index=False)
        st.download_button(
            label="📥 Download CSV",
            data=csv_data,
            file_name=f"{indicator.replace('/', '-')}_data.csv",
            mime="text/csv"
        )
        
# -------- Commodities Tab --------
if page == "Commodities":
    col1, col2 = st.columns([1.5, 5])

    with col1:
        st.markdown("<div style='margin-top:-40px;'>", unsafe_allow_html=True)

        # -------- Indicator Groups --------
        indicator_groups = {
            "Energy": ["Crude Oil", "Natural Gas", "Brent Oil"],
            "Metals": ["Gold", "Silver", "Copper"],
            "Agriculture": ["Wheat", "Corn", "Soybeans"]
        }

        # Category dropdown
        category = st.selectbox("Select Category", list(indicator_groups.keys()))

        # Indicator dropdown based on category
        indicator = st.selectbox("Select Indicator", indicator_groups[category])

        # -------- Chart Type + Timeframe side by side --------
        ct_col, tf_col = st.columns(2)
        with ct_col:
            chart_type = st.selectbox("Chart Type", ["Line", "Area", "Bar", "Step"])
        with tf_col:
            timeframe = st.selectbox("Time Frame", ["1Y", "3Y", "5Y", "10Y", "MAX"])

        # Delta Type (allow turning it off)
        delta_type = st.selectbox("Delta Type", ["Off", "Cumulative", "Daily"])

        # -------- Indicator Function Mapping --------
      
        indicator_map = {
            "Crude Oil": (lambda: get_fx_data_yahoo("CL=F"), "daily", None),
            "Natural Gas": (lambda: get_fx_data_yahoo("NG=F"), "daily", None),
            "Brent Oil": (lambda: get_fx_data_yahoo("BZ=F"), "daily", None),
            "Gold": (lambda: get_fx_data_yahoo("GC=F"), "daily", None),
            "Silver": (lambda: get_fx_data_yahoo("SI=F"), "daily", None),
            "Copper": (lambda: get_fx_data_yahoo("HG=F"), "daily", None),
            "Wheat": (lambda: get_fx_data_yahoo("ZW=F"), "daily", None),
            "Corn": (lambda: get_fx_data_yahoo("ZC=F"), "daily", None),
            "Soybeans": (lambda: get_fx_data_yahoo("ZS=F"), "daily", None)
        }


        # Load data dynamically
        func, date_format, tickformat_override = indicator_map[indicator]
        df = func()
        df = df.dropna()
        if df.empty:
            st.error("No data available.")
            st.stop()

        # -------- Time Frame Logic --------
        earliest_date = df['date'].min().date()
        latest_date = df['date'].max().date()
        if timeframe != "MAX":
            years = int(timeframe.replace("Y", ""))
            default_start_date = max(earliest_date, latest_date - dt.timedelta(days=365*years))
        else:
            default_start_date = earliest_date

        # -------- Start & End Dates side by side --------
        date_col1, date_col2 = st.columns(2)
        with date_col1:
            start_date = st.date_input("Start Date", default_start_date, min_value=earliest_date, max_value=latest_date)
        with date_col2:
            end_date = st.date_input("End Date", latest_date, min_value=earliest_date, max_value=latest_date)

        if start_date > end_date:
            st.warning("Start date cannot be after end date.")
            st.stop()

        st.markdown("</div>", unsafe_allow_html=True)

    with col2:
        # -------- Commentary --------
        commentary = {
            # Energy Commodities
            "Crude Oil": (
                "Crude oil prices reflect global supply and demand dynamics, OPEC production decisions, and geopolitical risks. "
                "They are influenced by global economic growth, inventory levels, and disruptions in major producing regions."
            ),

            "Natural Gas": (
                "Natural gas prices are sensitive to weather patterns, seasonal heating/cooling demand, storage levels, and energy consumption trends. "
                "They are also influenced by pipeline infrastructure, liquefied natural gas (LNG) exports, and policy regulations."
            ),

            "Brent Oil": (
                "Brent crude oil is a major international benchmark, reflecting global oil market trends. "
                "It is influenced by production in Europe, Africa, and the Middle East, as well as global demand forecasts."
            ),

            # Precious Metals
            "Gold": (
                "Gold is a safe-haven asset that reacts to inflation expectations, USD strength, interest rates, and geopolitical uncertainty. "
                "It is widely used for portfolio hedging and wealth preservation."
            ),

            "Silver": (
                "Silver serves both as an industrial metal and a store of value. "
                "Its price is influenced by industrial demand, investor sentiment, and monetary policy conditions."
            ),

            # Industrial Metals
            "Copper": (
                "Copper is a key industrial metal whose price reflects global manufacturing activity and economic growth. "
                "It is sensitive to construction, infrastructure demand, and supply disruptions in major producing countries."
            ),

            # Agricultural Commodities
            "Wheat": (
                "Wheat prices respond to global crop yields, weather conditions, planting and harvesting cycles, and international demand. "
                "They are also affected by export policies and geopolitical events impacting major wheat-producing countries."
            ),

            "Corn": (
                "Corn prices are influenced by planting and harvest cycles, ethanol production demand, livestock feed requirements, and weather conditions. "
                "Global trade policies and U.S. crop reports play a key role in price fluctuations."
            ),

            "Soybeans": (
                "Soybean prices track agricultural supply, global consumption, and trade policies. "
                "They are impacted by crop yields, weather events, biofuel demand, and geopolitical developments affecting major exporters."
            )
        }


        st.markdown(
            f"""
            <div style="
                position: relative;
                top: -10px;
                margin-left: 30px;
                font-size:19px;
                font-family: 'Arial Bold';
                font-weight:normal;
                color:#333;
            ">
                {commentary.get(indicator, "")}
            </div>
            """,
            unsafe_allow_html=True
        )

        # -------- Filter Data by Date --------
        df_filtered = df[(df['date'] >= pd.to_datetime(start_date)) &
                         (df['date'] <= pd.to_datetime(end_date))]

        # Detect if quarterly data (rare for commodities)
        quarterly = False
        if df_filtered.shape[0] > 1:
            avg_days = (df_filtered['date'].diff().dropna().dt.days.mean())
            if avg_days >= 80:
                quarterly = True

        # -------- Plot Chart --------
        delta_type_arg = None if delta_type == "Off" else delta_type.lower()
        hover_style = "delta" if delta_type_arg is not None else "none"

        fig = plot_chart(
            df_filtered,
            indicator,
            chart_type,
            hover_style=hover_style,
            delta_type=delta_type_arg,
            date_format="quarterly" if quarterly else date_format,
            tickformat_override=tickformat_override,
            show_markers=False
        )

        if quarterly:
            tickvals = df_filtered[df_filtered['date'].dt.quarter == 4]['date']
            ticktext = df_filtered[df_filtered['date'].dt.quarter == 4].dt.to_period('Q').apply(lambda x: f"Q{x.quarter} {x.year}")
            fig.update_xaxes(tickmode='array', tickvals=tickvals, ticktext=ticktext)

        fig.update_layout(
            hoverlabel=dict(
                font_size=13,
                font_color="black",
                font_family="Arial"
            )
        )

        # -------- Display Chart --------
        st.plotly_chart(
            fig,
            use_container_width=True,
            config={
                "displayModeBar": True,
                "displaylogo": False,
                "modeBarButtonsToAdd": ["toImage", "resetScale2d", "zoom2d", "pan2d"],
                "modeBarButtonsToRemove": ["lasso2d", "select2d"]
            }
        )

        # -------- CSV Download --------
        csv_data = df_filtered.to_csv(index=False)
        st.download_button(
            label="📥 Download CSV",
            data=csv_data,
            file_name=f"Commodities_{indicator.replace(' ', '_')}_data.csv",
            mime="text/csv"
        )

        
# -------- Bonds Tab --------
if page == "Bonds":
    col1, col2 = st.columns([1.5, 5])

    with col1:
        st.markdown("<div style='margin-top:-40px;'>", unsafe_allow_html=True)

        # -------- Bond Categories --------
        bond_groups = {
            "US Treasuries": ["US 2Y", "US 10Y"],
            "UK Gilts": ["UK 2Y", "UK 10Y"],
            "Japan JGBs": ["Japan 2Y", "Japan 10Y"],
            "Euro Bonds": ["Euro 2Y", "Euro 10Y"]
        }

        # Category dropdown
        category = st.selectbox("Select Country/Group", list(bond_groups.keys()))

        # Indicator dropdown based on category
        indicator = st.selectbox("Select Bond", bond_groups[category])

        # -------- Chart Type + Time Frame side by side --------
        ct_col, tf_col = st.columns(2)
        with ct_col:
            chart_type = st.selectbox("Chart Type", ["Line", "Area", "Bar", "Step"])
        with tf_col:
            timeframe = st.selectbox("Time Frame", ["1Y", "3Y", "5Y", "10Y", "MAX"])

        # Delta Type (allow turning it off)
        delta_type = st.selectbox("Delta Type", ["Off", "Cumulative", "Daily"])

        # -------- Bond Indicator Mapping --------
        bond_map = {
            "US 2Y": (get_usa_2yr_yield_data, "US 2-Year Treasury Yield"),
            "US 10Y": (get_usa_10yr_yield_data, "US 10-Year Treasury Yield"),
            "UK 2Y": (get_uk_2yr_yield_data, "UK 2-Year Gilt Yield"),
            "UK 10Y": (get_uk_10yr_yield_data, "UK 10-Year Gilt Yield"),
            "Japan 2Y": (get_japan_2yr_yield_data, "Japan 2-Year JGB Yield"),
            "Japan 10Y": (get_japan_10yr_yield_data, "Japan 10-Year JGB Yield"),
            "Euro 2Y": (get_euro_2yr_yield_data, "Euro 2-Year Yield"),
            "Euro 10Y": (get_euro_10yr_yield_data, "Euro 10-Year Yield")
        }

        data_func, title = bond_map[indicator]

        # Load bond data
        df = data_func()
        df = df.dropna()
        if df.empty:
            st.error("No data available.")
            st.stop()

        # -------- Time Frame Logic --------
        earliest_date = df['date'].min().date()
        latest_date = df['date'].max().date()
        if timeframe != "MAX":
            years = int(timeframe.replace("Y", ""))
            default_start_date = max(earliest_date, latest_date - dt.timedelta(days=365*years))
        else:
            default_start_date = earliest_date

        # -------- Start & End Dates side by side --------
        date_col1, date_col2 = st.columns(2)
        with date_col1:
            start_date = st.date_input("Start Date", default_start_date, min_value=earliest_date, max_value=latest_date)
        with date_col2:
            end_date = st.date_input("End Date", latest_date, min_value=earliest_date, max_value=latest_date)

        if start_date > end_date:
            st.warning("Start date must be before end date.")
            st.stop()

        st.markdown("</div>", unsafe_allow_html=True)

    with col2:
        # -------- Commentary --------
        commentary = {
            # U.S. Treasuries
            "US 2Y": (
                "The US 2-Year Treasury yield reflects short-term interest rate expectations and Federal Reserve policy guidance. "
                "It is highly sensitive to Fed rate changes, inflation data, and economic forecasts, serving as a barometer for near-term monetary policy."
            ),

            "US 10Y": (
                "The US 10-Year Treasury yield signals long-term growth and inflation expectations in the U.S. economy. "
                "It is influenced by economic data, Federal Reserve policy, and investor sentiment regarding future inflation and fiscal policy."
            ),

            # UK Gilts
            "UK 2Y": (
                "The UK 2-Year Gilt yield responds primarily to Bank of England policy guidance and short-term rate expectations. "
                "It reflects market sentiment on near-term monetary policy and economic conditions in the UK."
            ),

            "UK 10Y": (
                "The UK 10-Year Gilt yield indicates long-term expectations for inflation, growth, and fiscal stability. "
                "It is influenced by government borrowing, economic data, and Bank of England policy signals."
            ),

            # Japan Government Bonds
            "Japan 2Y": (
                "The Japan 2-Year JGB yield tracks short-term expectations for Bank of Japan policy. "
                "It is closely tied to BoJ rate guidance, domestic economic conditions, and market sentiment."
            ),

            "Japan 10Y": (
                "The Japan 10-Year JGB yield reflects long-term growth and inflation expectations in Japan. "
                "It is influenced by BoJ policy, government debt issuance, and global economic trends."
            ),

            # Eurozone Bonds
            "Euro 2Y": (
                "The Euro 2-Year government bond yield reflects ECB policy signals and short-term interest rate expectations across the Eurozone. "
                "It is sensitive to ECB guidance, inflation data, and economic activity."
            ),

            "Euro 10Y": (
                "The Euro 10-Year government bond yield signals long-term growth and inflation expectations in the Eurozone. "
                "It is influenced by fiscal policies, ECB strategy, and investor demand for euro-denominated debt."
            )
        }


        st.markdown(
            f"""
            <div style="
                position: relative;
                top: -10px;
                margin-left: 30px;
                font-size:19px;
                font-family: 'Arial Bold';
                font-weight:normal;
                color:#333;
            ">
                {commentary.get(indicator, "")}
            </div>
            """,
            unsafe_allow_html=True
        )

        # -------- Filter Data by Date --------
        df_filtered = df[(df['date'] >= pd.to_datetime(start_date)) &
                         (df['date'] <= pd.to_datetime(end_date))]

        # Detect quarterly data
        quarterly = False
        if df_filtered.shape[0] > 1:
            avg_days = df_filtered['date'].diff().dropna().dt.days.mean()
            if avg_days >= 80:  # ~quarter
                quarterly = True

        # -------- Plot Chart --------
        delta_type_arg = None if delta_type == "Off" else delta_type.lower()
        hover_style = "delta" if delta_type_arg is not None else "none"

        fig = plot_chart(
            df_filtered,
            title,
            chart_type,
            hover_style=hover_style,
            delta_type=delta_type_arg,
            date_format="quarterly" if quarterly else "daily",
            show_markers=False
        )

        if quarterly:
            tickvals = df_filtered[df_filtered['date'].dt.quarter == 4]['date']
            ticktext = df_filtered[df_filtered['date'].dt.quarter == 4].dt.to_period('Q').apply(lambda x: f"Q{x.quarter} {x.year}")
            fig.update_xaxes(tickmode='array', tickvals=tickvals, ticktext=ticktext)

        fig.update_layout(
            hoverlabel=dict(
                font_size=13,
                font_color="black",
                font_family="Arial"
            )
        )

        # -------- Display Chart --------
        st.plotly_chart(
            fig,
            use_container_width=True,
            config={
                "displayModeBar": True,
                "displaylogo": False,
                "modeBarButtonsToAdd": ["toImage", "resetScale2d", "zoom2d", "pan2d"],
                "modeBarButtonsToRemove": ["lasso2d", "select2d"]
            }
        )

        # -------- CSV Download --------
        csv_data = df_filtered.to_csv(index=False)
        st.download_button(
            label="📥 Download CSV",
            data=csv_data,
            file_name=f"Bonds_{indicator.replace(' ', '_')}_data.csv",
            mime="text/csv"
        )

     
# -------- Crypto Tab --------
if page == "Crypto":
    col1, col2 = st.columns([1.5, 5])

    with col1:
        st.markdown("<div style='margin-top:-40px;'>", unsafe_allow_html=True)

        # -------- Indicator Groups --------
        indicator_groups = {
            "Major Coins": ["Bitcoin", "Ethereum"]
        }

        # Category dropdown
        category = st.selectbox("Select Category", list(indicator_groups.keys()))

        # Indicator dropdown based on category
        indicator = st.selectbox("Select Indicator", indicator_groups[category])

        # -------- Chart Type + Timeframe side by side --------
        ct_col, tf_col = st.columns(2)
        with ct_col:
            chart_type = st.selectbox("Chart Type", ["Line", "Area", "Bar", "Step"])
        with tf_col:
            timeframe = st.selectbox("Time Frame", ["1Y", "3Y", "5Y", "10Y", "MAX"])

        # Delta Type (allow turning it off)
        delta_type = st.selectbox("Delta Type", ["Off", "Cumulative", "Daily"])

        # -------- Indicator Function Mapping --------
        crypto_map = {
            "Bitcoin": ("BTC-USD", "Bitcoin"),
            "Ethereum": ("ETH-USD", "Ethereum")
        }
        ticker, title = crypto_map[indicator]

        # Load crypto data
        df = get_fx_data_yahoo(ticker, start_date=dt.date(2010, 1, 1), end_date=dt.date.today())
        df = df.dropna()
        if df.empty:
            st.error("No data available.")
            st.stop()

        # -------- Time Frame Logic --------
        earliest_date = df['date'].min().date()
        latest_date = df['date'].max().date()
        if timeframe != "MAX":
            years = int(timeframe.replace("Y", ""))
            default_start_date = max(earliest_date, latest_date - dt.timedelta(days=365*years))
        else:
            default_start_date = earliest_date

        # -------- Start & End Dates side by side --------
        date_col1, date_col2 = st.columns(2)
        with date_col1:
            start_date = st.date_input("Start Date", default_start_date, min_value=earliest_date, max_value=latest_date)
        with date_col2:
            end_date = st.date_input("End Date", latest_date, min_value=earliest_date, max_value=latest_date)

        if start_date > end_date:
            st.warning("Start date cannot be after end date.")
            st.stop()

        st.markdown("</div>", unsafe_allow_html=True)

    with col2:
        # -------- Commentary --------
        commentary = {
            "Bitcoin": (
                "Bitcoin is the largest cryptocurrency by market capitalization and is often considered 'digital gold.' "
                "Its price is influenced by investor sentiment, adoption trends, regulatory developments, macroeconomic conditions, and supply-demand dynamics of its fixed supply."
            ),

            "Ethereum": (
                "Ethereum is the leading smart contract platform, enabling decentralized applications (dApps), decentralized finance (DeFi), and NFTs. "
                "Its value is driven by network activity, adoption of dApps, technological upgrades, gas fees, and overall crypto market sentiment."
            )
        }


        st.markdown(
            f"""
            <div style="
                position: relative;
                top: -10px;
                margin-left: 30px;
                font-size:19px;
                font-family: 'Arial Bold';
                font-weight:normal;
                color:#333;
            ">
                {commentary.get(indicator, "")}
            </div>
            """,
            unsafe_allow_html=True
        )

        # -------- Filter Data by Date --------
        df_filtered = df[(df['date'] >= pd.to_datetime(start_date)) &
                         (df['date'] <= pd.to_datetime(end_date))]

        # Detect if quarterly data (optional for crypto, usually daily)
        quarterly = False

        # -------- Plot Chart --------
        delta_type_arg = None if delta_type == "Off" else delta_type.lower()
        hover_style = "delta" if delta_type_arg is not None else "none"

        fig = plot_chart(
            df_filtered,
            title,
            chart_type,
            hover_style=hover_style,
            delta_type=delta_type_arg,
            date_format="daily",
            show_markers=False
        )

        # Display chart
        st.plotly_chart(
            fig,
            use_container_width=True,
            config={
                "displayModeBar": True,
                "displaylogo": False,
                "modeBarButtonsToAdd": ["toImage", "resetScale2d", "zoom2d", "pan2d"],
                "modeBarButtonsToRemove": ["lasso2d", "select2d"]
            }
        )

        # -------- CSV Download --------
        csv_data = df_filtered.to_csv(index=False)
        st.download_button(
            label="📥 Download CSV",
            data=csv_data,
            file_name=f"{indicator.replace(' ', '_')}_data.csv",
            mime="text/csv"
        )

       
# -------- Yield Curve Tab --------
if page == "Yield Curve":

    col1, col2 = st.columns([1.5, 5])

    with col1:
        st.markdown("<div style='margin-top:-40px;'>", unsafe_allow_html=True)

        # -------- Country Selection --------
        country = st.selectbox("Select Country", ["US", "UK", "Japan", "Euro"])

        # -------- Chart Type + Timeframe side by side --------
        ct_col, tf_col = st.columns(2)
        with ct_col:
            chart_type = st.selectbox("Chart Type", ["Line", "Area", "Bar", "Step"])
        with tf_col:
            timeframe = st.selectbox("Time Frame", ["1Y", "3Y", "5Y", "10Y", "MAX"])

        # -------- Delta Type --------
        delta_type = st.selectbox("Delta Type", ["Off", "Cumulative", "Daily"])

        # -------- Maturity Functions --------
        yield_funcs = {
            "US": {"1M": get_usa_1mo_yield_data, "3M": get_usa_3mo_yield_data, "6M": get_usa_6mo_yield_data,
                   "1Y": get_usa_1yr_yield_data, "2Y": get_usa_2yr_yield_data, "3Y": get_usa_3yr_yield_data,
                   "5Y": get_usa_5yr_yield_data, "7Y": get_usa_7yr_yield_data, "10Y": get_usa_10yr_yield_data,
                   "20Y": get_usa_20yr_yield_data, "30Y": get_usa_30yr_yield_data},
            "UK": {"2Y": get_uk_2yr_yield_data, "10Y": get_uk_10yr_yield_data},
            "Japan": {"2Y": get_japan_2yr_yield_data, "10Y": get_japan_10yr_yield_data},
            "Euro": {"2Y": get_euro_2yr_yield_data, "10Y": get_euro_10yr_yield_data}
        }

        # Sort maturities numerically
        def maturity_to_months(m):
            return int(m[:-1]) * 12 if m.endswith("Y") else int(m[:-1])

        maturities = sorted(list(yield_funcs[country].keys()), key=maturity_to_months)

        # Default selections
        default_long = "10Y" if "10Y" in maturities else maturities[-1]
        default_short = "2Y" if "2Y" in maturities else maturities[0]

        maturity_short = st.selectbox("Short-term Maturity", maturities,
                                      index=maturities.index(default_short))

        long_options = [m for m in maturities if maturity_to_months(m) > maturity_to_months(maturity_short)]
        if not long_options:
            long_options = [maturity_short]
        maturity_long = st.selectbox("Long-term Maturity", long_options,
                                     index=long_options.index(default_long) if default_long in long_options else 0)

        # -------- Load Data --------
        df_long = yield_funcs[country][maturity_long]().dropna().rename(columns={'value': f'yield_{maturity_long}'})
        df_short = yield_funcs[country][maturity_short]().dropna().rename(columns={'value': f'yield_{maturity_short}'})
        df = pd.merge(df_long, df_short, on='date')
        df['spread'] = df[f'yield_{maturity_long}'] - df[f'yield_{maturity_short}']

        # -------- Time Frame Logic --------
        earliest_date = df['date'].min().date()
        latest_date = df['date'].max().date()
        if timeframe != "MAX":
            years = int(timeframe.replace("Y", ""))
            default_start_date = max(earliest_date, latest_date - dt.timedelta(days=365*years))
        else:
            default_start_date = earliest_date

        # -------- Start & End Dates side by side --------
        date_col1, date_col2 = st.columns(2)
        with date_col1:
            start_date = st.date_input("Start Date", default_start_date, min_value=earliest_date, max_value=latest_date)
        with date_col2:
            end_date = st.date_input("End Date", latest_date, min_value=earliest_date, max_value=latest_date)

        if start_date > end_date:
            st.warning("Start date cannot be after end date.")
            st.stop()

        st.markdown("</div>", unsafe_allow_html=True)

    with col2:
        # -------- Commentary --------
        commentary = f"{country} {maturity_long}-{maturity_short} spread indicates yield curve shape and market expectations."
        st.markdown(
            f"""
            <div style="
                position: relative;
                top: -10px;
                margin-left: 30px;
                font-size:19px;
                font-family: 'Arial Bold';
                font-weight:normal;
                color:#333;
            ">
                {commentary}
            </div>
            """,
            unsafe_allow_html=True
        )

        # -------- Filter Data by Date --------
        df_filtered = df[(df['date'] >= pd.to_datetime(start_date)) &
                         (df['date'] <= pd.to_datetime(end_date))]
        df_plot = df_filtered[['date', 'spread']].rename(columns={'spread': 'value'})

        # -------- Plot Chart --------
        delta_type_arg = None if delta_type == "Off" else delta_type.lower()
        hover_style = "delta" if delta_type_arg else "none"

        fig = plot_chart(
            df_plot,
            title=f"{country} {maturity_long}-{maturity_short} Yield Spread",
            chart_type=chart_type,
            hover_style=hover_style,
            delta_type=delta_type_arg,
            date_format="daily",
            show_markers=False
        )

        fig.add_hline(
            y=0,
            line=dict(color="black", width=3, dash="solid"),
            annotation_text="0",
            annotation_position="top left",
            opacity=0.8
        )

        fig.update_layout(
            hoverlabel=dict(font_size=13, font_color="black", font_family="Arial")
        )

        # -------- Display Chart --------
        st.plotly_chart(
            fig,
            use_container_width=True,
            config={
                "displayModeBar": True,
                "displaylogo": False,
                "modeBarButtonsToAdd": ["toImage", "resetScale2d", "zoom2d", "pan2d"],
                "modeBarButtonsToRemove": ["lasso2d", "select2d"]
            }
        )

        # -------- CSV Download --------
        csv_data = df_filtered.to_csv(index=False)
        st.download_button(
            label="📥 Download CSV",
            data=csv_data,
            file_name=f"{country}_{maturity_long}-{maturity_short}_spread.csv",
            mime="text/csv"
        )



# -------- Regime Yield Curve Tab (All Maturities + Line Chart Only) --------
if page == "Curve Regimes":

    # Outer columns: left for controls + table, right for chart
    outer_col1, outer_col2 = st.columns([3, 5])

    with outer_col1:
        # Select country
        country = st.selectbox("Select Country", ["US", "UK", "Japan", "Euro"])

        # Periods for delta table
        period_offsets = {
            "1M": pd.DateOffset(months=1),
            "3M": pd.DateOffset(months=3),
            "1Y": pd.DateOffset(years=1)
        }

        # Map country to all yield maturities
        yield_funcs = {
            "US": {
                "1M": get_usa_1mo_yield_data,
                "3M": get_usa_3mo_yield_data,
                "1Y": get_usa_1yr_yield_data,
                "2Y": get_usa_2yr_yield_data,
                "3Y": get_usa_3yr_yield_data,
                "5Y": get_usa_5yr_yield_data,
                "7Y": get_usa_7yr_yield_data,
                "10Y": get_usa_10yr_yield_data,
                "20Y": get_usa_20yr_yield_data,
                "30Y": get_usa_30yr_yield_data
            },
            "UK": {"2Y": get_uk_2yr_yield_data, "10Y": get_uk_10yr_yield_data},
            "Japan": {"2Y": get_japan_2yr_yield_data, "10Y": get_japan_10yr_yield_data},
            "Euro": {"2Y": get_euro_2yr_yield_data, "10Y": get_euro_10yr_yield_data}
        }

        # Load all maturities for the country
        dfs = []
        for mat, func in yield_funcs[country].items():
            df_temp = func().dropna().rename(columns={'value': mat})
            dfs.append(df_temp)
        df = dfs[0]
        for df_next in dfs[1:]:
            df = pd.merge(df, df_next, on='date')

        # Latest date
        latest_date = df['date'].max()
        df_now = df[df['date'] == latest_date].iloc[0]

        # Build vertical delta table: maturities as rows, periods as columns
        maturities = [m for m in df.columns if m != 'date']
        table_data = {}
        table_data["Now"] = [df_now[m] for m in maturities]

        for label, offset in period_offsets.items():
            ref_date = latest_date - offset
            idx = (df['date'] - ref_date).abs().idxmin()
            row = df.loc[idx]
            table_data[label] = [df_now[m] - row[m] for m in maturities]

        df_table = pd.DataFrame(table_data, index=maturities)
        df_table.index.name = "Maturity"

        # HTML table rendering with color coding, unbold cell values, centered
        # HTML table rendering with color coding, unbold cell values, centered, first row & column highlighted
        def render_html_table(df):
            html = '<table style="border-collapse: collapse; width:100%;">'
            # Header row
            html += '<tr>'
            html += f'<th style="font-weight:bold; color:black; border: 1px solid black; padding:4px; text-align:center; background-color:#F9F9F9;">Maturity</th>'
            for col in df.columns:
                html += f'<th style="font-weight:bold; color:black; border: 1px solid black; padding:4px; text-align:center; background-color:#F9F9F9;">{col}</th>'
            html += '</tr>'
            # Rows
            for idx in df.index:
                html += f'<tr>'
                # First column (maturity)
                html += f'<th style="font-weight:bold; color:black; border: 1px solid black; padding:4px; text-align:center; background-color:#F9F9F9;">{idx}</th>'
                # Other columns
                for col in df.columns:
                    val = df.loc[idx, col]
                    if col == "Now":
                        color = "black"
                    else:
                        if val > 0:
                            color = "green"
                        elif val < 0:
                            color = "red"
                        else:
                            color = "black"
                    html += f'<td style="color:{color}; font-weight:normal; border: 1px solid black; padding:4px; text-align:center;">{val:+.2f}%</td>'
                html += '</tr>'
            html += '</table>'
            return html

        st.markdown(render_html_table(df_table), unsafe_allow_html=True)


    with outer_col2:
        # Regime calculation (short vs long 2Y vs 10Y)
        if "2Y" in df.columns and "10Y" in df.columns:
            ref_date_1m = latest_date - pd.DateOffset(months=1)
            idx_1m = (df['date'] - ref_date_1m).abs().idxmin()
            delta_2y = df_now['2Y'] - df.loc[idx_1m, '2Y']
            delta_10y = df_now['10Y'] - df.loc[idx_1m, '10Y']

            if delta_2y < 0 and delta_10y < 0:
                regime = "Bull Flattener" if abs(delta_10y) > abs(delta_2y) else "Bull Steepener"
            elif delta_2y > 0 and delta_10y > 0:
                regime = "Bear Flattener" if abs(delta_2y) > abs(delta_10y) else "Bear Steepener"
            elif delta_2y < 0 and delta_10y > 0:
                regime = "Bull Steepener"
            elif delta_2y > 0 and delta_10y < 0:
                regime = "Bear Steepener"
            else:
                regime = "Indeterminate"
        else:
            regime = "N/A"
        st.markdown(f"**Current Regime (Now vs 1M): {regime}**")

        # -------- Line Chart (all maturities, historical periods) --------
        df_plot_rows = []
        for label, offset in {"Now": None, **period_offsets}.items():
            if label == "Now":
                row = df_now.copy()
            else:
                ref_date = latest_date - offset
                idx = (df['date'] - ref_date).abs().idxmin()
                row = df.loc[idx].copy()
            row['Period'] = label
            df_plot_rows.append(row)

        df_plot = pd.DataFrame(df_plot_rows)
        df_melt = df_plot.melt(id_vars="Period", value_vars=maturities,
                               var_name="Maturity", value_name="Yield")

        fig = go.Figure()
        for period in df_plot['Period']:
            temp = df_melt[df_melt['Period'] == period]
            fig.add_trace(go.Scatter(
                x=temp['Maturity'],
                y=temp['Yield'],
                mode="lines+markers",
                name=period,
                hovertemplate="<b>%{x}</b><br>Yield: %{y:.2f}%<extra></extra>"
            ))

        axis_tickfont = dict(size=14, family="Arial Bold", color="black")
        axis_title_font = dict(size=16, family="Arial Bold", color="black")

        fig.update_layout(
            title=f"{country} Yield Curve (All Maturities)",
            xaxis=dict(title="Maturity", tickfont=axis_tickfont, linecolor='black', linewidth=2, showline=True,
                       title_font=axis_title_font),
            yaxis=dict(title="Yield (%)", tickfont=axis_tickfont, title_font=axis_title_font,
                       linecolor='black', linewidth=2, showline=True),
            template="plotly_white",
            font=dict(color="black"),
            legend=dict(x=0.01, y=1.1, orientation="h"),
            height=500,
            hoverlabel=dict(bgcolor="#F9F9F9")
        )

        st.plotly_chart(fig, use_container_width=True,
                        config={"displayModeBar": True, "displaylogo": False,
                                "modeBarButtonsToAdd": ["toImage", "resetScale2d", "zoom2d", "pan2d"],
                                "modeBarButtonsToRemove": ["lasso2d", "select2d"]})


# -------- Economic Cycle Tab --------
if page == "Cycle":
    st.header("🌍 Global Economic Cycle Positioning")
    st.write("""
    This page shows where major economies (USA, UK, Euro Area, Japan) sit in the business cycle 
    based on growth, inflation, unemployment, and policy data — mapped into the **macro seasons** 
    (Spring, Summer, Fall, Winter).
    """)

    # ---- Helper: classify cycle ----
    def classify_cycle(gdp_df, cpi_df, unemployment_df, rate_df):
        gdp = analyze_series(gdp_df)
        cpi = analyze_series(cpi_df)
        unemp = analyze_series(unemployment_df)
        rate = analyze_series(rate_df)

        gdp_trend = gdp.get("trend_slope", 0)
        inflation = cpi.get("latest_value", 0)
        unemp_val = unemp.get("latest_value", 0)

        # --- Macro Seasonal Rules ---
        if gdp_trend > 0 and inflation <= 3:
            return "Spring"   # Growth improving, inflation low/sideways
        elif gdp_trend > 0 and inflation > 3:
            return "Summer"   # Growth strong, inflation rising
        elif gdp_trend < 0 and inflation > 3:
            return "Fall"     # Growth weak, inflation sticky/stagflation
        else:
            return "Winter"   # Growth weak, inflation falling

    # ---- Get positions for each country ----
    positions = {}
    positions["USA"] = classify_cycle(get_usa_gdp_qoq_data(), get_usa_cpi_yoy_data(),
                                      get_usa_unemployment_rate_data(), get_usa_interest_rate_data())
    positions["UK"] = classify_cycle(get_uk_gdp_qoq_data(), get_uk_cpi_yoy_data(),
                                     get_uk_unemployment_rate_data(), get_uk_interest_rate_data())
    positions["Euro Area"] = classify_cycle(get_euro_gdp_qoq_data(), get_euro_cpi_yoy_data(),
                                            get_euro_unemployment_rate_data(), get_euro_interest_rate_data())
    positions["Japan"] = classify_cycle(get_japan_gdp_qoq_data(), get_japan_cpi_yoy_data(),
                                        get_japan_unemployment_rate_data(), get_japan_interest_rate_data())

    # ---- Show table ----
    cycle_df = pd.DataFrame({
        "Country": list(positions.keys()),
        "Macro Season": list(positions.values())
    })
    st.subheader("📋 Current Classification")
    st.table(cycle_df)

    # ---- Wave-style cycle chart ----
    def build_cycle_wave(pos_dict):
        import numpy as np

        # Base sine wave (one cycle)
        x = np.linspace(0, 2 * np.pi, 400)
        y = np.sin(x)

        fig = go.Figure()

        # ---- Background Seasons ----
        seasons = [
            {"name": "Spring", "x0": 0, "x1": np.pi/2, "color": "rgba(144,238,144,0.15)"},   # light green
            {"name": "Summer", "x0": np.pi/2, "x1": np.pi, "color": "rgba(255,215,0,0.15)"}, # gold
            {"name": "Fall", "x0": np.pi, "x1": 3*np.pi/2, "color": "rgba(255,140,0,0.15)"}, # orange
            {"name": "Winter", "x0": 3*np.pi/2, "x1": 2*np.pi, "color": "rgba(135,206,250,0.15)"} # light blue
        ]

        for s in seasons:
            fig.add_vrect(
                x0=s["x0"], x1=s["x1"], fillcolor=s["color"], opacity=0.3,
                line_width=0, annotation_text=s["name"], annotation_position="top"
            )

        # ---- Business Cycle Wave ----
        fig.add_trace(go.Scatter(x=x, y=y, mode="lines",
                                 line=dict(color="black", width=3),
                                 name="Business Cycle"))

        # ---- Map phases to positions ----
        mapping = {
            "Spring": np.pi/4,      # mid Spring
            "Summer": 3*np.pi/4,    # Summer top
            "Fall": 5*np.pi/4,      # Fall
            "Winter": 7*np.pi/4     # Winter bottom
        }

        # ---- Plot countries (avoid overlapping labels) ----
        phase_counts = {}
        for country, phase in pos_dict.items():
            xpos = mapping.get(phase, 0)
            ypos = np.sin(xpos)

            # Count how many countries already in this phase
            phase_counts[phase] = phase_counts.get(phase, 0) + 1
            count = phase_counts[phase]

            # Alternate label positions if multiple countries
            text_pos = "top center" if count % 2 == 1 else "bottom center"

            fig.add_trace(go.Scatter(
                x=[xpos], y=[ypos],
                mode="markers+text",
                text=[country],
                textposition=text_pos,
                marker=dict(size=16, symbol="circle", color="red"),
                name=country
            ))

        # ---- Layout ----
        fig.update_layout(
            title=dict(
                text="🌍 Macro Investing<br><span style='font-size:16px;'>Market Seasons & Business Cycle</span>",
                x=0.5, xanchor="center"
            ),
            xaxis=dict(
                title="Economic Cycle (Seasons)",
                tickvals=[0, np.pi/2, np.pi, 3*np.pi/2, 2*np.pi],
                ticktext=["Start", "Spring", "Summer", "Fall", "Winter"],
                showline=True, linewidth=2, linecolor="black", mirror=True
            ),
            yaxis=dict(
                title="Economic Activity",
                showline=True, linewidth=2, linecolor="black", mirror=True,
                range=[-1.5, 1.5]
            ),
            height=550,
            margin=dict(l=40, r=40, t=80, b=40),
            showlegend=False
        )

        return fig

    st.subheader("📊 Cycle Visualization")
    fig = build_cycle_wave(positions)
    st.plotly_chart(fig, use_container_width=True)
