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
        fig.update_traces(line=dict(width=3, color=chart_color), mode=mode)
    elif chart_type == "Step":
        fig = px.line(df, x='date', y='value', title=title, labels={'date': '', 'value': ''}, height=height)
        fig.update_traces(line_shape='hv', line=dict(width=3, color=chart_color), mode=mode)
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

def get_usa_10yr_yield_data():
    base_dir = os.path.dirname(__file__)
    file_path = os.path.join(base_dir, "USA_10_Year_Yield.txt")
        
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

def get_usa_2yr_yield_data():
    base_dir = os.path.dirname(__file__)
    file_path = os.path.join(base_dir, "USA_2_Year_Yield.txt")
  
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
        <a href="?page=FX%20Rates" target="_self">FX Rates</a>
        <a href="?page=Compare" target="_self">Compare</a>
        <a href="?page=Calendar" target="_self">Calendar</a>
        <a href="?page=Login" target="_self">Login</a>
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
            "10Y Yield",
            "2Y Yield"
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
        elif indicator == "10Y Yield":
            df = get_usa_10yr_yield_data()
            date_format = "daily"
            tickformat_override = "%b %Y"
        elif indicator == "2Y Yield":
            df = get_usa_2yr_yield_data()
            date_format = "daily"
            tickformat_override = "%b %Y"

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
            "Unemployment Rate": "The unemployment rate is a key measure of labor market health in the U.S. economy.",
            "10Y Yield": "The 10-Year Treasury yield is a benchmark for global borrowing costs and risk sentiment.",
            "2Y Yield": "The 2-Year Treasury yield reflects expectations for near-term Fed policy moves."
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
            "10Y Yield": "10-Year Treasury Yield (%)",
            "2Y Yield": "2-Year Treasury Yield (%)"
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
            "Unemployment Rate",
            "10Y Yield",
            "2Y Yield"
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
        elif indicator == "10Y Yield":
            df = get_japan_10yr_yield_data()
            date_format = "daily"
            tickformat_override = "%b %Y"
        elif indicator == "2Y Yield":
            df = get_japan_2yr_yield_data()
            date_format = "daily"
            tickformat_override = "%b %Y"

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
            "Unemployment Rate": "The unemployment rate is a key measure of labor market health in the U.S. economy.",
            "10Y Yield": "The 10-Year Treasury yield is a benchmark for global borrowing costs and risk sentiment.",
            "2Y Yield": "The 2-Year Treasury yield reflects expectations for near-term Fed policy moves."
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
            "Unemployment Rate": "Unemployment Rate (%)",
            "10Y Yield": "10-Year Treasury Yield (%)",
            "2Y Yield": "2-Year Treasury Yield (%)"
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
            file_name=f"USA_{indicator.replace(' ', '_')}_data.csv",
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
            "Unemployment Rate",
            "10Y Yield",
            "2Y Yield"
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
        elif indicator == "10Y Yield":
            df = get_uk_10yr_yield_data()
            date_format = "daily"
            tickformat_override = "%b %Y"
        elif indicator == "2Y Yield":
            df = get_uk_2yr_yield_data()
            date_format = "daily"
            tickformat_override = "%b %Y"

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
            "Unemployment Rate": "The unemployment rate is a key measure of labor market health in the U.S. economy.",
            "10Y Yield": "The 10-Year Treasury yield is a benchmark for global borrowing costs and risk sentiment.",
            "2Y Yield": "The 2-Year Treasury yield reflects expectations for near-term Fed policy moves."
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
            "Unemployment Rate": "Unemployment Rate (%)",
            "10Y Yield": "10-Year Treasury Yield (%)",
            "2Y Yield": "2-Year Treasury Yield (%)"
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
            file_name=f"USA_{indicator.replace(' ', '_')}_data.csv",
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
            "Unemployment Rate",
            "10Y Yield",
            "2Y Yield"
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
        elif indicator == "10Y Yield":
            df = get_euro_10yr_yield_data()
            date_format = "daily"
            tickformat_override = "%b %Y"
        elif indicator == "2Y Yield":
            df = get_euro_2yr_yield_data()
            date_format = "daily"
            tickformat_override = "%b %Y"

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
            "Unemployment Rate": "The unemployment rate is a key measure of labor market health in the U.S. economy.",
            "10Y Yield": "The 10-Year Treasury yield is a benchmark for global borrowing costs and risk sentiment.",
            "2Y Yield": "The 2-Year Treasury yield reflects expectations for near-term Fed policy moves."
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
            "Unemployment Rate": "Unemployment Rate (%)",
            "10Y Yield": "10-Year Treasury Yield (%)",
            "2Y Yield": "2-Year Treasury Yield (%)"
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
            file_name=f"USA_{indicator.replace(' ', '_')}_data.csv",
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
        chart_type = st.selectbox("Chart Type", ["Line", "Area", "Bar"])

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



if page == "Compare":
    col1, col2 = st.columns([1, 3])

    with col1:
        st.header("📊 Compare Indicators")

        indicator_options = {
            # USA
            "USA: Interest Rate": "FEDFUNDS",
            "USA: Inflation Rate (YoY %)": "CPIAUCSL",
            "USA: GDP Growth Rate": "A191RL1Q225SBEA",
            "USA: Unemployment Rate": "UNRATE",
            "USA: 10Y Yield": "DGS10",
            "USA: 2Y Yield": "DGS2",
            # Japan
            "Japan: CPI YoY Change (%)": "JP_CPI",
            "Japan: Unemployment Rate": "JP_UNEMPLOYMENT",
            "Japan: Real GDP QoQ Growth": "JP_GDP",
            "Japan: Interest Rate (Short-Term)": "IRSTCI01JPM156N",
            "Japan: Interest Rate (Long-Term)": "IRLTLT01JPM156N",
            # UK
            "UK: BoE Base Rate (%)": "UK_BASE_RATE",
            "UK: CPI Inflation Rate (YoY %)": "UK_CPI",
            "UK: GDP Growth Rate (QoQ %)": "UK_GDP",
            "UK: Unemployment Rate": "UK_UNEMPLOYMENT",
            "UK: Interest Rate (Short-Term)": "IR3TIB01GBM156N",
            "UK: Interest Rate (Long-Term)": "IRLTLT01GBM156N",
            # Euro Area
            "Euro: ECB Main Refinancing Rate": "EU_REF_RATE",
            "Euro: HICP Annual Change": "EU_HICP",
            "Euro: Unemployment Rate": "EU_UNEMPLOYMENT",
            "Euro: GDP Quarterly Growth": "EU_GDP",
            "Euro: Interest Rate (Short-Term)": "IR3TIB01EZM156N",
            "Euro: Interest Rate (Long-Term)": "IRLTLT01EZM156N",
            # FX
            "FX: EUR/USD": "EURUSD=X",
            "FX: GBP/USD": "GBPUSD=X",
            "FX: USD/JPY": "USDJPY=X",
            "FX: EUR/GBP": "EURGBP=X",
            "FX: EUR/JPY": "EURJPY=X",
            "FX: GBP/JPY": "GBPJPY=X",
            "FX: DXY": "DX-Y.NYB"
        }

        indicator1_label = st.selectbox("Select Indicator 1", list(indicator_options.keys()))
        indicator2_label = st.selectbox("Select Indicator 2", list(indicator_options.keys()))
        chart_type = st.selectbox("Chart Type", ["Line", "Area", "Bar"])

        def load_indicator_data(label, code):
            if code.startswith("JP_"):
                if code == "JP_CPI":
                    return get_japan_cpi_yoy_data()
                elif code == "JP_UNEMPLOYMENT":
                    return get_japan_unemployment_data()
                elif code == "JP_GDP":
                    df = get_japan_gdp_qoq_growth()
                    return df.rename(columns={'gdp_qoq_growth': 'value'})
            elif code.startswith("UK_"):
                if code == "UK_BASE_RATE":
                    return get_uk_base_rate_from_url().rename(columns={'Date': 'date', 'Bank Rate': 'value'})
                elif code == "UK_CPI":
                    df = get_uk_cpi_yoy()
                    return df.rename(columns={'cpi_yoy': 'value'})
                elif code == "UK_GDP":
                    df = get_uk_gdp_qoq()
                    return df.rename(columns={'gdp_qoq': 'value'})
                elif code == "UK_UNEMPLOYMENT":
                    df = get_uk_unemployment_rate()
                    return df.rename(columns={'unemployment_rate': 'value'})
            elif code.startswith("EU_"):
                if code == "EU_REF_RATE":
                    return get_ecb_refinancing_rate()
                elif code == "EU_HICP":
                    return get_euro_hicp_annual_gzip()
                elif code == "EU_UNEMPLOYMENT":
                    return get_euro_unemployment_gzip()
                elif code == "EU_GDP":
                    return get_gdp_quarterly_gzip()
            elif code.endswith("=X") or code == "DX-Y.NYB":
                return get_fx_data_yahoo(code, start_date=dt.date(1980, 1, 1), end_date=dt.date.today())
            elif code == "CPIAUCSL":  # USA CPI → convert to YoY %
                raw = fred.get_series(code)
                df = pd.DataFrame(raw).reset_index()
                df.columns = ['date', 'value']
                df['value'] = (df['value'].pct_change(periods=12) * 100).round(2)
                return df.dropna()
            else:
                return get_data(code)

        # Load + drop missing
        df1 = load_indicator_data(indicator1_label, indicator_options[indicator1_label]).dropna()
        df2 = load_indicator_data(indicator2_label, indicator_options[indicator2_label]).dropna()

        df1_min, df1_max = df1['date'].min().date(), df1['date'].max().date()
        df2_min, df2_max = df2['date'].min().date(), df2['date'].max().date()

        # New logic: End date = latest date of either indicator
        latest_date = max(df1_max, df2_max)

        # Start date = latest_date - 1825 days (5 years) or earliest date whichever is later
        earliest_start = min(df1_min, df2_min)
        default_start_date = max(earliest_start, latest_date - dt.timedelta(days=1825))

        start_date = st.date_input("Start Date", default_start_date, min_value=earliest_start, max_value=latest_date)
        end_date = st.date_input("End Date", latest_date, min_value=earliest_start, max_value=latest_date)

        if start_date > end_date:
            st.warning("Start date cannot be after end date.")
            st.stop()

    with col2:
        # Filter data to user date range
        df1_filtered = df1[(df1['date'] >= pd.to_datetime(start_date)) & (df1['date'] <= pd.to_datetime(end_date))]
        df2_filtered = df2[(df2['date'] >= pd.to_datetime(start_date)) & (df2['date'] <= pd.to_datetime(end_date))]

        if df1_filtered.empty or df2_filtered.empty:
            st.warning("Not enough data for this date range.")
            st.stop()

        # Get latest available value for each indicator (from filtered data)
        latest_val_1 = df1_filtered.iloc[-1]['value']
        latest_val_2 = df2_filtered.iloc[-1]['value']

        # Format values for display nicely (round 4 decimals if float)
        def format_val(v):
            return f"{v:.4f}" if isinstance(v, float) else str(v)

        title_str = (f"{indicator1_label} (Latest: {format_val(latest_val_1)}) "
                     f"vs {indicator2_label} (Latest: {format_val(latest_val_2)})")

        st.subheader(title_str)
        st.caption(f"Date Range: {start_date.strftime('%d %B %Y')} → {end_date.strftime('%d %B %Y')}")

        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=df1_filtered['date'],
            y=df1_filtered['value'],
            mode='lines',
            name=indicator1_label,
            yaxis="y1"
        ))

        fig.add_trace(go.Scatter(
            x=df2_filtered['date'],
            y=df2_filtered['value'],
            mode='lines',
            name=indicator2_label,
            yaxis="y2"
        ))

        fig.update_layout(
            title=title_str,
            xaxis=dict(title="Date"),
            yaxis=dict(title=indicator1_label, side="left"),
            yaxis2=dict(title=indicator2_label, overlaying="y", side="right", showgrid=False),
            template="plotly_white",
            legend=dict(x=0.01, y=1.1, orientation="h")
        )

        st.plotly_chart(fig, use_container_width=True)
        
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
 

if page == "Login":
    authenticator.login(location='main', key="login_form")

    auth_status = st.session_state.get("authentication_status")
    name = st.session_state.get("name")
    username = st.session_state.get("username")

    if auth_status is False:
        st.error("❌ Incorrect username or password")
    elif auth_status is None:
        st.warning("Please enter your username and password")
    elif auth_status:
        st.success(f"Welcome {name}!")
        st.write("You are logged in.")