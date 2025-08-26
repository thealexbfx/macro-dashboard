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
def plot_chart(df, title, chart_type, height=450, date_format="daily",
               yaxis_suffix='', reference_lines=None, shaded_regions=None,
               tickformat_override=None):

    df = df.copy()
    chart_color = '#1f77b4'

    # -------------------- Hover Formatting --------------------
    if date_format == "daily":
        hover_date_format = "%d %B %Y"
    elif date_format == "monthly":
        hover_date_format = "%B %Y"
    elif date_format == "quarterly":
        df['hover_label'] = df['date'].dt.to_period('Q').apply(lambda x: f"Q{x.quarter} {x.year}")
        hovertemplate = "<b>%{customdata}</b><br>Value: %{y:.2f}" + yaxis_suffix + "<extra></extra>"
    else:
        hover_date_format = "%Y-%m-%d"

    # -------------------- Chart Type --------------------
    if chart_type == "Line":
        fig = px.line(df, x='date', y='value', title=title, labels={'date': '', 'value': ''}, height=height)
        fig.update_traces(line=dict(width=3, color=chart_color), mode='lines')
    elif chart_type == "Step":
        fig = px.line(df, x='date', y='value', title=title, labels={'date': '', 'value': ''}, height=height)
        fig.update_traces(line_shape='hv', line=dict(width=3, color=chart_color))
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
        margin=dict(l=30, r=30, t=50, b=30),
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
            bgcolor="white",
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

    # -------------------- Hover Template --------------------
    if date_format == "quarterly":
        # Hover for all quarters
        fig.update_traces(hovertemplate=hovertemplate, customdata=df['hover_label'])

        # Only show Q4 labels on x-axis
        tickvals = df[df['date'].dt.quarter == 4]['date']
        ticktext = df[df['date'].dt.quarter == 4]['hover_label']
        fig.update_xaxes(tickmode='array', tickvals=tickvals, ticktext=ticktext)

    else:
        # Daily/monthly hover
        fig.update_traces(
            hovertemplate=f"<b>%{{x|{hover_date_format}}}</b><br>Value: %{{y:.2f}}{yaxis_suffix}<extra></extra>"
        )

        # Apply tickformat_override using ticktext for clean axis labels
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
    background-color: #f2f2f2;
    width: 100%;
    padding: 1rem 2rem;
    display: flex;
    justify-content: space-between;
    align-items: center;
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

    display: flex;        /* make it a flex container */
    align-items: center;  /* vertically center text */
    height: 100%;         /* match parent menu height */
    padding: 0;           /* remove extra padding */
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

    st.markdown('<div class="chart-title">📉 Sample FX Chart: US Dollar Index (DXY)</div>', unsafe_allow_html=True)
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
    st.markdown("<h2 style='text-align:left; font-weight:bold;'>USA Macro Data</h2>", unsafe_allow_html=True)
    col1, col2 = st.columns([1, 5])

    with col1:
        # Dropdowns
        indicator = st.selectbox("**Indicator**", [
            "Interest Rate",
            "Inflation Rate",
            "GDP Growth Rate",
            "Unemployment Rate",
            "10Y Yield",
            "2Y Yield"
        ])
        chart_type = st.selectbox("**Chart Type**", ["Line", "Area", "Bar", "Step"])

        # Load data based on indicator
        if indicator == "Interest Rate":
            df = get_usa_interest_rate_data()
            date_format = "daily"
            tickformat_override = "%b %Y"
        elif indicator == "Inflation Rate":
            df = get_usa_cpi_yoy_data()
            date_format = "monthly"
        elif indicator == "GDP Growth Rate":
            df = get_usa_gdp_qoq_data()
            date_format = "quarterly"
            df['tick_label'] = df['date'].dt.to_period('Q').apply(lambda x: f"Q{x.quarter} {x.year}")
        elif indicator == "Unemployment Rate":
            df = get_usa_unemployment_rate_data()
            date_format = "monthly"
        elif indicator == "10Y Yield":
            df = get_usa_10yr_yield_data()
            date_format = "daily"
            tickformat_override = "%b %Y"
        elif indicator == "2Y Yield":
            df = get_usa_2yr_yield_data()
            date_format = "daily"
            tickformat_override = "%b %Y"

        df = df.dropna()
        earliest_date = df['date'].min().date()
        latest_date = df['date'].max().date()

        # -------- Time Frame Selector --------
        timeframe = st.selectbox("**Time Frame**", ["1Y", "3Y", "5Y", "10Y", "MAX"])

        if timeframe != "MAX":
            years = int(timeframe.replace("Y", ""))
            default_start_date = max(earliest_date, latest_date - dt.timedelta(days=365*years))
        else:
            default_start_date = earliest_date

        # Date inputs
        start_date = st.date_input("**Start Date**", default_start_date, min_value=earliest_date, max_value=latest_date)
        end_date = st.date_input("**End Date**", latest_date, min_value=earliest_date, max_value=latest_date)

        if start_date > end_date:
            st.warning("Start date cannot be after end date.")
            st.stop()

    with col2:
        # Filter data
        df = df[(df['date'] >= pd.to_datetime(start_date)) & (df['date'] <= pd.to_datetime(end_date))]

        # Dynamic Title
        titles = {
            "Interest Rate": "Federal Funds Rate (%)",
            "Inflation Rate": "CPI YoY (%)",
            "GDP Growth Rate": "Real GDP Growth Rate (QoQ Annualized %)",
            "Unemployment Rate": "Unemployment Rate (%)",
            "10Y Yield": "10-Year Government Bond Yield (%)",
            "2Y Yield": "2-Year Government Bond Yield (%)"
        }

        # Chart plotting
        st.plotly_chart(
            plot_chart(df, titles[indicator], chart_type, date_format=date_format),
            use_container_width=True
        )

# -------- Japan Tab --------
if page == "Japan":
    col1, col2 = st.columns([1, 3])  # Make col1 narrow, col2 wide

    with col1:
        st.header("🇯🇵 Japan Macro Data")

        indicator = st.selectbox("Select Indicator", [
            "CPI YoY Change (%)",
            "Unemployment Rate",
            "Real GDP QoQ Growth",
            "Interest Rate (Short-Term)",
            "Interest Rate (Long-Term)",
            "BOJ Interest Rate"
        ])

        chart_type = st.selectbox("Chart Type", ["Line", "Area", "Bar"])

        # Load full dataset to determine bounds
        if indicator == "BOJ Interest Rate":  # <-- new option
            df = get_japan_interest_rate_data()
        elif indicator == "CPI YoY Change (%)":
            df = get_japan_cpi_yoy_data()
        elif indicator == "Unemployment Rate":
            df = get_japan_unemployment_data()
        elif indicator == "Real GDP QoQ Growth":
            df = get_japan_gdp_qoq_growth()
            df.rename(columns={'gdp_qoq_growth': 'value'}, inplace=True)
        elif indicator == "Interest Rate (Short-Term)":
            df = get_data("IRSTCI01JPM156N")
        elif indicator == "Interest Rate (Long-Term)":
            df = get_data("IRLTLT01JPM156N")
        
        df = df.dropna()
        earliest_date = df['date'].min().date()
        latest_date = df['date'].max().date()
        default_start_date = max(earliest_date, latest_date - dt.timedelta(days=1825))

        # Date input widgets
        start_date = st.date_input("Start Date", default_start_date, min_value=earliest_date, max_value=latest_date)
        end_date = st.date_input("End Date", latest_date, min_value=earliest_date, max_value=latest_date)

        if start_date > end_date:
            st.warning("Start date cannot be after end date.")
            st.stop()

    with col2:
        df = df[(df['date'] >= pd.to_datetime(start_date)) & (df['date'] <= pd.to_datetime(end_date))]

        if df.empty:
            st.warning("No data available for this date range.")
        else:
            if indicator == "CPI YoY Change (%)":
                st.subheader("Japan CPI Year-over-Year Change (All Items)")
                st.plotly_chart(plot_chart(df, "CPI YoY Change (%)", chart_type), use_container_width=True)

            elif indicator == "Unemployment Rate":
                st.subheader("Japan Unemployment Rate")
                st.plotly_chart(plot_chart(df, "Unemployment Rate", chart_type), use_container_width=True)

            elif indicator == "Real GDP QoQ Growth":
                st.subheader("Japan Real GDP QoQ Growth Rate (%)")
                st.plotly_chart(plot_chart(df, "Real GDP QoQ Growth", chart_type), use_container_width=True)

            elif indicator == "Interest Rate (Short-Term)":
                st.subheader("Japan Short-Term Interest Rate (FRED: IRSTCI01JPM156N)")
                st.plotly_chart(plot_chart(df, "Interest Rate (Short-Term)", chart_type), use_container_width=True)

            elif indicator == "Interest Rate (Long-Term)":
                st.subheader("Japan Long-Term Interest Rate (FRED: IRLTLT01JPM156N)")
                st.plotly_chart(plot_chart(df, "Interest Rate (Long-Term)", chart_type), use_container_width=True)
                
            elif indicator == "BOJ Interest Rate":
                st.subheader("BOJ Official Interest Rate")
                st.plotly_chart(plot_chart(df, "BOJ Interest Rate (%)", chart_type), use_container_width=True)

        
# -------- UK Tab --------        
if page == "UK":
    col1, col2 = st.columns([1, 3])  # Left: narrow for controls, Right: wide for output

    with col1:
        st.header("🇬🇧 UK Macro Data")

        indicator = st.selectbox("Select Indicator", [
            "Bank of England Base Rate (%)",
            "CPI Inflation Rate (YoY %)",
            "GDP Growth Rate (QoQ %)",
            "Unemployment Rate",
            "Interest Rate (Short-Term)",
            "Interest Rate (Long-Term)"
        ])

        chart_type = st.selectbox("Chart Type", ["Line", "Area", "Bar"])

        # Load full dataset temporarily for date bounds
        if indicator == "Bank of England Base Rate (%)":
            df = get_uk_interest_rate_data().rename(columns={'Date': 'date', 'Bank Rate': 'value'})
        elif indicator == "CPI Inflation Rate (YoY %)":
            df = get_uk_cpi_yoy()
            df = df.rename(columns={'cpi_yoy': 'value'}) if 'cpi_yoy' in df.columns else df
        elif indicator == "GDP Growth Rate (QoQ %)":
            df = get_uk_gdp_qoq()
            df = df.rename(columns={'gdp_qoq': 'value'}) if 'gdp_qoq' in df.columns else df
        elif indicator == "Unemployment Rate":
            df = get_uk_unemployment_rate()
            df = df.rename(columns={'unemployment_rate': 'value'}) if 'unemployment_rate' in df.columns else df
        elif indicator == "Interest Rate (Short-Term)":
            df = get_data("IR3TIB01GBM156N")
        elif indicator == "Interest Rate (Long-Term)":
            df = get_data("IRLTLT01GBM156N")

        df = df.dropna()
        earliest_date = df['date'].min().date()
        latest_date = df['date'].max().date()
        default_start_date = max(earliest_date, latest_date - dt.timedelta(days=1825))

        # Date inputs with safe bounds
        start_date = st.date_input("Start Date", default_start_date, min_value=earliest_date, max_value=latest_date)
        end_date = st.date_input("End Date", latest_date, min_value=earliest_date, max_value=latest_date)

        if start_date > end_date:
            st.warning("Start date cannot be after end date.")
            st.stop()

    with col2:
        df = df[(df['date'] >= pd.to_datetime(start_date)) & (df['date'] <= pd.to_datetime(end_date))]

        if df.empty:
            st.warning("No data found for this date range.")
        else:
            if indicator == "Bank of England Base Rate (%)":
                st.subheader("Bank of England Base Rate (%)")
                st.plotly_chart(plot_chart(df, "Bank of England Base Rate (%)", chart_type), use_container_width=True)

            elif indicator == "CPI Inflation Rate (YoY %)":
                st.subheader("UK CPI Inflation Rate (YoY %)")
                st.plotly_chart(plot_chart(df, "UK CPI Inflation Rate (YoY %)", chart_type), use_container_width=True)

            elif indicator == "GDP Growth Rate (QoQ %)":
                st.subheader("UK Real GDP QoQ Growth (%)")
                st.plotly_chart(plot_chart(df, "UK Real GDP QoQ Growth (%)", chart_type), use_container_width=True)

            elif indicator == "Unemployment Rate":
                st.subheader("UK Unemployment Rate (%)")
                st.plotly_chart(plot_chart(df, "UK Unemployment Rate (%)", chart_type), use_container_width=True)

            elif indicator == "Interest Rate (Short-Term)":
                st.subheader("UK Short-Term Interest Rate (FRED: IR3TIB01GBM156N)")
                st.plotly_chart(plot_chart(df, "Interest Rate (Short-Term)", chart_type), use_container_width=True)

            elif indicator == "Interest Rate (Long-Term)":
                st.subheader("UK Long-Term Interest Rate (FRED: IRLTLT01GBM156N)")
                st.plotly_chart(plot_chart(df, "Interest Rate (Long-Term)", chart_type), use_container_width=True)
        
# -------- EURO Tab --------
if page == "EURO":
    col1, col2 = st.columns([1, 3])  # Controls (left), output (right)

    with col1:
        st.header("🇪🇺 Euro Area Macro Data")

        indicator = st.selectbox("Select Indicator", [
            "ECB Main Refinancing Rate",
            "HICP Annual Change (Eurostat gzip)",
            "Unemployment Rate (Seasonally Adjusted)",
            "GDP Quarterly Growth (Seasonally Adjusted)",
            "Interest Rate (Short-Term)",
            "Interest Rate (Long-Term)"
        ])

        chart_type = st.selectbox("Chart Type", ["Line", "Area", "Bar"])

        # Temporarily load full dataset for date range
        if indicator == "ECB Main Refinancing Rate":
            df = get_euro_interest_rate_data()
        elif indicator == "HICP Annual Change (Eurostat gzip)":
            df = get_euro_hicp_annual_gzip()
        elif indicator == "Unemployment Rate (Seasonally Adjusted)":
            df = get_euro_unemployment_gzip()
        elif indicator == "GDP Quarterly Growth (Seasonally Adjusted)":
            df = get_gdp_quarterly_gzip()
        elif indicator == "Interest Rate (Short-Term)":
            df = get_data("IR3TIB01EZM156N")
        elif indicator == "Interest Rate (Long-Term)":
            df = get_data("IRLTLT01EZM156N")

        df = df.dropna()
        earliest_date = df['date'].min().date()
        latest_date = df['date'].max().date()
        default_start_date = max(earliest_date, latest_date - dt.timedelta(days=1825))

        # Date inputs with bounds
        start_date = st.date_input("Start Date", default_start_date, min_value=earliest_date, max_value=latest_date)
        end_date = st.date_input("End Date", latest_date, min_value=earliest_date, max_value=latest_date)

        # Validation: prevent wrong ordering
        if start_date > end_date:
            st.warning("Start date cannot be after end date.")
            st.stop()

    with col2:
        df = df[(df['date'] >= pd.to_datetime(start_date)) & (df['date'] <= pd.to_datetime(end_date))]

        if df.empty:
            st.warning("No data found for this date range.")
        else:
            if indicator == "ECB Main Refinancing Rate":
                st.subheader("ECB Main Refinancing Rate (%)")
                st.plotly_chart(plot_chart(df, "ECB Refinancing Rate", chart_type), use_container_width=True)

            elif indicator == "HICP Annual Change (Eurostat gzip)":
                st.subheader("Euro Area HICP Annual Change (%)")
                st.plotly_chart(plot_chart(df, "Euro Area HICP Annual Change (%)", chart_type), use_container_width=True)

            elif indicator == "Unemployment Rate (Seasonally Adjusted)":
                st.subheader("Euro Area Unemployment Rate (Seasonally Adjusted)")
                st.plotly_chart(plot_chart(df, "Euro Area Unemployment Rate (%)", chart_type), use_container_width=True)

            elif indicator == "GDP Quarterly Growth (Seasonally Adjusted)":
                st.subheader("Euro Area GDP Quarterly Growth (%)")
                st.plotly_chart(plot_chart(df, "GDP Quarterly Growth (%)", chart_type), use_container_width=True)

            elif indicator == "Interest Rate (Short-Term)":
                st.subheader("EURO Short-Term Interest Rate (FRED: IR3TIB01EZM156N)")
                st.plotly_chart(plot_chart(df, "Interest Rate (Short-Term)", chart_type), use_container_width=True)

            elif indicator == "Interest Rate (Long-Term)":
                st.subheader("EURO Long-Term Interest Rate (FRED: IRLTLT01EZM156N)")
                st.plotly_chart(plot_chart(df, "Interest Rate (Long-Term)", chart_type), use_container_width=True)
        
# -------- FX Rates Tab --------
if page == "FX Rates":
    st.markdown("<h2 style='text-align:left; font-weight:bold;'>Forex Rates</h2>", unsafe_allow_html=True)
    col1, col2 = st.columns([1, 5])

    with col1:
       
        # Select indicator and chart type
        indicator = st.selectbox("Select Indicator", [
            "EUR/USD", "GBP/USD", "USD/JPY", "EUR/GBP", "EUR/JPY", "GBP/JPY", "DXY"
        ])
        chart_type = st.selectbox("Chart Type", ["Line", "Area", "Bar"])

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

        # Load full FX data
        df = get_fx_data_yahoo(ticker, start_date=dt.date(1980, 1, 1), end_date=dt.date.today())
        df = df.dropna()

        if df.empty:
            st.error("No data available.")
            st.stop()

        # Get dynamic min/max dates
        earliest_date = df['date'].min().date()
        latest_date = df['date'].max().date()

        # -------- Time Frame Selector --------
        timeframe = st.selectbox("**Time Frame**", ["1Y", "3Y", "5Y", "10Y", "MAX"])
        if timeframe != "MAX":
            years = int(timeframe.replace("Y", ""))
            default_start_date = max(earliest_date, latest_date - dt.timedelta(days=365*years))
        else:
            default_start_date = earliest_date

        # Date inputs
        start_date = st.date_input("Start Date", default_start_date, min_value=earliest_date, max_value=latest_date)
        end_date = st.date_input("End Date", latest_date, min_value=earliest_date, max_value=latest_date)

        # Validate dates
        if start_date > end_date:
            st.warning("Start date must be before end date.")
            st.stop()

    with col2:
        

        # Filter data by user-selected date range
        df_filtered = df[(df['date'] >= pd.to_datetime(start_date)) & 
                         (df['date'] <= pd.to_datetime(end_date))]

        # Plot chart
        st.plotly_chart(plot_chart(df_filtered, title, chart_type), use_container_width=True)

        

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