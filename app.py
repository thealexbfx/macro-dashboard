import streamlit as st
import pandas as pd
from fredapi import Fred
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

# -------- API Setup --------
load_dotenv()

fred_api_key = os.getenv("FRED_API_KEY")
estat_api_key = os.getenv("ESTAT_API_KEY")

fred = Fred(api_key=fred_api_key)

# -------- Helper Functions --------
def get_data(series_id, start_date, end_date):
    data = fred.get_series(series_id)
    df = pd.DataFrame(data)
    df.columns = ['value']
    df.index.name = 'date'
    df = df.reset_index()
    df = df[(df['date'] >= pd.to_datetime(start_date)) & (df['date'] <= pd.to_datetime(end_date))]
    return df

def plot_chart(df, title, chart_type):
    if chart_type == "Line":
        fig = px.line(df, x='date', y='value', height=600, title=title)
    elif chart_type == "Area":
        fig = px.area(df, x='date', y='value', height=600, title=title)
    elif chart_type == "Bar":
        fig = px.bar(df, x='date', y='value', height=600, title=title)
    return fig

def get_japan_cpi_yoy_data():
    url = "https://api.e-stat.go.jp/rest/3.0/app/json/getStatsData"
    params = {
        "appId": estat_api_key,
        "statsDataId": "0003427113",
        "cdArea": "00000",  # All-Japan
        "lang": "E",
        "metaGetFlg": "Y",
        "cntGetFlg": "N",
        "explanationGetFlg": "Y",
        "annotationGetFlg": "Y",
        "sectionHeaderFlg": "1"
    }

    response = requests.get(url, params=params)
    response.raise_for_status()
    json_data = response.json()

    # DEBUG: print keys at top level and sample VALUE entries
    #st.write("Top-level keys in JSON:", json_data.keys())
    try:
        values = json_data['GET_STATS_DATA']['STATISTICAL_DATA']['DATA_INF']['VALUE']
        #st.write(f"Number of VALUE entries: {len(values)}")
        # Show first 5 entries raw
        #for i, val in enumerate(values[:5]):
            #st.write(f"Entry {i}:", val)
    except Exception as e:
        st.write("Error accessing VALUE in JSON:", e)
        return pd.DataFrame()

    records = []
    for item in values[:600]:
        # Temporarily comment out filter to check all items:
        # if item.get('@cat01') == '000' and item.get('@tab') == '020':
        time_str = item.get('@time')
        val_str = item.get('$')
        #st.write(f"Time: {time_str}, Value: {val_str}, Cat01: {item.get('@cat01')}, Tab: {item.get('@tab')}")
        try:
            timestr1 = time_str[:4] + time_str[-2:]
            if time_str[-2:] != '00':
                date = pd.to_datetime(timestr1, format='%Y%m')
                value = float(val_str) if val_str != '-' else None
                if value is not None:
                    records.append({'date': date, 'value': value})
        except Exception as e:
            st.write(f"Error parsing item: {e}")
            continue

    df = pd.DataFrame(records)
    df = df.sort_values('date')
    df['value'] = (df['value'].pct_change(periods=12) * 100).round(2)
    return df
    
def get_japan_unemployment_data():
    url = "https://api.e-stat.go.jp/rest/3.0/app/json/getStatsData"
    params = {
        "appId": estat_api_key,
        "statsDataId": "0003006300",  # Unemployment rate dataset
        "cdTab": "02",                # Tab code: Rate
        "cdCat01": "08",              # Labour force status: Unemployed person
        "cdCat02": "0",               # Sex: Both sexes (aggregate)
        "cdCat03": "000",             # Industry: All industries
        "cdCat04": "00",              # Household: Total
        "cdArea": "00000",            # All-Japan
        "lang": "E",
        "metaGetFlg": "Y",
        "cntGetFlg": "N",
        "explanationGetFlg": "Y",
        "annotationGetFlg": "Y",
        "sectionHeaderFlg": "1"
    }

    response = requests.get(url, params=params)
    response.raise_for_status()
    json_data = response.json()

    try:
        values = json_data['GET_STATS_DATA']['STATISTICAL_DATA']['DATA_INF']['VALUE']
    except Exception as e:
        st.write("Error accessing VALUE in JSON:", e)
        return pd.DataFrame()

    records = []
    for item in values:
        # Filter explicitly just in case
        if item.get('@cat02') != '0':
            continue
        if item.get('@cat03') != '000':
            continue
        if item.get('@cat04') != '00':
            continue

        time_str = item.get('@time')
        val_str = item.get('$')
        try:
            if val_str in ('-', '…', None):
                continue

            timestr1 = time_str[:4] + time_str[-2:]
            if time_str[-2:] != '00':  # Ignore yearly totals or invalid months
                date = pd.to_datetime(timestr1, format='%Y%m')
                value = float(val_str)
                records.append({'date': date, 'value': value})
        except Exception as e:
            st.write(f"Error parsing item: {e}")
            continue

    df = pd.DataFrame(records)
    df = df.sort_values('date')
    return df
    
def get_japan_gdp_qoq_growth():
    url = 'https://www.esri.cao.go.jp/en/sna/data/sokuhou/files/2025/qe251_2/gdemenuea.html'
    target_text = "Real, Seasonally Adjusted Series (Quarter-to-Quarter)"

    page_resp = requests.get(url)
    page_resp.raise_for_status()

    from bs4 import BeautifulSoup
    soup = BeautifulSoup(page_resp.text, 'html.parser')

    csv_url = None
    for link in soup.find_all('a', href=True):
        if target_text in link.text:
            csv_url = urljoin(url, link['href'])
            break

    if not csv_url:
        st.error("Could not find the GDP CSV link on the page.")
        return pd.DataFrame()

    csv_resp = requests.get(csv_url)
    csv_resp.raise_for_status()
    content = csv_resp.content.decode('cp932')

    reader = csv.reader(io.StringIO(content))

    results = []
    last_year = None
    for row in reader:
        if not row or len(row) < 2:
            continue
        quarter_label = row[0].strip()

        # Track the year if it's present in this row
        if '/' in quarter_label:
            parts = quarter_label.split('/')
            if len(parts) == 2:
                try:
                    last_year = int(parts[0].strip())
                    quarter = parts[1].strip().replace('.', '')
                except:
                    continue
        else:
            quarter = quarter_label.strip().replace('.', '')

        if last_year is None or not quarter:
            continue

        # Determine quarter end month
        if '1- 3' in quarter:
            month = 3
        elif '4- 6' in quarter:
            month = 6
        elif '7- 9' in quarter:
            month = 9
        elif '10-12' in quarter:
            month = 12
        else:
            continue  # Skip unrecognized quarters

        # Get first valid numeric value
        first_value = None
        for val in row[1:]:
            val = val.strip()
            if val and (val[0].isdigit() or val[0] == '-' or val[0] == '.'):
                try:
                    first_value = float(val)
                    break
                except ValueError:
                    continue

        if first_value is not None:
            results.append({
                'date': pd.Timestamp(year=last_year, month=month, day=1),
                'gdp_qoq_growth': first_value
            })

    df = pd.DataFrame(results)
    df = df.sort_values('date')
    return df

def get_uk_base_rate_from_url():
    url = "https://www.bankofengland.co.uk/-/media/boe/files/monetary-policy/baserate.xls"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/115.0.0.0 Safari/537.36"
    }

    response = requests.get(url, headers=headers)
    response.raise_for_status()

    xls = pd.ExcelFile(BytesIO(response.content)), engine='openpyxl'
    sheet_name = "HISTORICAL SINCE 1694"

    df_raw = xls.parse(sheet_name, header=None)
    df_raw = df_raw.dropna(how='all').reset_index(drop=True)

    # Forward fill the Year column (column 0)
    df_raw[0] = df_raw[0].ffill()

    # Filter for years >= 1951
    df_data = df_raw[df_raw[0].apply(lambda x: str(x).isdigit() and int(x) >= 1951)].copy()

    # Select columns: Year, Day, Month, Bank Rate
    df_data = df_data[[0, 1, 2, 3]]
    df_data.columns = ['Year', 'Day', 'Month', 'Bank Rate']

    # Remove rows where 'Day' is not numeric (to exclude e.g. 'no changes' rows)
    df_data = df_data[pd.to_numeric(df_data['Day'], errors='coerce').notnull()]
    df_data['Day'] = df_data['Day'].astype(int)

    # Map month names to numbers
    month_map = {
        'Jan':1, 'Feb':2, 'Mar':3, 'Apr':4, 'May':5, 'Jun':6,
        'Jul':7, 'Aug':8, 'Sep':9, 'Oct':10, 'Nov':11, 'Dec':12
    }
    df_data['Month'] = df_data['Month'].map(month_map)

    # Construct datetime column
    df_data['Date'] = pd.to_datetime(df_data[['Year','Month','Day']])

    # Sort by date ascending
    df_data = df_data.sort_values('Date').reset_index(drop=True)

    # Convert Bank Rate to numeric, coerce errors to NaN
    df_data['Bank Rate'] = pd.to_numeric(df_data['Bank Rate'], errors='coerce')

    # Filter date range from 1951-01-01 to today
    df_final = df_data[(df_data['Date'] >= '1951-01-01') & (df_data['Date'] <= pd.Timestamp.today())]

    return df_final[['Date', 'Bank Rate']]

def get_uk_cpi_yoy():
    url = "https://www.ons.gov.uk/generator?format=csv&uri=/economy/inflationandpriceindices/timeseries/d7g7/mm23"
    response = requests.get(url)
    response.raise_for_status()

    # Load CSV, skip bad rows
    df = pd.read_csv(io.StringIO(response.content.decode("utf-8")), header=None)

    # Filter only rows that look like '2025 JAN' or similar
    df = df[df[0].str.match(r"^\d{4} [A-Z]{3}$", na=False)]

    # Rename columns for consistency
    df.columns = ['date', 'value']

    # Convert date
    df['date'] = pd.to_datetime(df['date'], format='%Y %b')

    # Convert value to float
    df['value'] = pd.to_numeric(df['value'], errors='coerce')

    df = df.dropna()
    df = df.sort_values('date')
    return df
    
def get_uk_gdp_qoq():
    url = "https://www.ons.gov.uk/generator?format=csv&uri=/economy/grossdomesticproductgdp/timeseries/ihyq/pn2"
    response = requests.get(url)
    response.raise_for_status()

    df = pd.read_csv(io.StringIO(response.content.decode("utf-8")), header=None)

    # Keep only rows that look like "2024 Q1"
    df = df[df[0].str.match(r"^\d{4} Q[1-4]$", na=False)]
    df.columns = ['date_str', 'value']

    # Extract year and quarter
    df['year'] = df['date_str'].str[:4].astype(int)
    df['quarter'] = df['date_str'].str[-2:]

    # Map quarter to month-end date
    quarter_to_month = {
        "Q1": 3,
        "Q2": 6,
        "Q3": 9,
        "Q4": 12
    }

    df['month'] = df['quarter'].map(quarter_to_month)
    df['date'] = pd.to_datetime({
        'year': df['year'],
        'month': df['month'],
        'day': 1
    })

    df['value'] = pd.to_numeric(df['value'], errors='coerce')
    df = df[['date', 'value']].dropna().sort_values('date')
    return df
    
def get_uk_unemployment_rate():
    url = "https://www.ons.gov.uk/generator?format=csv&uri=/employmentandlabourmarket/peoplenotinwork/unemployment/timeseries/mgsx/lms"
    response = requests.get(url)
    response.raise_for_status()

    df = pd.read_csv(io.StringIO(response.content.decode("utf-8")), header=None)

    # Keep only rows like "2025 JAN","4.4"
    df = df[df[0].str.match(r"^\d{4} [A-Z]{3}$", na=False)]

    # Rename columns
    df.columns = ['date_str', 'value']

    # Convert date_str to datetime
    df['date'] = pd.to_datetime(df['date_str'], format='%Y %b')

    # Convert value to float
    df['value'] = pd.to_numeric(df['value'], errors='coerce')

    # Drop rows with missing values and sort
    df = df[['date', 'value']].dropna().sort_values('date')
    return df

import requests
import pandas as pd

def get_ecb_refinancing_rate(start_date, end_date):
    # Convert start_date and end_date to pd.Timestamp to avoid comparison issues
    start_date = pd.Timestamp(start_date)
    end_date = pd.Timestamp(end_date)

    url = "https://sdw-wsrest.ecb.europa.eu/service/data/FM/B.U2.EUR.4F.KR.MRR_FR.LEV"
    params = {
        'startPeriod': start_date.strftime('%Y-%m'),
        'endPeriod': end_date.strftime('%Y-%m'),
        'format': 'jsondata'
    }

    response = requests.get(url, params=params)
    response.raise_for_status()
    data = response.json()

    # Extract series key and observations
    series_key = list(data['dataSets'][0]['series'].keys())[0]
    series_data = data['dataSets'][0]['series'][series_key]
    observations = series_data['observations']

    # Extract dates from structure
    dates = data['structure']['dimensions']['observation'][0]['values']

    results = []
    for idx, date_info in enumerate(dates):
        date_str = date_info['id']  # e.g., '2024-06-12'
        obs_key = str(idx)
        if obs_key in observations:
            rate = observations[obs_key][0]  # rate value
            date = pd.to_datetime(date_str)
            if start_date <= date <= end_date:
                results.append({'date': date, 'value': rate})

    df = pd.DataFrame(results)
    df = df.sort_values('date').reset_index(drop=True)
    return df

def get_euro_hicp_annual_gzip(start_date, end_date):
    url = ("https://ec.europa.eu/eurostat/api/dissemination/sdmx/3.0/data/dataflow/ESTAT/prc_hicp_manr/"
           "1.0/*.*.*.*?c[freq]=M&c[unit]=RCH_A&c[coicop]=CP00&c[geo]=EA&compress=true&format=csvdata&formatVersion=1.0&lang=en&labels=label_only")
    r = requests.get(url)
    r.raise_for_status()

    with gzip.GzipFile(fileobj=io.BytesIO(r.content)) as f:
        df = pd.read_csv(f)

    euro_area = df[df['geo'].str.contains("Euro area")][['TIME_PERIOD', 'OBS_VALUE']].sort_values('TIME_PERIOD')

    # Filter by start_date and end_date (convert to datetime for filtering)
    euro_area['TIME_PERIOD'] = pd.to_datetime(euro_area['TIME_PERIOD'], format='%Y-%m')
    euro_area = euro_area[(euro_area['TIME_PERIOD'] >= pd.to_datetime(start_date)) & 
                          (euro_area['TIME_PERIOD'] <= pd.to_datetime(end_date))]

    euro_area = euro_area.rename(columns={'TIME_PERIOD': 'date', 'OBS_VALUE': 'value'})
    euro_area = euro_area.reset_index(drop=True)

    return euro_area
    
import requests
import pandas as pd
import io
import gzip

def get_euro_unemployment_gzip(start_date, end_date):
    url = (
        "https://ec.europa.eu/eurostat/api/dissemination/sdmx/3.0/data/dataflow/ESTAT/une_rt_m/1.0/"
        "*.*.*.*.*.*?"
        "c[freq]=M&c[s_adj]=SA&c[age]=TOTAL&c[unit]=PC_ACT&c[sex]=T&"
        "c[geo]=EU27_2020,EA20,BE,BG,CZ,DK,DE,EE,IE,EL,ES,FR,HR,IT,CY,LV,LT,LU,HU,MT,NL,AT,PL,PT,RO,SI,SK,FI,SE,IS,NO,CH,UK&"
        "compress=true&format=csvdata&formatVersion=1.0&lang=en&labels=label_only"
    )

    r = requests.get(url)
    r.raise_for_status()

    with gzip.GzipFile(fileobj=io.BytesIO(r.content)) as f:
        df = pd.read_csv(f)

    # We'll extract Euro Area (EA20) only for consistency
    euro_area = df[df['geo'].str.contains("Euro area")][['TIME_PERIOD', 'OBS_VALUE']].sort_values('TIME_PERIOD')

    euro_area['TIME_PERIOD'] = pd.to_datetime(euro_area['TIME_PERIOD'], format='%Y-%m')
    euro_area = euro_area[(euro_area['TIME_PERIOD'] >= pd.to_datetime(start_date)) & 
                          (euro_area['TIME_PERIOD'] <= pd.to_datetime(end_date))]

    euro_area = euro_area.rename(columns={'TIME_PERIOD': 'date', 'OBS_VALUE': 'value'})
    euro_area = euro_area.reset_index(drop=True)

    return euro_area
    
def get_gdp_quarterly_gzip(start_date, end_date):
    url = ("https://ec.europa.eu/eurostat/api/dissemination/sdmx/3.0/data/dataflow/ESTAT/namq_10_gdp/1.0/*.*.*.*.*?"
           "c[freq]=Q&c[unit]=CLV_PCH_PRE,CLV_PCH_SM,CLV_PCH_ANN&c[s_adj]=SA,SCA&c[na_item]=B1GQ&"
           "c[geo]=EU27_2020,EA20,BE,BG,CZ,DK,DE,EE,IE,EL,ES,FR,HR,IT,CY,LV,LT,LU,HU,MT,NL,AT,PL,PT,RO,SI,SK,FI,SE,IS,NO,CH,UK,BA,ME,MK,AL,RS,TR,XK&"
           "compress=true&format=csvdata&formatVersion=1.0&lang=en&labels=label_only")

    r = requests.get(url)
    r.raise_for_status()

    with gzip.GzipFile(fileobj=io.BytesIO(r.content)) as f:
        df = pd.read_csv(f)

    # Exact string for Euro area geo
    euro_area_geo = 'Euro area – 20 countries (from 2023)'

    # Unit description you want
    desired_unit = 'Chain linked volumes, percentage change on previous period'

    # Filter by geo and unit
    euro_area = df[(df['geo'] == euro_area_geo) & (df['unit'] == desired_unit)][['TIME_PERIOD', 'OBS_VALUE']].sort_values('TIME_PERIOD')

    # Convert quarters to timestamps (start of the quarter)
    euro_area['TIME_PERIOD'] = pd.PeriodIndex(euro_area['TIME_PERIOD'], freq='Q').to_timestamp()

    # Convert input dates to datetime
    start_dt = pd.to_datetime(start_date)
    end_dt = pd.to_datetime(end_date)

    # Filter by date range
    euro_area = euro_area[(euro_area['TIME_PERIOD'] >= start_dt) & (euro_area['TIME_PERIOD'] <= end_dt)]

    # Rename columns
    euro_area = euro_area.rename(columns={'TIME_PERIOD': 'date', 'OBS_VALUE': 'value'}).reset_index(drop=True)

    return euro_area

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

# -------- Streamlit App --------
st.set_page_config(layout="wide")
st.title("🌐 Global Macro Dashboard")

tab = st.sidebar.radio("Select Section", ["Home", "USA", "Japan", "UK", "EURO", "FX Rates"])

# -------- Home Tab --------
if tab == "Home":
    st.header("Welcome to the Macro Dashboard")
    st.markdown("""
    This dashboard visualizes key macroeconomic indicators for major economies.

    ✅ Data updates daily via the [FRED API](https://fred.stlouisfed.org) and [e-Stat API](https://www.e-stat.go.jp/en/)  
    ✅ Choose time ranges and chart styles  
    ✅ Built for macro-FX strategists and analysts  
    """)

# -------- USA Tab --------
if tab == "USA":
    st.header("🇺🇸 United States Macro Data")

    indicator = st.sidebar.radio("Select Indicator", [
        "Interest Rate",
        "Inflation Rate",
        "GDP Growth Rate",
        "Unemployment Rate",
        "10Y Yield",
        "2Y Yield"
    ])

    chart_type = st.selectbox("Chart Type", ["Line", "Area", "Bar"])
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Start Date", dt.date(2010, 1, 1), min_value=dt.date(1980, 1, 1), max_value=dt.date.today())
    with col2:
        end_date = st.date_input("End Date", dt.date.today(), min_value=dt.date(1980, 1, 1), max_value=dt.date.today())

    if indicator == "Interest Rate":
        st.subheader("Federal Funds Rate")
        df = get_data("FEDFUNDS", start_date, end_date)
        st.plotly_chart(plot_chart(df, "Federal Funds Rate (%)", chart_type), use_container_width=True)

    elif indicator == "Inflation Rate":
        st.subheader("CPI Inflation Rate (YoY %)")
        cpi_raw = fred.get_series('CPIAUCSL')
        df_cpi = pd.DataFrame(cpi_raw)
        df_cpi.columns = ['value']
        df_cpi.index.name = 'date'
        df_cpi = df_cpi.reset_index()
        df_cpi['YoY Inflation Rate'] = (df_cpi['value'].pct_change(periods=12) * 100).round(2)
        df_cpi = df_cpi[(df_cpi['date'] >= pd.to_datetime(start_date)) & (df_cpi['date'] <= pd.to_datetime(end_date))]
        df_cpi = df_cpi.dropna()
        fig = plot_chart(df_cpi[['date', 'YoY Inflation Rate']].rename(columns={'YoY Inflation Rate': 'value'}), "Inflation Rate (YoY %)", chart_type)
        st.plotly_chart(fig, use_container_width=True)

    elif indicator == "GDP Growth Rate":
        st.subheader("Real GDP Growth Rate (QoQ Annualized %)")
        df = get_data("A191RL1Q225SBEA", start_date, end_date)
        st.plotly_chart(plot_chart(df, "GDP Growth Rate (QoQ Annualized %)", chart_type), use_container_width=True)

    elif indicator == "Unemployment Rate":
        st.subheader("Unemployment Rate")
        df = get_data("UNRATE", start_date, end_date)
        st.plotly_chart(plot_chart(df, "Unemployment Rate (%)", chart_type), use_container_width=True)

    elif indicator == "10Y Yield":
        st.subheader("10-Year Treasury Yield")
        df = get_data("DGS10", start_date, end_date)
        st.plotly_chart(plot_chart(df, "10-Year Government Bond Yield (%)", chart_type), use_container_width=True)

    elif indicator == "2Y Yield":
        st.subheader("2-Year Treasury Yield")
        df = get_data("DGS2", start_date, end_date)
        st.plotly_chart(plot_chart(df, "2-Year Government Bond Yield (%)", chart_type), use_container_width=True)

# -------- Japan Tab --------
if tab == "Japan":
    st.header("🇯🇵 Japan Macro Data")
    indicator = st.sidebar.radio("Select Indicator", ["CPI YoY Change (%)", "Unemployment Rate", "Real GDP QoQ Growth", "Interest Rate (Short-Term)",
    "Interest Rate (Long-Term)"])
    chart_type = st.selectbox("Chart Type", ["Line", "Area", "Bar"])
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Start Date", dt.date(1980, 1, 1), min_value=dt.date(1980, 1, 1), max_value=dt.date.today())
    with col2:
        end_date = st.date_input("End Date", dt.date.today(), min_value=dt.date(1980, 1, 1), max_value=dt.date.today())

    if indicator == "CPI YoY Change (%)":
        st.subheader("Japan CPI Year-over-Year Change (All Items)")
        df = get_japan_cpi_yoy_data()
        st.plotly_chart(plot_chart(df, "CPI YoY Change (%)", chart_type), use_container_width=True)

    elif indicator == "Unemployment Rate":
        st.subheader("Japan Unemployment Rate")
        df = get_japan_unemployment_data()
        st.plotly_chart(plot_chart(df, "Unemployment Rate", chart_type), use_container_width=True)

    elif indicator == "Real GDP QoQ Growth":
        st.subheader("Japan Real GDP QoQ Growth Rate (%)")
        df = get_japan_gdp_qoq_growth()
        df.rename(columns={'gdp_qoq_growth': 'value'}, inplace=True)
        st.plotly_chart(plot_chart(df, "Real GDP QoQ Growth", chart_type), use_container_width=True)
     
    elif indicator == "Interest Rate (Short-Term)":
        st.subheader("Japan Short-Term Interest Rate (FRED: IRSTCI01JPM156N)")
        df = get_data("IRSTCI01JPM156N", start_date, end_date)
        st.plotly_chart(plot_chart(df, "Interest Rate (Short-Term)", chart_type), use_container_width=True)
        
    elif indicator == "Interest Rate (Long-Term)":
        st.subheader("Japan Long-Term Interest Rate (FRED: IRLTLT01JPM156N)")
        df = get_data("IRLTLT01JPM156N", start_date, end_date)
        st.plotly_chart(plot_chart(df, "Interest Rate (Long-Term)", chart_type), use_container_width=True)
        
# -------- UK Tab --------        
if tab == "UK":
    st.header("🇬🇧 UK Macro Data")
    indicator = st.sidebar.radio("Select Indicator", [
        "Bank of England Base Rate (%)",
        "CPI Inflation Rate (YoY %)",
    "GDP Growth Rate (QoQ %)", "Unemployment Rate", "Interest Rate (Short-Term)", "Interest Rate (Long-Term)"
    ])

    chart_type = st.selectbox("Chart Type", ["Line", "Area", "Bar"])
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Start Date", pd.to_datetime("1989-01-01"))
    with col2:
        end_date = st.date_input("End Date", pd.Timestamp.today())

    if indicator == "Bank of England Base Rate (%)":
        df = get_uk_base_rate_from_url()
        df = df.rename(columns={'Date': 'date', 'Bank Rate': 'value'})
        df = df[(df['date'] >= pd.to_datetime(start_date)) & (df['date'] <= pd.to_datetime(end_date))]
        st.plotly_chart(plot_chart(df, "Bank of England Base Rate (%)", chart_type), use_container_width=True)

    elif indicator == "CPI Inflation Rate (YoY %)":
        df = get_uk_cpi_yoy()
        df = df[(df['date'] >= pd.to_datetime(start_date)) & (df['date'] <= pd.to_datetime(end_date))]
        st.plotly_chart(plot_chart(df, "UK CPI Inflation Rate (YoY %)", chart_type), use_container_width=True)
        
    elif indicator == "GDP Growth Rate (QoQ %)":
        df = get_uk_gdp_qoq()
        df = df[(df['date'] >= pd.to_datetime(start_date)) & (df['date'] <= pd.to_datetime(end_date))]
        st.plotly_chart(plot_chart(df, "UK Real GDP QoQ Growth (%)", chart_type), use_container_width=True)

    elif indicator == "Unemployment Rate":
        df = get_uk_unemployment_rate()
        df = df[(df['date'] >= pd.to_datetime(start_date)) & (df['date'] <= pd.to_datetime(end_date))]
        st.plotly_chart(plot_chart(df, "UK Unemployment Rate (%)", chart_type), use_container_width=True)
        
    elif indicator == "Interest Rate (Short-Term)":
        st.subheader("UK Short-Term Interest Rate (FRED: IR3TIB01GBM156N)")
        df = get_data("IR3TIB01GBM156N", start_date, end_date)
        st.plotly_chart(plot_chart(df, "Interest Rate (Short-Term)", chart_type), use_container_width=True)
        
    elif indicator == "Interest Rate (Long-Term)":
        st.subheader("UK Long-Term Interest Rate (FRED: IRLTLT01GBM156N)")
        df = get_data("IRLTLT01GBM156N", start_date, end_date)
        st.plotly_chart(plot_chart(df, "Interest Rate (Long-Term)", chart_type), use_container_width=True)
        
# -------- EURO Tab --------
if tab == "EURO":
    st.header("🇪🇺 Euro Area Macro Data")
    indicator = st.sidebar.radio("Select Indicator", [
        "ECB Main Refinancing Rate",
        "HICP Annual Change (Eurostat gzip)", "Unemployment Rate (Seasonally Adjusted)", "GDP Quarterly Growth (Seasonally Adjusted)", 
        "Interest Rate (Short-Term)", "Interest Rate (Long-Term)"
    ])
    chart_type = st.selectbox("Chart Type", ["Line", "Area", "Bar"])
    c1, c2 = st.columns(2)
    with c1:
        start_date = st.date_input("Start Date", dt.date(2020, 1, 1), min_value=dt.date(2000,1,1), max_value=dt.date.today())
    with c2:
        end_date = st.date_input("End Date", dt.date.today(), min_value=dt.date(2000,1,1), max_value=dt.date.today())

    if indicator == "ECB Main Refinancing Rate":
        st.subheader("ECB Main Refinancing Rate (%)")
        df = get_ecb_refinancing_rate(start_date, end_date)
        st.plotly_chart(plot_chart(df, "ECB Refinancing Rate", chart_type), use_container_width=True)

    elif indicator == "HICP Annual Change (Eurostat gzip)":
        st.subheader("Euro Area HICP Annual Change (Eurostat gzip data)")
        df = get_euro_hicp_annual_gzip(start_date, end_date)
        if df.empty:
            st.warning("No HICP data found for this period.")
        else:
            st.plotly_chart(plot_chart(df, "Euro Area HICP Annual Change (%)", chart_type), use_container_width=True)
            
    elif indicator == "Unemployment Rate (Seasonally Adjusted)":
        st.subheader("Euro Area Unemployment Rate (Seasonally Adjusted, Eurostat gzip data)")
        df = get_euro_unemployment_gzip(start_date, end_date)
        if df.empty:
            st.warning("No unemployment data found for this period.")
        else:
            st.plotly_chart(plot_chart(df, "Euro Area Unemployment Rate (%)", chart_type), use_container_width=True)
            
    elif indicator == "GDP Quarterly Growth (Seasonally Adjusted)":
        st.subheader("Euro Area GDP Quarterly Growth (Seasonally Adjusted, Eurostat gzip data)")
        df = get_gdp_quarterly_gzip(start_date, end_date)
        if df.empty:
            st.warning("No GDP data found for this period.")
        else:
            st.plotly_chart(plot_chart(df, "GDP Quarterly Growth (%)", chart_type), use_container_width=True)
    
    elif indicator == "Interest Rate (Short-Term)":
        st.subheader("EURO Short-Term Interest Rate (FRED: IR3TIB01EZM156N)")
        df = get_data("IR3TIB01EZM156N", start_date, end_date)
        st.plotly_chart(plot_chart(df, "Interest Rate (Short-Term)", chart_type), use_container_width=True)
        
    elif indicator == "Interest Rate (Long-Term)":
        st.subheader("EURO Long-Term Interest Rate (FRED: IRLTLT01EZM156N)")
        df = get_data("IRLTLT01EZM156N", start_date, end_date)
        st.plotly_chart(plot_chart(df, "Interest Rate (Long-Term)", chart_type), use_container_width=True)
        
if tab == "FX Rates":
    st.header("FX Rates")
    indicator = st.sidebar.radio("Select Indicator", [
        "EUR/USD", "GBP/USD", "USD/JPY", "EUR/GBP", "EURJPY", "GBPJPY", "DXY"
        
    ])
    chart_type = st.selectbox("Chart Type", ["Line", "Area", "Bar"])
    c1, c2 = st.columns(2)
    with c1:
        start_date = st.date_input("Start Date", dt.date(2020, 1, 1), min_value=dt.date(2000,1,1), max_value=dt.date.today())
    with c2:
        end_date = st.date_input("End Date", dt.date.today(), min_value=dt.date(2000,1,1), max_value=dt.date.today())

    if indicator == "EUR/USD":
        st.subheader("EUR/USD Daily Exchange Rate (Close Price)")
        df = get_fx_data_yahoo("EURUSD=X", start_date, end_date)
        if df.empty:
            st.error("Could not load FX data.")
        else:
            st.plotly_chart(plot_chart(df, "EUR/USD Close Price", chart_type), use_container_width=True)
            
    elif indicator == "GBP/USD":
        st.subheader("GBP/USD Daily Exchange Rate (Close Price)")
        df = get_fx_data_yahoo("GBPUSD=X", start_date, end_date)
        if df.empty:
            st.error("Could not load FX data.")
        else:
            st.plotly_chart(plot_chart(df, "GBP/USD Close Price", chart_type), use_container_width=True)
            
    elif indicator == "USD/JPY":
        st.subheader("USD/JPY Daily Exchange Rate (Close Price)")
        df = get_fx_data_yahoo("USDJPY=X", start_date, end_date)
        if df.empty:
            st.error("Could not load FX data.")
        else:
            st.plotly_chart(plot_chart(df, "USD/JPY Close Price", chart_type), use_container_width=True)
            
    elif indicator == "DXY":
        st.subheader("DXY Daily Exchange Rate (Close Price)")
        df = get_fx_data_yahoo("DX-Y.NYB", start_date, end_date)
        if df.empty:
            st.error("Could not load FX data.")
        else:
            st.plotly_chart(plot_chart(df, "DXY Close Price", chart_type), use_container_width=True)





