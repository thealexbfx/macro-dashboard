import streamlit as st
import pandas as pd

from data.local import load_usa_data
from data.fred import get_fred_series, get_usa_yield_data
from data.bls import get_bls_series
from data.bea import get_bea_nipa_series
from data.transforms import calculate_yoy_from_index, calculate_mom_pct_change, calculate_diff

def get_usa_interest_rate_data():
    return get_fred_series("DFEDTARU")

def get_usa_cpi_yoy_data():
    return calculate_yoy_from_index(
        get_bls_series("CUUR0000SA0", start_year=2000)
    )
    
def get_usa_headline_cpi_3m_annualized_data():
    """
    Return the three-month annualized change in headline CPI.

    Uses the seasonally adjusted headline CPI index so that short-term
    momentum is not distorted by normal seasonal price patterns.
    """
    df = get_bls_series(
        "CUSR0000SA0",
        start_year=2000,
    ).copy()

    df["value"] = (
        (
            df["value"]
            / df["value"].shift(3)
        ) ** 4
        - 1
    ) * 100

    return (
        df.dropna(subset=["value"])
        .reset_index(drop=True)
    )


def get_usa_food_cpi_yoy_data():
    """Return the year-over-year change in the CPI for food."""
    return calculate_yoy_from_index(
        get_bls_series(
            "CUUR0000SAF1",
            start_year=2000,
        )
    )


def get_usa_energy_cpi_yoy_data():
    """Return the year-over-year change in the CPI for energy."""
    return calculate_yoy_from_index(
        get_bls_series(
            "CUUR0000SA0E",
            start_year=2000,
        )
    )

def get_usa_core_cpi_yoy_data():
    return calculate_yoy_from_index(
        get_bls_series("CUUR0000SA0L1E", start_year=2000)
    )

def get_usa_pce_yoy_data():
    df = get_bea_nipa_series("T20804", 1, frequency="M")
    return calculate_yoy_from_index(df)

def get_usa_core_pce_yoy_data():
    df = get_bea_nipa_series("T20804", 25, frequency="M")
    return calculate_yoy_from_index(df)

def get_usa_ppi_yoy_data():
    return calculate_yoy_from_index(
        get_bls_series("WPUFD4", start_year=2000)
    )

def get_usa_core_ppi_yoy_data():
    return calculate_yoy_from_index(
        get_bls_series("WPSFD4131", start_year=2000)
    )

def get_usa_import_prices_yoy_data():
    return calculate_yoy_from_index(
        get_bls_series("EIUIR", start_year=2000)
    )

def get_usa_export_prices_yoy_data():
    return calculate_yoy_from_index(
        get_bls_series("EIUIQ", start_year=2000)
    )

def get_usa_unemployment_rate_data():
    return get_bls_series("LNS14000000", start_year=2000)

def get_usa_labor_force_participation_data():
    return get_bls_series("LNS11300000", start_year=2000)
    
def get_usa_prime_age_labor_force_participation_data():
    """Return the labor-force participation rate for ages 25 to 54."""
    return get_bls_series(
        "LNS11300060",
        start_year=2000,
    )


def get_usa_employment_population_ratio_data():
    """Return the civilian employment-population ratio."""
    return get_bls_series(
        "LNS12300000",
        start_year=2000,
    )

def get_usa_nfp_data():
    df = get_bls_series("CES0000000001", start_year=2000)
    df["value"] = df["value"].diff()
    return df.dropna().reset_index(drop=True)
    
def get_usa_nfp_3m_average_data():
    """Return the 3-month average change in nonfarm payrolls."""

    df = get_usa_nfp_data().copy()

    df["value"] = (
        df["value"]
        .rolling(window=3, min_periods=3)
        .mean()
    )

    return (
        df.dropna(subset=["value"])
        .reset_index(drop=True)
    )

def get_usa_average_hourly_earnings_yoy_data():
    return calculate_yoy_from_index(
        get_bls_series("CES0500000003", start_year=2006)
    )

def get_usa_jolts_job_openings_data():
    return get_bls_series("JTS000000000000000JOL", start_year=2000)

def get_usa_quits_rate_data():
    return get_bls_series("JTS000000000000000QUR", start_year=2000)

def get_usa_eci_total_compensation_yoy_data():
    return get_bls_series(
        "CIU2010000000000A",
        start_year=2001
    )

def get_usa_eci_wages_salaries_yoy_data():
    return get_bls_series(
        "CIU2020000000000A",
        start_year=2001
    )

def get_usa_gdp_qoq_data():
    # Real GDP percent change from preceding period
    return get_bea_nipa_series("T10101", 1, frequency="Q")

def get_usa_personal_income_mom_data():
    df = get_bea_nipa_series("T20600", 1, frequency="M")
    return calculate_mom_pct_change(df)

def get_usa_personal_consumption_mom_data():
    return get_bea_nipa_series("T20801", 1, frequency="M")

def get_usa_saving_rate_data():
    return get_bea_nipa_series("T20600", 35, frequency="M")

def get_usa_michigan_consumer_sentiment_data():
    return get_fred_series("UMCSENT")

def get_usa_chicago_fed_nfci_data():
    return get_fred_series("NFCI")

def get_usa_m2_yoy_data():
    """
    Year-over-year growth in the M2 money stock.

    FRED series:
        M2SL

    Positive values indicate expanding broad money.
    """
    return calculate_yoy_from_index(
        get_fred_series("M2SL")
    )

def get_usa_housing_starts_data():
    return get_fred_series("HOUST")


def get_usa_housing_starts_mom_data():
    return calculate_mom_pct_change(
        get_usa_housing_starts_data()
    )


def get_usa_building_permits_data():
    return get_fred_series("PERMIT")


def get_usa_building_permits_mom_data():
    return calculate_mom_pct_change(
        get_usa_building_permits_data()
    )


def get_usa_new_home_sales_data():
    return get_fred_series("HSN1F")


def get_usa_new_home_sales_mom_data():
    return calculate_mom_pct_change(
        get_usa_new_home_sales_data()
    )

def get_usa_retail_sales_mom_data():
    df = get_fred_series("RSAFS")
    return calculate_mom_pct_change(df)

def get_usa_trade_balance_data():
    return get_fred_series("BOPGSTB")

def get_usa_industrial_production_mom_data():
    df = get_fred_series("INDPRO")
    return calculate_mom_pct_change(df)

def get_usa_capacity_utilization_data():
    return get_fred_series("TCU")

def get_usa_durable_goods_orders_mom_data():
    df = get_fred_series("DGORDER")
    return calculate_mom_pct_change(df)

def get_usa_labor_productivity_data():
    df = get_bls_series("PRS85006093", start_year=2000)
    return calculate_yoy_from_index(df)

def get_usa_unit_labor_costs_data():
    df = get_bls_series("PRS85006103", start_year=2000)
    return calculate_yoy_from_index(df)

def get_usa_real_hourly_compensation_data():
    df = get_bls_series("PRS85006153", start_year=2000)
    return calculate_yoy_from_index(df)

def get_usa_initial_jobless_claims_data():
    return get_fred_series("ICSA")

def get_usa_initial_jobless_claims_4wk_average_data():
    """Return the 4-week moving average of initial jobless claims."""

    df = get_usa_initial_jobless_claims_data().copy()

    df["value"] = (
        df["value"]
        .rolling(window=4, min_periods=4)
        .mean()
    )

    return (
        df.dropna(subset=["value"])
        .reset_index(drop=True)
    )

def get_usa_ism_manufacturing_pmi_data():
    return load_usa_data("USA_ISM_Manufacturing_PMI.txt", freq="monthly")

def get_usa_ism_services_pmi_data():
    return load_usa_data("USA_ISM_Services_PMI.txt", freq="monthly")


def get_usa_fed_balance_sheet_data():
    return get_fred_series("WALCL")

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

def calculate_period_change(
    data,
    periods: int,
):
    """
    Calculate the absolute change over a specified number of observations.

    The input must contain date and value columns.
    """
    result = data[["date", "value"]].copy()
    result["value"] = result["value"].diff(periods)

    return result.dropna().reset_index(drop=True)


def get_usa_fed_total_assets_data():
    """
    Federal Reserve total assets.

    FRED series WALCL.
    Units: millions of US dollars.
    Frequency: weekly.
    """
    return get_fred_series("WALCL")


def get_usa_treasury_general_account_data():
    """
    US Treasury General Account balance held at Federal Reserve Banks.

    A rising TGA generally drains reserve liquidity from the banking system.

    FRED series WTREGEN.
    Units: millions of US dollars.
    Frequency: weekly.
    """
    return get_fred_series("WTREGEN")


def get_usa_overnight_reverse_repo_data():
    """
    Overnight reverse repurchase agreements conducted by the Federal Reserve.

    A rising reverse-repo balance generally absorbs liquidity.

    FRED series RRPONTSYD.
    Units: billions of US dollars.
    Frequency: daily.
    """
    return get_fred_series("RRPONTSYD")


def get_usa_reserve_balances_data():
    """
    Reserve balances held by depository institutions at Federal Reserve Banks.

    FRED series WRESBAL.
    Units: millions of US dollars.
    Frequency: weekly.
    """
    return get_fred_series("WRESBAL")


def get_usa_fed_total_assets_13w_change_data():
    """
    Thirteen-week change in Federal Reserve total assets.

    A positive value represents a balance-sheet liquidity injection.
    """
    return calculate_period_change(
        get_usa_fed_total_assets_data(),
        periods=13,
    )


def get_usa_reserve_balances_13w_change_data():
    """
    Thirteen-week change in reserve balances.

    A positive value represents increasing banking-system reserves.
    """
    return calculate_period_change(
        get_usa_reserve_balances_data(),
        periods=13,
    )

def get_usa_net_fed_liquidity_13w_change_data():
    """
    Thirteen-week change in the net Federal Reserve liquidity proxy.

    Positive values indicate a net liquidity injection.
    Negative values indicate a net liquidity drain.
    """
    return calculate_period_change(
        get_usa_net_fed_liquidity_data(),
        periods=13,
    )

def get_usa_net_fed_liquidity_data():
    """
    Construct a weekly proxy for net Federal Reserve liquidity.

    Net Fed Liquidity =
        Fed Total Assets
        - Treasury General Account
        - Overnight Reverse Repo

    Fed assets and the TGA are weekly Wednesday observations.
    Reverse repo is daily, so the most recently available reverse-repo
    observation on or before each weekly Fed date is used.

    All values are converted to millions of US dollars.
    """
    fed_assets = (
        get_usa_fed_total_assets_data()
        .rename(columns={"value": "fed_assets"})
        .sort_values("date")
        .reset_index(drop=True)
    )

    treasury_account = (
        get_usa_treasury_general_account_data()
        .rename(columns={"value": "tga"})
        .sort_values("date")
        .reset_index(drop=True)
    )

    reverse_repo = (
        get_usa_overnight_reverse_repo_data()
        .rename(columns={"value": "reverse_repo"})
        .sort_values("date")
        .reset_index(drop=True)
    )

    # RRPONTSYD is reported in billions; convert it to millions.
    reverse_repo["reverse_repo"] *= 1000.0

    weekly_balance_sheet = (
        fed_assets
        .merge(
            treasury_account,
            on="date",
            how="inner",
            validate="one_to_one",
        )
        .sort_values("date")
        .reset_index(drop=True)
    )

    combined = pd.merge_asof(
        weekly_balance_sheet,
        reverse_repo,
        on="date",
        direction="backward",
        tolerance=pd.Timedelta(days=7),
    )

    combined = combined.dropna(
        subset=[
            "fed_assets",
            "tga",
            "reverse_repo",
        ]
    )

    combined["value"] = (
        combined["fed_assets"]
        - combined["tga"]
        - combined["reverse_repo"]
    )

    result = (
        combined[["date", "value"]]
        .sort_values("date")
        .reset_index(drop=True)
    )

    result = result[
        result["date"] >= pd.Timestamp("2014-01-01")
    ]

    return result.reset_index(drop=True)
    
def get_usa_policy_rate_6m_change_data():
    """
    Six-month change in the upper bound of the Federal Reserve's
    target range.

    Positive values indicate policy tightening.
    Negative values indicate policy easing.
    """
    df = get_usa_interest_rate_data().copy()

    df = (
        df[["date", "value"]]
        .sort_values("date")
        .drop_duplicates(subset=["date"], keep="last")
        .reset_index(drop=True)
    )

    # Approximately six months of daily observations.
    df["value"] = df["value"].diff(126)

    return (
        df.dropna(subset=["value"])
        .reset_index(drop=True)
    )


def get_usa_real_policy_rate_data():
    """
    Construct a monthly real policy-rate proxy.

    Real Policy Rate =
        Federal Funds Target Range Upper Limit
        - Core PCE Inflation YoY

    The latest available target rate on or before each monthly core-PCE
    observation is used.
    """
    policy_rate = (
        get_usa_interest_rate_data()
        .rename(columns={"value": "policy_rate"})
        .sort_values("date")
        .drop_duplicates(subset=["date"], keep="last")
        .reset_index(drop=True)
    )

    core_pce = (
        get_usa_core_pce_yoy_data()
        .rename(columns={"value": "core_pce"})
        .sort_values("date")
        .drop_duplicates(subset=["date"], keep="last")
        .reset_index(drop=True)
    )

    combined = pd.merge_asof(
        core_pce,
        policy_rate,
        on="date",
        direction="backward",
        tolerance=pd.Timedelta(days=45),
    )

    combined = combined.dropna(
        subset=["core_pce", "policy_rate"]
    )

    combined["value"] = (
        combined["policy_rate"]
        - combined["core_pce"]
    )

    return (
        combined[["date", "value"]]
        .sort_values("date")
        .reset_index(drop=True)
    )


def get_usa_2yr_policy_gap_data():
    """
    Difference between the two-year Treasury yield and the upper bound
    of the Federal Reserve's target range.

    Negative values generally indicate that markets expect policy rates
    to be lower in the future.
    """
    two_year_yield = (
        get_usa_2yr_yield_data()
        .rename(columns={"value": "two_year_yield"})
        .sort_values("date")
        .drop_duplicates(subset=["date"], keep="last")
        .reset_index(drop=True)
    )

    policy_rate = (
        get_usa_interest_rate_data()
        .rename(columns={"value": "policy_rate"})
        .sort_values("date")
        .drop_duplicates(subset=["date"], keep="last")
        .reset_index(drop=True)
    )

    combined = pd.merge_asof(
        two_year_yield,
        policy_rate,
        on="date",
        direction="backward",
        tolerance=pd.Timedelta(days=7),
    )

    combined = combined.dropna(
        subset=["two_year_yield", "policy_rate"]
    )

    combined["value"] = (
        combined["two_year_yield"]
        - combined["policy_rate"]
    )

    return (
        combined[["date", "value"]]
        .sort_values("date")
        .reset_index(drop=True)
    )