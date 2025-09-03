import streamlit as st
import pandas as pd
import plotly.express as px
import datetime as dt
import requests
import io
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

# -------- Helper Functions --------
def plot_chart(df, title, chart_type, height=550, date_format="daily",
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
    
def get_usa_interest_rate_data():
    base_dir = os.path.dirname(__file__)
    file_path = os.path.join(base_dir, "USA_Interest_Rate.txt")

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

def get_usa_cpi_yoy_data():
    base_dir = os.path.dirname(__file__)
    file_path = os.path.join(base_dir, "USA_CPI_YoY.txt")
    
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

def get_usa_gdp_qoq_data():
    base_dir = os.path.dirname(__file__)
    file_path = os.path.join(base_dir, "USA_GDP_Growth_Rate_QoQ.txt")
    
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
    
def get_usa_unemployment_rate_data():
    base_dir = os.path.dirname(__file__)
    file_path = os.path.join(base_dir, "USA_Unemployment_Rate.txt")
    
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
    
def get_usa_core_cpi_yoy_data():
    base_dir = os.path.dirname(__file__)
    file_path = os.path.join(base_dir, "USA_Core_CPI_YoY.txt")
    
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
    
def get_usa_average_hourly_earnings_yoy_data():
    base_dir = os.path.dirname(__file__)
    file_path = os.path.join(base_dir, "USA_Average_Hourly_Earnings_YoY.txt")
    
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

# ---------------------------
# FRED API Setup
# ---------------------------
FRED_API_KEY = "3be1b836ee6f78badf0f0a5a4905ab73"   # <- put your key here once

# ---------------------------
# Yield Data Functions
# ---------------------------


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
def get_usa_1mo_yield_data():
    return get_usa_yield_data("DGS1MO")

def get_usa_3mo_yield_data():
    return get_usa_yield_data("DGS3MO")

def get_usa_6mo_yield_data():
    return get_usa_yield_data("DGS6MO")

def get_usa_1yr_yield_data():
    return get_usa_yield_data("DGS1")

def get_usa_2yr_yield_data():
    return get_usa_yield_data("DGS2")

def get_usa_3yr_yield_data():
    return get_usa_yield_data("DGS3")

def get_usa_5yr_yield_data():
    return get_usa_yield_data("DGS5")

def get_usa_7yr_yield_data():
    return get_usa_yield_data("DGS7")

def get_usa_10yr_yield_data():
    return get_usa_yield_data("DGS10")

def get_usa_20yr_yield_data():
    return get_usa_yield_data("DGS20")

def get_usa_30yr_yield_data():
    return get_usa_yield_data("DGS30")


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
        <a href="?page=Analysis" target="_self">Analysis</a>
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
                    <h3>📈 FX Rates</h3>
                    <p>Live tracking of major currency pairs and the DXY index. Analyze trends and turning points across daily data.</p>
                </div>
                <div class="feature-box">
                    <h3>📊 Macroeconomic Indicators</h3>
                    <p>From interest rates and inflation to GDP growth and unemployment — all organized by country, all in one place.</p>
                </div>
                <div class="feature-box">
                    <h3>⚖️ Cross-Compare</h3>
                    <p>Want to compare U.S. CPI vs EUR/USD? 10Y yields vs GDP? Use the 'Compare' tab to overlay any indicators with dual axes.</p>
                </div>
                <div class="feature-box">
                    <h3>🧠 Built for Analysts</h3>
                    <p>This isn't a toy. It's for traders, researchers, and macro enthusiasts who want clean data, fast insights, and real flexibility.</p>
                </div>
            </div>
        </div>

        <div class="section">
            <h2>🚀 How to Use This Dashboard</h2>
            <ul>
                <li><b>Select a country or FX tab</b> in the top bar to explore economic indicators</li>
                <li><b>Choose your chart type</b> (Line, Area, Bar)</li>
                <li><b>Adjust the date range</b> as needed — everything updates instantly</li>
                <li><b>Use 'Compare'</b> to overlay different indicators on one chart with dual y-axes</li>
            </ul>
        </div>

        <div class="section">
            <h2>📡 Data Sources</h2>
            <ul>
                <li><b>USA:</b> Federal Reserve (FRED API)</li>
                <li><b>Japan:</b> e-Stat Japan Government Portal</li>
                <li><b>UK:</b> Bank of England, ONS</li>
                <li><b>Euro Area:</b> ECB, Eurostat</li>
                <li><b>FX:</b> Yahoo Finance</li>
            </ul>
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
    col1, col2 = st.columns([1, 5])

    with col1:
        st.markdown("<div style='margin-top:-40px;'>", unsafe_allow_html=True)

        # Dropdowns
        indicator = st.selectbox("Select Indicator", [
            "Interest Rate",
            "Inflation Rate",
            "GDP Growth Rate",
            "Unemployment Rate",
            "Core CPI YoY",
            "Average Hourly Earnings YoY"
        ])
        chart_type = st.selectbox("Chart Type", ["Line", "Area", "Bar", "Step"])

        # Toggle for delta type
        delta_type = st.selectbox("Delta Type", ["Cumulative", "Daily"])

        # Load data based on indicator
        if indicator == "Interest Rate":
            df = get_usa_interest_rate_data()
            date_format = "daily"
            tickformat_override = "%b %Y"
        elif indicator == "Inflation Rate":
            df = get_usa_cpi_yoy_data()
            date_format = "monthly"
            tickformat_override = None
        elif indicator == "GDP Growth Rate":
            df = get_usa_gdp_qoq_data()
            date_format = "quarterly"
            df['tick_label'] = df['date'].dt.to_period('Q').apply(lambda x: f"Q{x.quarter} {x.year}")
            tickformat_override = None
        elif indicator == "Unemployment Rate":
            df = get_usa_unemployment_rate_data()
            date_format = "monthly"
            tickformat_override = None
        elif indicator == "Core CPI YoY":
            df = get_usa_core_cpi_yoy_data()
            date_format = "monthly"
            tickformat_override = None
        elif indicator == "Average Hourly Earnings YoY":
            df = get_usa_average_hourly_earnings_yoy_data()
            date_format = "monthly"
            tickformat_override = None
            
            
        df = df.dropna()
        if df.empty:
            st.error("No data available.")
            st.stop()

        # -------- Time Frame Selector --------
        earliest_date = df['date'].min().date()
        latest_date = df['date'].max().date()
        timeframe = st.selectbox("**Time Frame**", ["1Y", "3Y", "5Y", "10Y", "MAX"])

        if timeframe != "MAX":
            years = int(timeframe.replace("Y", ""))
            default_start_date = max(earliest_date, latest_date - dt.timedelta(days=365*years))
        else:
            default_start_date = earliest_date

        # Date inputs
        start_date = st.date_input("Start Date", default_start_date, min_value=earliest_date, max_value=latest_date)
        end_date = st.date_input("End Date", latest_date, min_value=earliest_date, max_value=latest_date)

        if start_date > end_date:
            st.warning("Start date cannot be after end date.")
            st.stop()

        st.markdown("</div>", unsafe_allow_html=True)

    with col2:
        # Commentary for each indicator
        commentary = {
            "Interest Rate": "The Federal Funds Rate reflects U.S. monetary policy stance and impacts global markets.",
            "Inflation Rate": "The CPI YoY measures U.S. inflation and influences Fed interest rate decisions.",
            "GDP Growth Rate": "Real GDP growth captures the pace of U.S. economic expansion or contraction.",
            "Unemployment Rate": "The unemployment rate is a key measure of labor market health in the U.S. economy."
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

        # Dynamic Titles
        titles = {
            "Interest Rate": "Federal Funds Rate (%)",
            "Inflation Rate": "CPI YoY (%)",
            "GDP Growth Rate": "Real GDP Growth Rate (QoQ Annualized %)",
            "Unemployment Rate": "Unemployment Rate (%)",
            "Core CPI YoY": "Core CPI YoY (%)",
            "Average Hourly Earnings YoY": "Average Hourly Earnings YoY (%)"
        }

        # Detect if quarterly data
        quarterly = (date_format == "quarterly")

        # Plot chart with delta hover
        fig = plot_chart(
            df_filtered,
            titles[indicator],
            chart_type,
            hover_style="delta",
            delta_type=delta_type.lower(),
            date_format="quarterly" if quarterly else date_format,
            tickformat_override=tickformat_override,
            show_markers=False
        )

        # For quarterly charts, show only Q4 labels
        if quarterly:
            tickvals = df_filtered.loc[df_filtered['date'].dt.quarter == 4, 'date']
            ticktext = df_filtered.loc[df_filtered['date'].dt.quarter == 4, 'date'] \
                .dt.to_period('Q').apply(lambda x: f"Q{x.quarter} {x.year}")
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
    col1, col2 = st.columns([1, 5])

    with col1:
        st.markdown("<div style='margin-top:-40px;'>", unsafe_allow_html=True)

        # Dropdowns
        indicator = st.selectbox("Select Indicator", [
            "Interest Rate",
            "Inflation Rate",
            "GDP Growth Rate",
            "Unemployment Rate"
        ])
        chart_type = st.selectbox("Chart Type", ["Line", "Area", "Bar", "Step"])

        # Toggle for delta type
        delta_type = st.selectbox("Delta Type", ["Cumulative", "Daily"])

        # Load data based on indicator
        if indicator == "Interest Rate":
            df = get_japan_interest_rate_data()
            date_format = "daily"
            tickformat_override = "%b %Y"
        elif indicator == "Inflation Rate":
            df = get_japan_cpi_yoy_data()
            date_format = "monthly"
            tickformat_override = None
        elif indicator == "GDP Growth Rate":
            df = get_japan_gdp_qoq_data()
            date_format = "quarterly"
            df['tick_label'] = df['date'].dt.to_period('Q').apply(lambda x: f"Q{x.quarter} {x.year}")
            tickformat_override = None
        elif indicator == "Unemployment Rate":
            df = get_japan_unemployment_rate_data()
            date_format = "monthly"
            tickformat_override = None

        df = df.dropna()
        if df.empty:
            st.error("No data available.")
            st.stop()

        # -------- Time Frame Selector --------
        earliest_date = df['date'].min().date()
        latest_date = df['date'].max().date()
        timeframe = st.selectbox("**Time Frame**", ["1Y", "3Y", "5Y", "10Y", "MAX"])

        if timeframe != "MAX":
            years = int(timeframe.replace("Y", ""))
            default_start_date = max(earliest_date, latest_date - dt.timedelta(days=365*years))
        else:
            default_start_date = earliest_date

        # Date inputs
        start_date = st.date_input("Start Date", default_start_date, min_value=earliest_date, max_value=latest_date)
        end_date = st.date_input("End Date", latest_date, min_value=earliest_date, max_value=latest_date)

        if start_date > end_date:
            st.warning("Start date cannot be after end date.")
            st.stop()

        st.markdown("</div>", unsafe_allow_html=True)

    with col2:
        # Commentary for each indicator
        commentary = {
            "Interest Rate": "The Federal Funds Rate reflects U.S. monetary policy stance and impacts global markets.",
            "Inflation Rate": "The CPI YoY measures U.S. inflation and influences Fed interest rate decisions.",
            "GDP Growth Rate": "Real GDP growth captures the pace of U.S. economic expansion or contraction.",
            "Unemployment Rate": "The unemployment rate is a key measure of labor market health in the U.S. economy."
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

        # Dynamic Titles
        titles = {
            "Interest Rate": "Bank of Japan Policy Rate",
            "Inflation Rate": "CPI YoY (%)",
            "GDP Growth Rate": "Real GDP Growth Rate (QoQ Annualized %)",
            "Unemployment Rate": "Unemployment Rate (%)"
        }

        # Detect if quarterly data
        quarterly = (date_format == "quarterly")

        # Plot chart with delta hover (same as FX tab)
        fig = plot_chart(
            df_filtered,
            titles[indicator],
            chart_type,
            hover_style="delta",
            delta_type=delta_type.lower(),
            date_format="quarterly" if quarterly else date_format,
            tickformat_override=tickformat_override,
            show_markers=False
        )

        # For quarterly charts, show only Q4 labels
        if quarterly:
            tickvals = df_filtered.loc[df_filtered['date'].dt.quarter == 4, 'date']
            ticktext = df_filtered.loc[df_filtered['date'].dt.quarter == 4, 'date'] \
                .dt.to_period('Q').apply(lambda x: f"Q{x.quarter} {x.year}")
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
    col1, col2 = st.columns([1, 5])

    with col1:
        st.markdown("<div style='margin-top:-40px;'>", unsafe_allow_html=True)

        # Dropdowns
        indicator = st.selectbox("Select Indicator", [
            "Interest Rate",
            "Inflation Rate",
            "GDP Growth Rate",
            "Unemployment Rate"
        ])
        chart_type = st.selectbox("Chart Type", ["Line", "Area", "Bar", "Step"])

        # Toggle for delta type
        delta_type = st.selectbox("Delta Type", ["Cumulative", "Daily"])

        # Load data based on indicator
        if indicator == "Interest Rate":
            df = get_uk_interest_rate_data()
            date_format = "daily"
            tickformat_override = "%b %Y"
        elif indicator == "Inflation Rate":
            df = get_uk_cpi_yoy_data()
            date_format = "monthly"
            tickformat_override = None
        elif indicator == "GDP Growth Rate":
            df = get_uk_gdp_qoq_data()
            date_format = "quarterly"
            df['tick_label'] = df['date'].dt.to_period('Q').apply(lambda x: f"Q{x.quarter} {x.year}")
            tickformat_override = None
        elif indicator == "Unemployment Rate":
            df = get_uk_unemployment_rate_data()
            date_format = "monthly"
            tickformat_override = None

        df = df.dropna()
        if df.empty:
            st.error("No data available.")
            st.stop()

        # -------- Time Frame Selector --------
        earliest_date = df['date'].min().date()
        latest_date = df['date'].max().date()
        timeframe = st.selectbox("**Time Frame**", ["1Y", "3Y", "5Y", "10Y", "MAX"])

        if timeframe != "MAX":
            years = int(timeframe.replace("Y", ""))
            default_start_date = max(earliest_date, latest_date - dt.timedelta(days=365*years))
        else:
            default_start_date = earliest_date

        # Date inputs
        start_date = st.date_input("Start Date", default_start_date, min_value=earliest_date, max_value=latest_date)
        end_date = st.date_input("End Date", latest_date, min_value=earliest_date, max_value=latest_date)

        if start_date > end_date:
            st.warning("Start date cannot be after end date.")
            st.stop()

        st.markdown("</div>", unsafe_allow_html=True)

    with col2:
        # Commentary for each indicator
        commentary = {
            "Interest Rate": "The Federal Funds Rate reflects U.S. monetary policy stance and impacts global markets.",
            "Inflation Rate": "The CPI YoY measures U.S. inflation and influences Fed interest rate decisions.",
            "GDP Growth Rate": "Real GDP growth captures the pace of U.S. economic expansion or contraction.",
            "Unemployment Rate": "The unemployment rate is a key measure of labor market health in the U.S. economy."
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

        # Dynamic Titles
        titles = {
            "Interest Rate": "Bank of Japan Policy Rate",
            "Inflation Rate": "CPI YoY (%)",
            "GDP Growth Rate": "Real GDP Growth Rate (QoQ Annualized %)",
            "Unemployment Rate": "Unemployment Rate (%)"
        }

        # Detect if quarterly data
        quarterly = (date_format == "quarterly")

        # Plot chart with delta hover (same as FX tab)
        fig = plot_chart(
            df_filtered,
            titles[indicator],
            chart_type,
            hover_style="delta",
            delta_type=delta_type.lower(),
            date_format="quarterly" if quarterly else date_format,
            tickformat_override=tickformat_override,
            show_markers=False
        )

        # For quarterly charts, show only Q4 labels
        if quarterly:
            tickvals = df_filtered.loc[df_filtered['date'].dt.quarter == 4, 'date']
            ticktext = df_filtered.loc[df_filtered['date'].dt.quarter == 4, 'date'] \
                .dt.to_period('Q').apply(lambda x: f"Q{x.quarter} {x.year}")
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
    col1, col2 = st.columns([1, 5])

    with col1:
        st.markdown("<div style='margin-top:-40px;'>", unsafe_allow_html=True)

        # Dropdowns
        indicator = st.selectbox("Select Indicator", [
            "Interest Rate",
            "Inflation Rate",
            "GDP Growth Rate",
            "Unemployment Rate"
        ])
        chart_type = st.selectbox("Chart Type", ["Line", "Area", "Bar", "Step"])

        # Toggle for delta type
        delta_type = st.selectbox("Delta Type", ["Cumulative", "Daily"])

        # Load data based on indicator
        if indicator == "Interest Rate":
            df = get_euro_interest_rate_data()
            date_format = "daily"
            tickformat_override = "%b %Y"
        elif indicator == "Inflation Rate":
            df = get_euro_cpi_yoy_data()
            date_format = "monthly"
            tickformat_override = None
        elif indicator == "GDP Growth Rate":
            df = get_euro_gdp_qoq_data()
            date_format = "quarterly"
            df['tick_label'] = df['date'].dt.to_period('Q').apply(lambda x: f"Q{x.quarter} {x.year}")
            tickformat_override = None
        elif indicator == "Unemployment Rate":
            df = get_euro_unemployment_rate_data()
            date_format = "monthly"
            tickformat_override = None

        df = df.dropna()
        if df.empty:
            st.error("No data available.")
            st.stop()

        # -------- Time Frame Selector --------
        earliest_date = df['date'].min().date()
        latest_date = df['date'].max().date()
        timeframe = st.selectbox("**Time Frame**", ["1Y", "3Y", "5Y", "10Y", "MAX"])

        if timeframe != "MAX":
            years = int(timeframe.replace("Y", ""))
            default_start_date = max(earliest_date, latest_date - dt.timedelta(days=365*years))
        else:
            default_start_date = earliest_date

        # Date inputs
        start_date = st.date_input("Start Date", default_start_date, min_value=earliest_date, max_value=latest_date)
        end_date = st.date_input("End Date", latest_date, min_value=earliest_date, max_value=latest_date)

        if start_date > end_date:
            st.warning("Start date cannot be after end date.")
            st.stop()

        st.markdown("</div>", unsafe_allow_html=True)

    with col2:
        # Commentary for each indicator
        commentary = {
            "Interest Rate": "The Federal Funds Rate reflects U.S. monetary policy stance and impacts global markets.",
            "Inflation Rate": "The CPI YoY measures U.S. inflation and influences Fed interest rate decisions.",
            "GDP Growth Rate": "Real GDP growth captures the pace of U.S. economic expansion or contraction.",
            "Unemployment Rate": "The unemployment rate is a key measure of labor market health in the U.S. economy."
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

        # Dynamic Titles
        titles = {
            "Interest Rate": "Bank of Japan Policy Rate",
            "Inflation Rate": "CPI YoY (%)",
            "GDP Growth Rate": "Real GDP Growth Rate (QoQ Annualized %)",
            "Unemployment Rate": "Unemployment Rate (%)"
        }

        # Detect if quarterly data
        quarterly = (date_format == "quarterly")

        # Plot chart with delta hover (same as FX tab)
        fig = plot_chart(
            df_filtered,
            titles[indicator],
            chart_type,
            hover_style="delta",
            delta_type=delta_type.lower(),
            date_format="quarterly" if quarterly else date_format,
            tickformat_override=tickformat_override,
            show_markers=False
        )

        # For quarterly charts, show only Q4 labels
        if quarterly:
            tickvals = df_filtered.loc[df_filtered['date'].dt.quarter == 4, 'date']
            ticktext = df_filtered.loc[df_filtered['date'].dt.quarter == 4, 'date'] \
                .dt.to_period('Q').apply(lambda x: f"Q{x.quarter} {x.year}")
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
    
    col1, col2 = st.columns([1, 5])

    with col1:
        st.markdown("<div style='margin-top:-40px;'>", unsafe_allow_html=True)

        # Select indicator and chart type
        indicator = st.selectbox("Select Indicator", [
            "EUR/USD", "GBP/USD", "USD/JPY", "EUR/GBP", "EUR/JPY", "GBP/JPY", "DXY"
        ])
        chart_type = st.selectbox("Chart Type", ["Line", "Area", "Bar", "Step"])

        # Toggle for delta type
        delta_type = st.selectbox("Delta Type", ["Cumulative", "Daily"])

        # Map indicator to Yahoo ticker and chart title
        fx_tickers = {
            "EUR/USD": ("EURUSD=X", "EUR/USD"),
            "GBP/USD": ("GBPUSD=X", "GBP/USD"),
            "USD/JPY": ("USDJPY=X", "USD/JPY"),
            "EUR/GBP": ("EURGBP=X", "EUR/GBP"),
            "EUR/JPY": ("EURJPY=X", "EUR/JPY"),
            "GBP/JPY": ("GBPJPY=X", "GBP/JPY"),
            "DXY":     ("DX-Y.NYB", "DXY")    
        }
        ticker, title = fx_tickers[indicator]

        # Load FX data
        df = get_fx_data_yahoo(ticker, start_date=dt.date(1980, 1, 1), end_date=dt.date.today())
        df = df.dropna()
        if df.empty:
            st.error("No data available.")
            st.stop()

        # Time frame selector
        earliest_date = df['date'].min().date()
        latest_date = df['date'].max().date()
        timeframe = st.selectbox("**Time Frame**", ["1Y", "3Y", "5Y", "10Y", "MAX"])
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
            "EUR/USD": "The EUR/USD has seen recent gains due mainly to the expectation of the Fed cutting interest rates.",
            "GBP/USD": "The GBP/USD has been influenced by UK economic data and Bank of England rate expectations.",
            "USD/JPY": "The USD/JPY remains sensitive to changes in U.S. Treasury yields and risk sentiment.",
            "EUR/GBP": "The EUR/GBP reflects diverging monetary policy outlooks between the ECB and BoE.",
            "EUR/JPY": "The EUR/JPY is driven by ECB policy signals and broader risk appetite.",
            "GBP/JPY": "The GBP/JPY has been volatile due to risk sentiment and differences in monetary policy.",
            "DXY":     "The DXY index reflects overall USD strength, reacting strongly to Fed policy expectations."
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
                "GDP QoQ %": "usa_gdp",
                "Unemployment Rate": "usa_unemp"
                
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
            if code == "usa_gdp": return get_usa_gdp_qoq_data()
            if code == "usa_unemp": return get_usa_unemployment_rate_data()
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


        import numpy as np
        import pandas as pd

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
        import plotly.graph_objects as go

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
    import calendar

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
    
    col1, col2 = st.columns([1, 5])

    with col1:
        st.markdown("<div style='margin-top:-40px;'>", unsafe_allow_html=True)

        # Select indicator and chart type
        indicator = st.selectbox("Select Indicator", [
            "S&P 500", "NASDAQ", "Dow Jones", "FTSE 100", "Nikkei 225", "DAX", "MSCI Emerging Markets ETF", "VIX"
        ])
        chart_type = st.selectbox("Chart Type", ["Line", "Area", "Bar", "Step"])

        # Toggle for delta type
        delta_type = st.selectbox("Delta Type", ["Cumulative", "Daily"])

        # Map indicator to Yahoo ticker and chart title
        equities_tickers = {
            "S&P 500": ("^GSPC", "S&P 500"),
            "NASDAQ": ("^IXIC", "NASDAQ"),
            "Dow Jones": ("^DJI", "Dow Jones"),
            "FTSE 100": ("^FTSE", "FTSE 100"),
            "Nikkei 225": ("^N225", "Nikkei 225"),
            "DAX": ("^GDAXI", "DAX"),
            "MSCI Emerging Markets ETF":     ("EEM", "MSCI Emerging Markets ETF"),
            "VIX": ("^VIX", "VIX")
        }
        ticker, title = equities_tickers[indicator]

        # Load FX data
        df = get_fx_data_yahoo(ticker, start_date=dt.date(1980, 1, 1), end_date=dt.date.today())
        df = df.dropna()
        if df.empty:
            st.error("No data available.")
            st.stop()

        # Time frame selector
        earliest_date = df['date'].min().date()
        latest_date = df['date'].max().date()
        timeframe = st.selectbox("**Time Frame**", ["1Y", "3Y", "5Y", "10Y", "MAX"])
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
            "EUR/USD": "The EUR/USD has seen recent gains due mainly to the expectation of the Fed cutting interest rates.",
            "GBP/USD": "The GBP/USD has been influenced by UK economic data and Bank of England rate expectations.",
            "USD/JPY": "The USD/JPY remains sensitive to changes in U.S. Treasury yields and risk sentiment.",
            "EUR/GBP": "The EUR/GBP reflects diverging monetary policy outlooks between the ECB and BoE.",
            "EUR/JPY": "The EUR/JPY is driven by ECB policy signals and broader risk appetite.",
            "GBP/JPY": "The GBP/JPY has been volatile due to risk sentiment and differences in monetary policy.",
            "DXY":     "The DXY index reflects overall USD strength, reacting strongly to Fed policy expectations."
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
        timeframe = st.selectbox("**Time Frame**", ["1Y", "3Y", "5Y", "10Y", "MAX"])
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
            "EUR/USD": "The EUR/USD has seen recent gains due mainly to the expectation of the Fed cutting interest rates.",
            "GBP/USD": "The GBP/USD has been influenced by UK economic data and Bank of England rate expectations.",
            "USD/JPY": "The USD/JPY remains sensitive to changes in U.S. Treasury yields and risk sentiment.",
            "EUR/GBP": "The EUR/GBP reflects diverging monetary policy outlooks between the ECB and BoE.",
            "EUR/JPY": "The EUR/JPY is driven by ECB policy signals and broader risk appetite.",
            "GBP/JPY": "The GBP/JPY has been volatile due to risk sentiment and differences in monetary policy.",
            "DXY":     "The DXY index reflects overall USD strength, reacting strongly to Fed policy expectations."
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
    
    col1, col2 = st.columns([1, 5])

    with col1:
        st.markdown("<div style='margin-top:-40px;'>", unsafe_allow_html=True)

        # Select indicator and chart type
        indicator = st.selectbox("Select Indicator", [
            "Gold", "Silver", "Crude Oil (WTI)", "Brent Oil", "Natural Gas", "Wheat", "Copper", "Corn", "Soybeans"
        ])
        chart_type = st.selectbox("Chart Type", ["Line", "Area", "Bar", "Step"])

        # Toggle for delta type
        delta_type = st.selectbox("Delta Type", ["Cumulative", "Daily"])

        # Map indicator to Yahoo ticker and chart title
        commodities_tickers = {
            "Gold": ("GC=F", "Gold"),
            "Silver": ("SI=F", "Silver"),
            "Crude Oil (WTI)": ("CL=F", "Crude Oil (WTI)"),
            "Brent Oil": ("BZ=F", "Brent Oil"),
            "Natural Gas": ("NG=F", "Natural Gas"),
            "Wheat": ("ZW=F", "Wheat"),
            "Copper":     ("HG=F", "Copper"),
            "Corn":     ("ZC=F", "Corn"),
            "Soybeans":     ("ZS=F", "Soybeans")
        }
        ticker, title = commodities_tickers[indicator]

        # Load FX data
        df = get_fx_data_yahoo(ticker, start_date=dt.date(1980, 1, 1), end_date=dt.date.today())
        df = df.dropna()
        if df.empty:
            st.error("No data available.")
            st.stop()

        # Time frame selector
        earliest_date = df['date'].min().date()
        latest_date = df['date'].max().date()
        timeframe = st.selectbox("**Time Frame**", ["1Y", "3Y", "5Y", "10Y", "MAX"])
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
            "EUR/USD": "The EUR/USD has seen recent gains due mainly to the expectation of the Fed cutting interest rates.",
            "GBP/USD": "The GBP/USD has been influenced by UK economic data and Bank of England rate expectations.",
            "USD/JPY": "The USD/JPY remains sensitive to changes in U.S. Treasury yields and risk sentiment.",
            "EUR/GBP": "The EUR/GBP reflects diverging monetary policy outlooks between the ECB and BoE.",
            "EUR/JPY": "The EUR/JPY is driven by ECB policy signals and broader risk appetite.",
            "GBP/JPY": "The GBP/JPY has been volatile due to risk sentiment and differences in monetary policy.",
            "DXY":     "The DXY index reflects overall USD strength, reacting strongly to Fed policy expectations."
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
        
# -------- Bonds Tab --------
if page == "Bonds":
    
    col1, col2 = st.columns([1, 5])

    with col1:
        st.markdown("<div style='margin-top:-40px;'>", unsafe_allow_html=True)

        # Select indicator and chart type
        indicator = st.selectbox("Select Indicator", [
            "US 2Y", "US 10Y", "UK 2Y", "UK 10Y", "Japan 2Y", "Japan 10Y", "Euro 2Y", "Euro 10Y"
        ])
        chart_type = st.selectbox("Chart Type", ["Line", "Area", "Bar", "Step"])

        # Toggle for delta type
        delta_type = st.selectbox("Delta Type", ["Cumulative", "Daily"])

        # Map indicator to Yahoo ticker and chart title
        bonds_data_funcs = {
            "US 2Y": (get_usa_2yr_yield_data, "US 2-Year Treasury Yield"),
            "US 10Y": (get_usa_10yr_yield_data, "US 10-Year Treasury Yield"),
            "UK 2Y": (get_uk_2yr_yield_data, "UK 2-Year Gilt Yield"),
            "UK 10Y": (get_uk_10yr_yield_data, "UK 10-Year Gilt Yield"),
            "Japan 2Y": (get_japan_2yr_yield_data, "Japan 2-Year JGB Yield"),
            "Japan 10Y": (get_japan_10yr_yield_data, "Japan 10-Year JGB Yield"),
            "Euro 2Y": (get_euro_2yr_yield_data, "Euro 2-Year Yield"),
            "Euro 10Y": (get_euro_10yr_yield_data, "Euro 10-Year Yield")
        }
        data_func, title = bonds_data_funcs[indicator]

        # Load FX data
        df = data_func()  # calls get_usa_2yr_yield_data, get_uk_10yr_yield_data, etc.
        df = df.dropna()
        if df.empty:
            st.error("No data available.")
            st.stop()

        # Time frame selector
        earliest_date = df['date'].min().date()
        latest_date = df['date'].max().date()
        timeframe = st.selectbox("**Time Frame**", ["1Y", "3Y", "5Y", "10Y", "MAX"])
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
            "EUR/USD": "The EUR/USD has seen recent gains due mainly to the expectation of the Fed cutting interest rates.",
            "GBP/USD": "The GBP/USD has been influenced by UK economic data and Bank of England rate expectations.",
            "USD/JPY": "The USD/JPY remains sensitive to changes in U.S. Treasury yields and risk sentiment.",
            "EUR/GBP": "The EUR/GBP reflects diverging monetary policy outlooks between the ECB and BoE.",
            "EUR/JPY": "The EUR/JPY is driven by ECB policy signals and broader risk appetite.",
            "GBP/JPY": "The GBP/JPY has been volatile due to risk sentiment and differences in monetary policy.",
            "DXY":     "The DXY index reflects overall USD strength, reacting strongly to Fed policy expectations."
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
     
# -------- Crypto Tab --------
if page == "Crypto":
    
    col1, col2 = st.columns([1, 5])

    with col1:
        st.markdown("<div style='margin-top:-40px;'>", unsafe_allow_html=True)

        # Select indicator and chart type
        indicator = st.selectbox("Select Indicator", [
            "Bitcoin", "Ethereum"
        ])
        chart_type = st.selectbox("Chart Type", ["Line", "Area", "Bar", "Step"])

        # Toggle for delta type
        delta_type = st.selectbox("Delta Type", ["Cumulative", "Daily"])

        # Map indicator to Yahoo ticker and chart title
        crypto_tickers = {
            "Bitcoin": ("BTC-USD", "Bitcoin"),
            "Ethereum": ("ETH-USD", "Ethereum"),
   
        }
        ticker, title = crypto_tickers[indicator]

        # Load FX data
        df = get_fx_data_yahoo(ticker, start_date=dt.date(1980, 1, 1), end_date=dt.date.today())
        df = df.dropna()
        if df.empty:
            st.error("No data available.")
            st.stop()

        # Time frame selector
        earliest_date = df['date'].min().date()
        latest_date = df['date'].max().date()
        timeframe = st.selectbox("**Time Frame**", ["1Y", "3Y", "5Y", "10Y", "MAX"])
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
            "EUR/USD": "The EUR/USD has seen recent gains due mainly to the expectation of the Fed cutting interest rates.",
            "GBP/USD": "The GBP/USD has been influenced by UK economic data and Bank of England rate expectations.",
            "USD/JPY": "The USD/JPY remains sensitive to changes in U.S. Treasury yields and risk sentiment.",
            "EUR/GBP": "The EUR/GBP reflects diverging monetary policy outlooks between the ECB and BoE.",
            "EUR/JPY": "The EUR/JPY is driven by ECB policy signals and broader risk appetite.",
            "GBP/JPY": "The GBP/JPY has been volatile due to risk sentiment and differences in monetary policy.",
            "DXY":     "The DXY index reflects overall USD strength, reacting strongly to Fed policy expectations."
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
       
# -------- Yield Curve Tab --------
if page == "Yield Curve":

    col1, col2 = st.columns([1, 5])

    with col1:
        st.markdown("<div style='margin-top:-40px;'>", unsafe_allow_html=True)

        # Select country
        country = st.selectbox("Select Country", ["US", "UK", "Japan", "Euro"])

        # Delta type
        delta_type = st.selectbox("Delta Type", ["Cumulative", "Daily"])

        # Map country to all yield data functions
        yield_funcs = {
            "US": {
                "1M": get_usa_1mo_yield_data,
                "3M": get_usa_3mo_yield_data,
                "6M": get_usa_6mo_yield_data,
                "1Y": get_usa_1yr_yield_data,
                "2Y": get_usa_2yr_yield_data,
                "3Y": get_usa_3yr_yield_data,
                "5Y": get_usa_5yr_yield_data,
                "7Y": get_usa_7yr_yield_data,
                "10Y": get_usa_10yr_yield_data,
                "20Y": get_usa_20yr_yield_data,
                "30Y": get_usa_30yr_yield_data
            },
            "UK": {
                "2Y": get_uk_2yr_yield_data,
                "10Y": get_uk_10yr_yield_data
            },
            "Japan": {
                "2Y": get_japan_2yr_yield_data,
                "10Y": get_japan_10yr_yield_data
            },
            "Euro": {
                "2Y": get_euro_2yr_yield_data,
                "10Y": get_euro_10yr_yield_data
            }
        }

        # Sort maturities numerically for safe selection
        def maturity_to_months(m):
            if m.endswith("M"):
                return int(m[:-1])
            elif m.endswith("Y"):
                return int(m[:-1]) * 12
            return 0

        maturities = sorted(list(yield_funcs[country].keys()), key=maturity_to_months)

        # Default selections: Long=10Y, Short=2Y if available
        default_long = "10Y" if "10Y" in maturities else maturities[-1]
        default_short = "2Y" if "2Y" in maturities else maturities[0]

        # Select short-term maturity first
        maturity_short = st.selectbox("Short-term Maturity", maturities, index=maturities.index(default_short))

        # Filter long-term options to be strictly larger than short-term
        long_options = [m for m in maturities if maturity_to_months(m) > maturity_to_months(maturity_short)]
        if not long_options:
            long_options = [maturity_short]  # fallback
        maturity_long = st.selectbox("Long-term Maturity", long_options, index=long_options.index(default_long) if default_long in long_options else 0)

        # Load data
        df_long = yield_funcs[country][maturity_long]().dropna().rename(columns={'value': f'yield_{maturity_long}'})
        df_short = yield_funcs[country][maturity_short]().dropna().rename(columns={'value': f'yield_{maturity_short}'})

        # Merge on date
        df = pd.merge(df_long, df_short, on='date')
        df['spread'] = df[f'yield_{maturity_long}'] - df[f'yield_{maturity_short}']

        # Time frame selector
        earliest_date = df['date'].min().date()
        latest_date = df['date'].max().date()
        timeframe = st.selectbox("**Time Frame**", ["1Y", "3Y", "5Y", "10Y", "MAX"])
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
        # Commentary
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
                {country} {maturity_long}-{maturity_short} spread indicates yield curve shape and market expectations.
            </div>
            """,
            unsafe_allow_html=True
        )

        # Filter by selected date range
        df_filtered = df[(df['date'] >= pd.to_datetime(start_date)) &
                         (df['date'] <= pd.to_datetime(end_date))]

        # Prepare DataFrame for plotting
        df_plot = df_filtered[['date', 'spread']].rename(columns={'spread': 'value'})

        # Plot the spread
        fig = plot_chart(
            df_plot,
            title=f"{country} {maturity_long}-{maturity_short} Yield Spread",
            chart_type="Line",
            hover_style="delta",
            delta_type=delta_type.lower(),
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

        # CSV Download
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

