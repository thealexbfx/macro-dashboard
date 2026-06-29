import pandas as pd
import streamlit as st

from indicators.usa import (
    get_usa_interest_rate_data,
    get_usa_cpi_yoy_data,
    get_usa_core_cpi_yoy_data,
    get_usa_pce_yoy_data,
    get_usa_core_pce_yoy_data,
    get_usa_ppi_yoy_data,
    get_usa_core_ppi_yoy_data,
    get_usa_import_prices_yoy_data,
    get_usa_export_prices_yoy_data,
    get_usa_unemployment_rate_data,
    get_usa_labor_force_participation_data,
    get_usa_nfp_data,
    get_usa_average_hourly_earnings_yoy_data,
    get_usa_jolts_job_openings_data,
    get_usa_quits_rate_data,
    get_usa_eci_total_compensation_yoy_data,
    get_usa_eci_wages_salaries_yoy_data,
    get_usa_gdp_qoq_data,
    get_usa_personal_income_mom_data,
    get_usa_personal_consumption_mom_data,
    get_usa_saving_rate_data,
    get_usa_michigan_consumer_sentiment_data,
    get_usa_chicago_fed_nfci_data,
    get_usa_housing_starts_mom_data,
    get_usa_building_permits_mom_data,
    get_usa_new_home_sales_mom_data,
    get_usa_retail_sales_mom_data,
    get_usa_trade_balance_data,
    get_usa_industrial_production_mom_data,
    get_usa_capacity_utilization_data,
    get_usa_durable_goods_orders_mom_data,
    get_usa_labor_productivity_data,
    get_usa_unit_labor_costs_data,
    get_usa_real_hourly_compensation_data,
    get_usa_initial_jobless_claims_data,
    get_usa_fed_balance_sheet_data,
)

from indicators.uk import (
    get_uk_interest_rate_data,
    get_uk_cpi_yoy_data,
    get_uk_core_cpi_yoy_data,
    get_uk_gdp_qoq_data,
    get_uk_unemployment_rate_data,
    get_uk_retail_sales_mom_data,
    get_uk_average_weekly_earnings_yoy_data,
    get_uk_industrial_production_mom_data,
    get_uk_trade_balance_data,
    get_uk_house_prices_yoy_data,
    get_uk_vacancies_data,
)

from indicators.euro import (
    get_euro_interest_rate_data,
    get_euro_unemployment_rate_data,
    get_euro_gdp_qoq_data,
    get_euro_gdp_yoy_data,
    get_euro_hicp_yoy_data,
    get_euro_core_hicp_yoy_data,
    get_euro_retail_sales_mom_data,
    get_euro_industrial_production_mom_data,
)

from indicators.japan import (
    get_japan_interest_rate_data,
    get_japan_cpi_yoy_data,
    get_japan_core_cpi_yoy_data,
    get_japan_gdp_qoq_data,
    get_japan_unemployment_rate_data,
)


# --------- Global Analysis Functions ---------
@st.cache_data(ttl=1800)
def analyze_usa():
    """Compute latest value, slope, and relative position for all USA indicators."""
    usa_tickers = {
        # Monetary Policy
        "Federal Funds Rate": get_usa_interest_rate_data,
        "Fed Balance Sheet": get_usa_fed_balance_sheet_data,

        # Inflation
        "CPI YoY": get_usa_cpi_yoy_data,
        "Core CPI YoY": get_usa_core_cpi_yoy_data,
        "PCE YoY": get_usa_pce_yoy_data,
        "Core PCE YoY": get_usa_core_pce_yoy_data,
        "PPI YoY": get_usa_ppi_yoy_data,
        "Core PPI YoY": get_usa_core_ppi_yoy_data,
        "Import Prices YoY": get_usa_import_prices_yoy_data,
        "Export Prices YoY": get_usa_export_prices_yoy_data,

        # Labor Market
        "Unemployment Rate": get_usa_unemployment_rate_data,
        "Labor Force Participation Rate": get_usa_labor_force_participation_data,
        "Non Farm Payrolls": get_usa_nfp_data,
        "Average Hourly Earnings YoY": get_usa_average_hourly_earnings_yoy_data,
        "ECI Total Compensation YoY": get_usa_eci_total_compensation_yoy_data,
        "ECI Wages & Salaries YoY": get_usa_eci_wages_salaries_yoy_data,
        "JOLTS Job Openings": get_usa_jolts_job_openings_data,
        "Quits Rate": get_usa_quits_rate_data,
        "Initial Jobless Claims": get_usa_initial_jobless_claims_data,

        # Growth / Consumer / Activity
        "GDP Growth Rate": get_usa_gdp_qoq_data,
        "Personal Income MoM": get_usa_personal_income_mom_data,
        "Personal Consumption MoM": get_usa_personal_consumption_mom_data,
        "Retail Sales MoM": get_usa_retail_sales_mom_data,
        "Industrial Production MoM": get_usa_industrial_production_mom_data,
        "Capacity Utilization": get_usa_capacity_utilization_data,
        "Durable Goods Orders MoM": get_usa_durable_goods_orders_mom_data,
        "Trade Balance": get_usa_trade_balance_data,
        "Saving Rate": get_usa_saving_rate_data,

        # Housing
        "Housing Starts MoM": get_usa_housing_starts_mom_data,
        "Building Permits MoM": get_usa_building_permits_mom_data,
        "New Home Sales MoM": get_usa_new_home_sales_mom_data,

        # Productivity & Costs
        "Labor Productivity": get_usa_labor_productivity_data,
        "Unit Labor Costs": get_usa_unit_labor_costs_data,
        "Real Hourly Compensation": get_usa_real_hourly_compensation_data,

        # Sentiment & Conditions
        "Michigan Consumer Sentiment": get_usa_michigan_consumer_sentiment_data,
        "Chicago Fed NFCI": get_usa_chicago_fed_nfci_data,
        
        # Surveys
   ##     "ISM Manufacturing PMI": get_usa_ism_manufacturing_pmi_data,
   ##     "ISM Services PMI": get_usa_ism_services_pmi_data,
    }

    results = {}
    for name, func in usa_tickers.items():
        try:
            df = func().dropna()
            if len(df) < 12:
                continue
            df_1y = df[df["date"] >= (df["date"].max() - pd.DateOffset(years=1))]
            latest = df_1y["value"].iloc[-1]
            start = df_1y["value"].iloc[0]

            if latest > start:
                trend = "up"
            elif latest < start:
                trend = "down"
            else:
                trend = "flat"

            results[name] = {"latest": latest, "trend": trend}

        except Exception as e:
            if IS_PROD:
                st.warning(f"{name} data is temporarily unavailable.")
            else:
                st.warning(f"⚠️ Could not process {name}: {e}")
    return results

@st.cache_data(ttl=1800)
def analyze_japan():
    """Compute latest value, slope, and relative position for all japan indicators."""
    japan_tickers = {
        "Interest Rate": get_japan_interest_rate_data,
        "CPI YoY": get_japan_cpi_yoy_data,
        "GDP Growth Rate": get_japan_gdp_qoq_data,
        "Unemployment Rate": get_japan_unemployment_rate_data
    }

    results = {}
    for name, func in japan_tickers.items():
        try:
            df = func().dropna()
            if len(df) < 12:
                continue
            df_1y = df[df["date"] >= (df["date"].max() - pd.DateOffset(years=1))]
            latest = df_1y["value"].iloc[-1]
            start = df_1y["value"].iloc[0]

            if latest > start:
                trend = "up"
            elif latest < start:
                trend = "down"
            else:
                trend = "flat"

            results[name] = {"latest": latest, "trend": trend}

        except Exception as e:
            if IS_PROD:
                st.warning(f"{name} data is temporarily unavailable.")
            else:
                st.warning(f"⚠️ Could not process {name}: {e}")
    return results

@st.cache_data(ttl=1800)
def analyze_uk():
    """Compute latest value and 1-year trend for key UK indicators."""

    uk_tickers = {
        # Monetary Policy
        "Bank Rate": get_uk_interest_rate_data,

        # Inflation
        "CPI YoY": get_uk_cpi_yoy_data,
        "Core CPI YoY": get_uk_core_cpi_yoy_data,
        "House Prices YoY": get_uk_house_prices_yoy_data,

        # Growth / Activity
        "GDP QoQ": get_uk_gdp_qoq_data,
        "Retail Sales MoM": get_uk_retail_sales_mom_data,
        "Industrial Production MoM": get_uk_industrial_production_mom_data,

        # Labor Market
        "Unemployment Rate": get_uk_unemployment_rate_data,
        "Average Weekly Earnings YoY": get_uk_average_weekly_earnings_yoy_data,
        "Vacancies": get_uk_vacancies_data,

        # External Sector
        "Trade Balance": get_uk_trade_balance_data,
    }

    results = {}

    for name, func in uk_tickers.items():
        try:
            df = func().dropna()

            if len(df) < 4:
                continue

            df_1y = df[df["date"] >= (df["date"].max() - pd.DateOffset(years=1))]

            if len(df_1y) < 2:
                continue

            latest = df_1y["value"].iloc[-1]
            start = df_1y["value"].iloc[0]

            if latest > start:
                trend = "up"
            elif latest < start:
                trend = "down"
            else:
                trend = "flat"

            results[name] = {
                "latest": latest,
                "trend": trend,
            }

        except Exception as e:
            if IS_PROD:
                st.warning(f"{name} data is temporarily unavailable.")
            else:
                st.warning(f"⚠️ Could not process {name}: {e}")

    return results

@st.cache_data(ttl=1800)
def analyze_euro():
    """Compute latest value and trend for Euro Area indicators."""
    euro_tickers = {
        "Interest Rate": get_euro_interest_rate_data,
        "HICP YoY": get_euro_hicp_yoy_data,
        "Core HICP YoY": get_euro_core_hicp_yoy_data,
        "GDP QoQ": get_euro_gdp_qoq_data,
        "GDP YoY": get_euro_gdp_yoy_data,
        "Unemployment Rate": get_euro_unemployment_rate_data,
        "Retail Sales MoM": get_euro_retail_sales_mom_data,
    }

    results = {}
    for name, func in euro_tickers.items():
        try:
            df = func().dropna()
            if len(df) < 12:
                continue

            df_1y = df[df["date"] >= (df["date"].max() - pd.DateOffset(years=1))]
            latest = df_1y["value"].iloc[-1]
            start = df_1y["value"].iloc[0]

            if latest > start:
                trend = "up"
            elif latest < start:
                trend = "down"
            else:
                trend = "flat"

            results[name] = {"latest": latest, "trend": trend}

        except Exception as e:
            if IS_PROD:
                st.warning(f"{name} data is temporarily unavailable.")
            else:
                st.warning(f"⚠️ Could not process {name}: {e}")

    return results

    results = {}
    for name, func in euro_tickers.items():
        try:
            df = func().dropna()
            if len(df) < 12:
                continue
            df_1y = df[df["date"] >= (df["date"].max() - pd.DateOffset(years=1))]
            latest = df_1y["value"].iloc[-1]
            start = df_1y["value"].iloc[0]

            if latest > start:
                trend = "up"
            elif latest < start:
                trend = "down"
            else:
                trend = "flat"

            results[name] = {"latest": latest, "trend": trend}

        except Exception as e:
            if IS_PROD:
                st.warning(f"{name} data is temporarily unavailable.")
            else:
                st.warning(f"⚠️ Could not process {name}: {e}")
    return results