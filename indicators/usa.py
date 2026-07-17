import streamlit as st

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

def get_usa_nfp_data():
    df = get_bls_series("CES0000000001", start_year=2000)
    df["value"] = df["value"].diff()
    return df.dropna().reset_index(drop=True)

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
