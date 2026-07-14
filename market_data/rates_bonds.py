from data.bonds import (
    get_euro_1yr_yield_data,
    get_euro_2yr_yield_data,
    get_euro_3yr_yield_data,
    get_euro_5yr_yield_data,
    get_euro_7yr_yield_data,
    get_euro_10yr_yield_data,
    get_euro_20yr_yield_data,
    get_euro_30yr_yield_data,
    get_japan_1yr_yield_data,
    get_japan_2yr_yield_data,
    get_japan_3yr_yield_data,
    get_japan_5yr_yield_data,
    get_japan_7yr_yield_data,
    get_japan_10yr_yield_data,
    get_japan_20yr_yield_data,
    get_japan_30yr_yield_data,
    get_japan_40yr_yield_data,
    get_uk_5yr_yield_data,
    get_uk_10yr_yield_data,
    get_uk_20yr_yield_data,
    get_usa_1mo_yield_data,
    get_usa_3mo_yield_data,
    get_usa_6mo_yield_data,
    get_usa_1yr_yield_data,
    get_usa_2yr_yield_data,
    get_usa_3yr_yield_data,
    get_usa_5yr_yield_data,
    get_usa_7yr_yield_data,
    get_usa_10yr_yield_data,
    get_usa_20yr_yield_data,
    get_usa_30yr_yield_data,
)


US_DESCRIPTION = (
    "U.S. Treasury yields reflect expectations for Federal Reserve policy, "
    "inflation, economic growth, and fiscal conditions. Short maturities are "
    "more sensitive to expected policy-rate changes, while longer maturities "
    "also reflect long-term inflation, growth, and term-premium expectations."
)

UK_DESCRIPTION = (
    "UK gilt yields reflect expectations for Bank of England policy, "
    "inflation, economic growth, and government borrowing conditions. Short "
    "maturities are more sensitive to monetary-policy expectations, while "
    "longer maturities also reflect the long-term fiscal and inflation outlook."
)

JAPAN_DESCRIPTION = (
    "Japanese government bond yields reflect expectations for Bank of Japan "
    "policy, inflation, economic growth, and government borrowing conditions. "
    "Short maturities are more sensitive to policy expectations, while longer "
    "maturities reflect long-term inflation, growth, and fiscal conditions."
)

EURO_DESCRIPTION = (
    "Euro Area government bond yields reflect expectations for European "
    "Central Bank policy, inflation, economic growth, and fiscal conditions. "
    "Short maturities are more sensitive to ECB expectations, while longer "
    "maturities reflect long-term growth, inflation, term premium, and "
    "sovereign-debt conditions."
)


def bond_entry(
    data_func,
    title,
    category,
    description,
    source,
    related,
    drivers,
):
    return {
        "data_func": data_func,
        "title": title,
        "category": category,
        "description": description,
        "source": source,
        "related": related,
        "drivers": drivers,
        "unit": "percent",
    }


RATES_BONDS_MAP = {
    "US 1M": bond_entry(
        get_usa_1mo_yield_data,
        "US 1-Month Treasury Yield",
        "US Treasuries",
        US_DESCRIPTION,
        "Source: Federal Reserve Economic Data (FRED)",
        ["US 3M", "US 2Y", "Fed Funds Rate", "DXY", "S&P 500"],
        ["Federal Reserve policy", "Money-market conditions", "Inflation", "Liquidity", "Fiscal conditions"],
    ),
    "US 3M": bond_entry(
        get_usa_3mo_yield_data,
        "US 3-Month Treasury Yield",
        "US Treasuries",
        US_DESCRIPTION,
        "Source: Federal Reserve Economic Data (FRED)",
        ["US 1M", "US 6M", "US 2Y", "Fed Funds Rate", "DXY"],
        ["Federal Reserve policy", "Rate expectations", "Inflation", "Liquidity", "Treasury supply"],
    ),
    "US 6M": bond_entry(
        get_usa_6mo_yield_data,
        "US 6-Month Treasury Yield",
        "US Treasuries",
        US_DESCRIPTION,
        "Source: Federal Reserve Economic Data (FRED)",
        ["US 3M", "US 1Y", "US 2Y", "Fed Funds Rate", "DXY"],
        ["Federal Reserve policy", "Rate expectations", "Inflation", "Growth", "Treasury supply"],
    ),
    "US 1Y": bond_entry(
        get_usa_1yr_yield_data,
        "US 1-Year Treasury Yield",
        "US Treasuries",
        US_DESCRIPTION,
        "Source: Federal Reserve Economic Data (FRED)",
        ["US 6M", "US 2Y", "Fed Funds Rate", "DXY", "S&P 500"],
        ["Federal Reserve policy", "Inflation", "Growth", "Rate expectations", "Treasury supply"],
    ),
    "US 2Y": bond_entry(
        get_usa_2yr_yield_data,
        "US 2-Year Treasury Yield",
        "US Treasuries",
        US_DESCRIPTION,
        "Source: Federal Reserve Economic Data (FRED)",
        ["US 1Y", "US 5Y", "US 10Y", "Fed Funds Rate", "DXY"],
        ["Federal Reserve policy", "Rate expectations", "Inflation", "Growth", "Economic surprises"],
    ),
    "US 3Y": bond_entry(
        get_usa_3yr_yield_data,
        "US 3-Year Treasury Yield",
        "US Treasuries",
        US_DESCRIPTION,
        "Source: Federal Reserve Economic Data (FRED)",
        ["US 2Y", "US 5Y", "US 10Y", "DXY", "S&P 500"],
        ["Federal Reserve policy", "Inflation", "Growth", "Term premium", "Treasury supply"],
    ),
    "US 5Y": bond_entry(
        get_usa_5yr_yield_data,
        "US 5-Year Treasury Yield",
        "US Treasuries",
        US_DESCRIPTION,
        "Source: Federal Reserve Economic Data (FRED)",
        ["US 2Y", "US 10Y", "US 30Y", "DXY", "Gold"],
        ["Federal Reserve policy", "Inflation expectations", "Growth", "Real yields", "Term premium"],
    ),
    "US 7Y": bond_entry(
        get_usa_7yr_yield_data,
        "US 7-Year Treasury Yield",
        "US Treasuries",
        US_DESCRIPTION,
        "Source: Federal Reserve Economic Data (FRED)",
        ["US 5Y", "US 10Y", "US 30Y", "DXY", "Gold"],
        ["Inflation expectations", "Growth", "Real yields", "Term premium", "Treasury supply"],
    ),
    "US 10Y": bond_entry(
        get_usa_10yr_yield_data,
        "US 10-Year Treasury Yield",
        "US Treasuries",
        US_DESCRIPTION,
        "Source: Federal Reserve Economic Data (FRED)",
        ["US 2Y", "US 5Y", "US 30Y", "DXY", "Gold"],
        ["Inflation expectations", "Economic growth", "Real yields", "Term premium", "Treasury supply"],
    ),
    "US 20Y": bond_entry(
        get_usa_20yr_yield_data,
        "US 20-Year Treasury Yield",
        "US Treasuries",
        US_DESCRIPTION,
        "Source: Federal Reserve Economic Data (FRED)",
        ["US 10Y", "US 30Y", "DXY", "Gold", "S&P 500"],
        ["Long-term inflation", "Fiscal outlook", "Term premium", "Treasury supply", "Growth expectations"],
    ),
    "US 30Y": bond_entry(
        get_usa_30yr_yield_data,
        "US 30-Year Treasury Yield",
        "US Treasuries",
        US_DESCRIPTION,
        "Source: Federal Reserve Economic Data (FRED)",
        ["US 10Y", "US 20Y", "DXY", "Gold", "S&P 500"],
        ["Long-term inflation", "Fiscal outlook", "Term premium", "Treasury supply", "Growth expectations"],
    ),

    "UK 5Y": bond_entry(
        get_uk_5yr_yield_data,
        "UK 5-Year Gilt Yield",
        "UK Gilts",
        UK_DESCRIPTION,
        "Source: Bank of England (BOE)",
        ["UK 10Y", "GBP/USD", "FTSE 100", "US 5Y", "Euro 5Y"],
        ["Bank of England policy", "UK inflation", "UK growth", "Gilt supply", "Global yields"],
    ),
    "UK 10Y": bond_entry(
        get_uk_10yr_yield_data,
        "UK 10-Year Gilt Yield",
        "UK Gilts",
        UK_DESCRIPTION,
        "Source: Bank of England (BOE)",
        ["UK 5Y", "UK 20Y", "GBP/USD", "FTSE 100", "US 10Y"],
        ["Bank of England policy", "UK inflation", "Fiscal outlook", "Term premium", "Global yields"],
    ),
    "UK 20Y": bond_entry(
        get_uk_20yr_yield_data,
        "UK 20-Year Gilt Yield",
        "UK Gilts",
        UK_DESCRIPTION,
        "Source: Bank of England (BOE)",
        ["UK 10Y", "GBP/USD", "FTSE 100", "US 20Y", "Euro 20Y"],
        ["Long-term inflation", "Fiscal outlook", "Gilt supply", "Term premium", "Global yields"],
    ),

    "Japan 1Y": bond_entry(
        get_japan_1yr_yield_data,
        "Japan 1-Year JGB Yield",
        "Japan JGBs",
        JAPAN_DESCRIPTION,
        "Source: Japan Ministry of Finance (MOF)",
        ["Japan 2Y", "Japan 10Y", "USD/JPY", "Nikkei 225", "BOJ policy"],
        ["Bank of Japan policy", "Inflation", "Yield-curve policy", "Growth", "Liquidity"],
    ),
    "Japan 2Y": bond_entry(
        get_japan_2yr_yield_data,
        "Japan 2-Year JGB Yield",
        "Japan JGBs",
        JAPAN_DESCRIPTION,
        "Source: Japan Ministry of Finance (MOF)",
        ["Japan 1Y", "Japan 5Y", "Japan 10Y", "USD/JPY", "Nikkei 225"],
        ["Bank of Japan policy", "Inflation", "Rate expectations", "Growth", "Liquidity"],
    ),
    "Japan 3Y": bond_entry(
        get_japan_3yr_yield_data,
        "Japan 3-Year JGB Yield",
        "Japan JGBs",
        JAPAN_DESCRIPTION,
        "Source: Japan Ministry of Finance (MOF)",
        ["Japan 2Y", "Japan 5Y", "Japan 10Y", "USD/JPY", "Nikkei 225"],
        ["Bank of Japan policy", "Inflation", "Rate expectations", "Growth", "Liquidity"],
    ),
    "Japan 5Y": bond_entry(
        get_japan_5yr_yield_data,
        "Japan 5-Year JGB Yield",
        "Japan JGBs",
        JAPAN_DESCRIPTION,
        "Source: Japan Ministry of Finance (MOF)",
        ["Japan 2Y", "Japan 10Y", "USD/JPY", "Nikkei 225", "US 5Y"],
        ["Bank of Japan policy", "Inflation", "Growth", "Term premium", "Global yields"],
    ),
    "Japan 7Y": bond_entry(
        get_japan_7yr_yield_data,
        "Japan 7-Year JGB Yield",
        "Japan JGBs",
        JAPAN_DESCRIPTION,
        "Source: Japan Ministry of Finance (MOF)",
        ["Japan 5Y", "Japan 10Y", "USD/JPY", "Nikkei 225", "US 7Y"],
        ["Bank of Japan policy", "Inflation", "Growth", "Term premium", "Global yields"],
    ),
    "Japan 10Y": bond_entry(
        get_japan_10yr_yield_data,
        "Japan 10-Year JGB Yield",
        "Japan JGBs",
        JAPAN_DESCRIPTION,
        "Source: Japan Ministry of Finance (MOF)",
        ["Japan 5Y", "Japan 30Y", "USD/JPY", "Nikkei 225", "US 10Y"],
        ["Bank of Japan policy", "Inflation", "Yield-curve policy", "Term premium", "Global yields"],
    ),
    "Japan 20Y": bond_entry(
        get_japan_20yr_yield_data,
        "Japan 20-Year JGB Yield",
        "Japan JGBs",
        JAPAN_DESCRIPTION,
        "Source: Japan Ministry of Finance (MOF)",
        ["Japan 10Y", "Japan 30Y", "USD/JPY", "Nikkei 225", "US 20Y"],
        ["Long-term inflation", "Fiscal outlook", "JGB supply", "Term premium", "Global yields"],
    ),
    "Japan 30Y": bond_entry(
        get_japan_30yr_yield_data,
        "Japan 30-Year JGB Yield",
        "Japan JGBs",
        JAPAN_DESCRIPTION,
        "Source: Japan Ministry of Finance (MOF)",
        ["Japan 10Y", "Japan 20Y", "Japan 40Y", "USD/JPY", "US 30Y"],
        ["Long-term inflation", "Fiscal outlook", "JGB supply", "Term premium", "Global yields"],
    ),
    "Japan 40Y": bond_entry(
        get_japan_40yr_yield_data,
        "Japan 40-Year JGB Yield",
        "Japan JGBs",
        JAPAN_DESCRIPTION,
        "Source: Japan Ministry of Finance (MOF)",
        ["Japan 20Y", "Japan 30Y", "USD/JPY", "Nikkei 225", "US 30Y"],
        ["Long-term inflation", "Fiscal sustainability", "JGB supply", "Term premium", "Global yields"],
    ),

    "Euro 1Y": bond_entry(
        get_euro_1yr_yield_data,
        "Euro Area 1-Year AAA Yield",
        "Euro Area Bonds",
        EURO_DESCRIPTION,
        "Source: European Central Bank (ECB)",
        ["Euro 2Y", "Euro 10Y", "EUR/USD", "DAX", "ECB policy"],
        ["ECB policy", "Inflation", "Rate expectations", "Growth", "Liquidity"],
    ),
    "Euro 2Y": bond_entry(
        get_euro_2yr_yield_data,
        "Euro Area 2-Year AAA Yield",
        "Euro Area Bonds",
        EURO_DESCRIPTION,
        "Source: European Central Bank (ECB)",
        ["Euro 1Y", "Euro 5Y", "Euro 10Y", "EUR/USD", "DAX"],
        ["ECB policy", "Inflation", "Rate expectations", "Growth", "Liquidity"],
    ),
    "Euro 3Y": bond_entry(
        get_euro_3yr_yield_data,
        "Euro Area 3-Year AAA Yield",
        "Euro Area Bonds",
        EURO_DESCRIPTION,
        "Source: European Central Bank (ECB)",
        ["Euro 2Y", "Euro 5Y", "Euro 10Y", "EUR/USD", "DAX"],
        ["ECB policy", "Inflation", "Growth", "Term premium", "Liquidity"],
    ),
    "Euro 5Y": bond_entry(
        get_euro_5yr_yield_data,
        "Euro Area 5-Year AAA Yield",
        "Euro Area Bonds",
        EURO_DESCRIPTION,
        "Source: European Central Bank (ECB)",
        ["Euro 2Y", "Euro 10Y", "EUR/USD", "DAX", "US 5Y"],
        ["ECB policy", "Inflation expectations", "Growth", "Term premium", "Global yields"],
    ),
    "Euro 7Y": bond_entry(
        get_euro_7yr_yield_data,
        "Euro Area 7-Year AAA Yield",
        "Euro Area Bonds",
        EURO_DESCRIPTION,
        "Source: European Central Bank (ECB)",
        ["Euro 5Y", "Euro 10Y", "EUR/USD", "DAX", "US 7Y"],
        ["ECB policy", "Inflation expectations", "Growth", "Term premium", "Global yields"],
    ),
    "Euro 10Y": bond_entry(
        get_euro_10yr_yield_data,
        "Euro Area 10-Year AAA Yield",
        "Euro Area Bonds",
        EURO_DESCRIPTION,
        "Source: European Central Bank (ECB)",
        ["Euro 5Y", "Euro 30Y", "EUR/USD", "DAX", "US 10Y"],
        ["ECB policy", "Inflation expectations", "Growth", "Term premium", "Sovereign risk"],
    ),
    "Euro 20Y": bond_entry(
        get_euro_20yr_yield_data,
        "Euro Area 20-Year AAA Yield",
        "Euro Area Bonds",
        EURO_DESCRIPTION,
        "Source: European Central Bank (ECB)",
        ["Euro 10Y", "Euro 30Y", "EUR/USD", "DAX", "US 20Y"],
        ["Long-term inflation", "Fiscal conditions", "Term premium", "Sovereign risk", "Global yields"],
    ),
    "Euro 30Y": bond_entry(
        get_euro_30yr_yield_data,
        "Euro Area 30-Year AAA Yield",
        "Euro Area Bonds",
        EURO_DESCRIPTION,
        "Source: European Central Bank (ECB)",
        ["Euro 10Y", "Euro 20Y", "EUR/USD", "DAX", "US 30Y"],
        ["Long-term inflation", "Fiscal conditions", "Term premium", "Sovereign risk", "Global yields"],
    ),
}


RATES_BONDS_CATEGORY_MAP = {
    "US Treasuries": [
        "US 1M",
        "US 3M",
        "US 6M",
        "US 1Y",
        "US 2Y",
        "US 3Y",
        "US 5Y",
        "US 7Y",
        "US 10Y",
        "US 20Y",
        "US 30Y",
    ],
    "UK Gilts": [
        "UK 5Y",
        "UK 10Y",
        "UK 20Y",
    ],
    "Japan JGBs": [
        "Japan 1Y",
        "Japan 2Y",
        "Japan 3Y",
        "Japan 5Y",
        "Japan 7Y",
        "Japan 10Y",
        "Japan 20Y",
        "Japan 30Y",
        "Japan 40Y",
    ],
    "Euro Area Bonds": [
        "Euro 1Y",
        "Euro 2Y",
        "Euro 3Y",
        "Euro 5Y",
        "Euro 7Y",
        "Euro 10Y",
        "Euro 20Y",
        "Euro 30Y",
    ],
}


RATES_BONDS_COMPARE_MAP = {
    "Compare +": None,
    **{
        name: config["data_func"]
        for name, config in RATES_BONDS_MAP.items()
    },
}