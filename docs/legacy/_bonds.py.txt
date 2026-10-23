[1mdiff --git a/market_data/rates_bonds.py b/market_data/rates_bonds.py[m
[1mindex d38ae22..1c19e71 100644[m
[1m--- a/market_data/rates_bonds.py[m
[1m+++ b/market_data/rates_bonds.py[m
[36m@@ -1,5 +1,422 @@[m
[31m-RATES_BONDS_MAP = {}[m
[32m+[m[32mfrom data.bonds import ([m
[32m+[m[32m    get_euro_1yr_yield_data,[m
[32m+[m[32m    get_euro_2yr_yield_data,[m
[32m+[m[32m    get_euro_3yr_yield_data,[m
[32m+[m[32m    get_euro_5yr_yield_data,[m
[32m+[m[32m    get_euro_7yr_yield_data,[m
[32m+[m[32m    get_euro_10yr_yield_data,[m
[32m+[m[32m    get_euro_20yr_yield_data,[m
[32m+[m[32m    get_euro_30yr_yield_data,[m
[32m+[m[32m    get_japan_1yr_yield_data,[m
[32m+[m[32m    get_japan_2yr_yield_data,[m
[32m+[m[32m    get_japan_3yr_yield_data,[m
[32m+[m[32m    get_japan_5yr_yield_data,[m
[32m+[m[32m    get_japan_7yr_yield_data,[m
[32m+[m[32m    get_japan_10yr_yield_data,[m
[32m+[m[32m    get_japan_20yr_yield_data,[m
[32m+[m[32m    get_japan_30yr_yield_data,[m
[32m+[m[32m    get_japan_40yr_yield_data,[m
[32m+[m[32m    get_uk_5yr_yield_data,[m
[32m+[m[32m    get_uk_10yr_yield_data,[m
[32m+[m[32m    get_uk_20yr_yield_data,[m
[32m+[m[32m    get_usa_1mo_yield_data,[m
[32m+[m[32m    get_usa_3mo_yield_data,[m
[32m+[m[32m    get_usa_6mo_yield_data,[m
[32m+[m[32m    get_usa_1yr_yield_data,[m
[32m+[m[32m    get_usa_2yr_yield_data,[m
[32m+[m[32m    get_usa_3yr_yield_data,[m
[32m+[m[32m    get_usa_5yr_yield_data,[m
[32m+[m[32m    get_usa_7yr_yield_data,[m
[32m+[m[32m    get_usa_10yr_yield_data,[m
[32m+[m[32m    get_usa_20yr_yield_data,[m
[32m+[m[32m    get_usa_30yr_yield_data,[m
[32m+[m[32m)[m
 [m
[31m-RATES_BONDS_CATEGORY_MAP = {}[m
 [m
[31m-RATES_BONDS_COMPARE_MAP = {}[m
\ No newline at end of file[m
[32m+[m[32mUS_DESCRIPTION = ([m
[32m+[m[32m    "U.S. Treasury yields reflect expectations for Federal Reserve policy, "[m
[32m+[m[32m    "inflation, economic growth, and fiscal conditions. Short maturities are "[m
[32m+[m[32m    "more sensitive to expected policy-rate changes, while longer maturities "[m
[32m+[m[32m    "also reflect long-term inflation, growth, and term-premium expectations."[m
[32m+[m[32m)[m
[32m+[m
[32m+[m[32mUK_DESCRIPTION = ([m
[32m+[m[32m    "UK gilt yields reflect expectations for Bank of England policy, "[m
[32m+[m[32m    "inflation, economic growth, and government borrowing conditions. Short "[m
[32m+[m[32m    "maturities are more sensitive to monetary-policy expectations, while "[m
[32m+[m[32m    "longer maturities also reflect the long-term fiscal and inflation outlook."[m
[32m+[m[32m)[m
[32m+[m
[32m+[m[32mJAPAN_DESCRIPTION = ([m
[32m+[m[32m    "Japanese government bond yields reflect expectations for Bank of Japan "[m
[32m+[m[32m    "policy, inflation, economic growth, and government borrowing conditions. "[m
[32m+[m[32m    "Short maturities are more sensitive to policy expectations, while longer "[m
[32m+[m[32m    "maturities reflect long-term inflation, growth, and fiscal conditions."[m
[32m+[m[32m)[m
[32m+[m
[32m+[m[32mEURO_DESCRIPTION = ([m
[32m+[m[32m    "Euro Area government bond yields reflect expectations for European "[m
[32m+[m[32m    "Central Bank policy, inflation, economic growth, and fiscal conditions. "[m
[32m+[m[32m    "Short maturities are more sensitive to ECB expectations, while longer "[m
[32m+[m[32m    "maturities reflect long-term growth, inflation, term premium, and "[m
[32m+[m[32m    "sovereign-debt conditions."[m
[32m+[m[32m)[m
[32m+[m
[32m+[m
[32m+[m[32mdef bond_entry([m
[32m+[m[32m    data_func,[m
[32m+[m[32m    title,[m
[32m+[m[32m    category,[m
[32m+[m[32m    description,[m
[32m+[m[32m    source,[m
[32m+[m[32m    related,[m
[32m+[m[32m    drivers,[m
[32m+[m[32m):[m
[32m+[m[32m    return {[m
[32m+[m[32m        "data_func": data_func,[m
[32m+[m[32m        "title": title,[m
[32m+[m[32m        "category": category,[m
[32m+[m[32m        "description": description,[m
[32m+[m[32m        "source": source,[m
[32m+[m[32m        "related": related,[m
[32m+[m[32m        "drivers": drivers,[m
[32m+[m[32m        "unit": "percent",[m
[32m+[m[32m    }[m
[32m+[m
[32m+[m
[32m+[m[32mRATES_BONDS_MAP = {[m
[32m+[m[32m    "US 1M": bond_entry([m
[32m+[m[32m        get_usa_1mo_yield_data,[m
[32m+[m[32m        "US 1-Month Treasury Yield",[m
[32m+[m[32m        "US Treasuries",[m
[32m+[m[32m        US_DESCRIPTION,[m
[32m+[m[32m        "Source: Federal Reserve Economic Data (FRED)",[m
[32m+[m[32m        ["US 3M", "US 2Y", "Fed Funds Rate", "DXY", "S&P 500"],[m
[32m+[m[32m        ["Federal Reserve policy", "Money-market conditions", "Inflation", "Liquidity", "Fiscal conditions"],[m
[32m+[m[32m    ),[m
[32m+[m[32m    "US 3M": bond_entry([m
[32m+[m[32m        get_usa_3mo_yield_data,[m
[32m+[m[32m        "US 3-Month Treasury Yield",[m
[32m+[m[32m        "US Treasuries",[m
[32m+[m[32m        US_DESCRIPTION,[m
[32m+[m[32m        "Source: Federal Reserve Economic Data (FRED)",[m
[32m+[m[32m        ["US 1M", "US 6M", "US 2Y", "Fed Funds Rate", "DXY"],[m
[32m+[m[32m        ["Federal Reserve policy", "Rate expectations", "Inflation", "Liquidity", "Treasury supply"],[m
[32m+[m[32m    ),[m
[32m+[m[32m    "US 6M": bond_entry([m
[32m+[m[32m        get_usa_6mo_yield_data,[m
[32m+[m[32m        "US 6-Month Treasury Yield",[m
[32m+[m[32m        "US Treasuries",[m
[32m+[m[32m        US_DESCRIPTION,[m
[32m+[m[32m        "Source: Federal Reserve Economic Data (FRED)",[m
[32m+[m[32m        ["US 3M", "US 1Y", "US 2Y", "Fed Funds Rate", "DXY"],[m
[32m+[m[32m        ["Federal Reserve policy", "Rate expectations", "Inflation", "Growth", "Treasury supply"],[m
[32m+[m[32m    ),[m
[32m+[m[32m    "US 1Y": bond_entry([m
[32m+[m[32m        get_usa_1yr_yield_data,[m
[32m+[m[32m        "US 1-Year Treasury Yield",[m
[32m+[m[32m        "US Treasuries",[m
[32m+[m[32m        US_DESCRIPTION,[m
[32m+[m[32m        "Source: Federal Reserve Economic Data (FRED)",[m
[32m+[m[32m        ["US 6M", "US 2Y", "Fed Funds Rate", "DXY", "S&P 500"],[m
[32m+[m[32m        ["Federal Reserve policy", "Inflation", "Growth", "Rate expectations", "Treasury supply"],[m
[32m+[m[32m    ),[m
[32m+[m[32m    "US 2Y": bond_entry([m
[32m+[m[32m        get_usa_2yr_yield_data,[m
[32m+[m[32m        "US 2-Year Treasury Yield",[m
[32m+[m[32m        "US Treasuries",[m
[32m+[m[32m        US_DESCRIPTION,[m
[32m+[m[32m        "Source: Federal Reserve Economic Data (FRED)",[m
[32m+[m[32m        ["US 1Y", "US 5Y", "US 10Y", "Fed Funds Rate", "DXY"],[m
[32m+[m[32m        ["Federal Reserve policy", "Rate expectations", "Inflation", "Growth", "Economic surprises"],[m
[32m+[m[32m    ),[m
[32m+[m[32m    "US 3Y": bond_entry([m
[32m+[m[32m        get_usa_3yr_yield_data,[m
[32m+[m[32m        "US 3-Year Treasury Yield",[m
[32m+[m[32m        "US Treasuries",[m
[32m+[m[32m        US_DESCRIPTION,[m
[32m+[m[32m        "Source: Federal Reserve Economic Data (FRED)",[m
[32m+[m[32m        ["US 2Y", "US 5Y", "US 10Y", "DXY", "S&P 500"],[m
[32m+[m[32m        ["Federal Reserve policy", "Inflation", "Growth", "Term premium", "Treasury supply"],[m
[32m+[m[32m    ),[m
[32m+[m[32m    "US 5Y": bond_entry([m
[32m+[m[32m        get_usa_5yr_yield_data,[m
[32m+[m[32m        "US 5-Year Treasury Yield",[m
[32m+[m[32m        "US Treasuries",[m
[32m+[m[32m        US_DESCRIPTION,[m
[32m+[m[32m        "Source: Federal Reserve Economic Data (FRED)",[m
[32m+[m[32m        ["US 2Y", "US 10Y", "US 30Y", "DXY", "Gold"],[m
[32m+[m[32m        ["Federal Reserve policy", "Inflation expectations", "Growth", "Real yields", "Term premium"],[m
[32m+[m[32m    ),[m
[32m+[m[32m    "US 7Y": bond_entry([m
[32m+[m[32m        get_usa_7yr_yield_data,[m
[32m+[m[32m        "US 7-Year Treasury Yield",[m
[32m+[m[32m        "US Treasuries",[m
[32m+[m[32m        US_DESCRIPTION,[m
[32m+[m[32m        "Source: Federal Reserve Economic Data (FRED)",[m
[32m+[m[32m        ["US 5Y", "US 10Y", "US 30Y", "DXY", "Gold"],[m
[32m+[m[32m        ["Inflation expectations", "Growth", "Real yields", "Term premium", "Treasury supply"],[m
[32m+[m[32m    ),[m
[32m+[m[32m    "US 10Y": bond_entry([m
[32m+[m[32m        get_usa_10yr_yield_data,[m
[32m+[m[32m        "US 10-Year Treasury Yield",[m
[32m+[m[32m        "US Treasuries",[m
[32m+[m[32m        US_DESCRIPTION,[m
[32m+[m[32m        "Source: Federal Reserve Economic Data (FRED)",[m
[32m+[m[32m        ["US 2Y", "US 5Y", "US 30Y", "DXY", "Gold"],[m
[32m+[m[32m        ["Inflation expectations", "Economic growth", "Real yields", "Term premium", "Treasury supply"],[m
[32m+[m[32m    ),[m
[32m+[m[32m    "US 20Y": bond_entry([m
[32m+[m[32m        get_usa_20yr_yield_data,[m
[32m+[m[32m        "US 20-Year Treasury Yield",[m
[32m+[m[32m        "US Treasuries",[m
[32m+[m[32m        US_DESCRIPTION,[m
[32m+[m[32m        "Source: Federal Reserve Economic Data (FRED)",[m
[32m+[m[32m        ["US 10Y", "US 30Y", "DXY", "Gold", "S&P 500"],[m
[32m+[m[32m        ["Long-term inflation", "Fiscal outlook", "Term premium", "Treasury supply", "Growth expectations"],[m
[32m+[m[32m    ),[m
[32m+[m[32m    "US 30Y": bond_entry([m
[32m+[m[32m        get_usa_30yr_yield_data,[m
[32m+[m[32m        "US 30-Year Treasury Yield",[m
[32m+[m[32m        "US Treasuries",[m
[32m+[m[32m        US_DESCRIPTION,[m
[32m+[m[32m        "Source: Federal Reserve Economic Data (FRED)",[m
[32m+[m[32m        ["US 10Y", "US 20Y", "DXY", "Gold", "S&P 500"],[m
[32m+[m[32m        ["Long-term inflation", "Fiscal outlook", "Term premium", "Treasury supply", "Growth expectations"],[m
[32m+[m[32m    ),[m
[32m+[m
[32m+[m[32m    "UK 5Y": bond_entry([m
[32m+[m[32m        get_uk_5yr_yield_data,[m
[32m+[m[32m        "UK 5-Year Gilt Yield",[m
[32m+[m[32m        "UK Gilts",[m
[32m+[m[32m        UK_DESCRIPTION,[m
[32m+[m[32m        "Source: Bank of England (BOE)",[m
[32m+[m[32m        ["UK 10Y", "GBP/USD", "FTSE 100", "US 5Y", "Euro 5Y"],[m
[32m+[m[32m        ["Bank of England policy", "UK inflation", "UK growth", "Gilt supply", "Global yields"],[m
[32m+[m[32m    ),[m
[32m+[m[32m    "UK 10Y": bond_entry([m
[32m+[m[32m        get_uk_10yr_yield_data,[m
[32m+[m[32m        "UK 10-Year Gilt Yield",[m
[32m+[m[32m        "UK Gilts",[m
[32m+[m[32m        UK_DESCRIPTION,[m
[32m+[m[32m        "Source: Bank of England (BOE)",[m
[32m+[m[32m        ["UK 5Y", "UK 20Y", "GBP/USD", "FTSE 100", "US 10Y"],[m
[32m+[m[32m        ["Bank of England policy", "UK inflation", "Fiscal outlook", "Term premium", "Global yields"],[m
[32m+[m[32m    ),[m
[32m+[m[32m    "UK 20Y": bond_entry([m
[32m+[m[32m        get_uk_20yr_yield_data,[m
[32m+[m[32m        "UK 20-Year Gilt Yield",[m
[32m+[m[32m        "UK Gilts",[m
[32m+[m[32m        UK_DESCRIPTION,[m
[32m+[m[32m        "Source: Bank of England (BOE)",[m
[32m+[m[32m        ["UK 10Y", "GBP/USD", "FTSE 100", "US 20Y", "Euro 20Y"],[m
[32m+[m[32m        ["Long-term inflation", "Fiscal outlook", "Gilt supply", "Term premium", "Global yields"],[m
[32m+[m[32m    ),[m
[32m+[m
[32m+[m[32m    "Japan 1Y": bond_entry([m
[32m+[m[32m        get_japan_1yr_yield_data,[m
[32m+[m[32m        "Japan 1-Year JGB Yield",[m
[32m+[m[32m        "Japan JGBs",[m
[32m+[m[32m        JAPAN_DESCRIPTION,[m
[32m+[m[32m        "Source: Japan Ministry of Finance (MOF)",[m
[32m+[m[32m        ["Japan 2Y", "Japan 10Y", "USD/JPY", "Nikkei 225", "BOJ policy"],[m
[32m+[m[32m        ["Bank of Japan policy", "Inflation", "Yield-curve policy", "Growth", "Liquidity"],[m
[32m+[m[32m    ),[m
[32m+[m[32m    "Japan 2Y": bond_entry([m
[32m+[m[32m        get_japan_2yr_yield_data,[m
[32m+[m[32m        "Japan 2-Year JGB Yield",[m
[32m+[m[32m        "Japan JGBs",[m
[32m+[m[32m        JAPAN_DESCRIPTION,[m
[32m+[m[32m        "Source: Japan Ministry of Finance (MOF)",[m
[32m+[m[32m        ["Japan 1Y", "Japan 5Y", "Japan 10Y", "USD/JPY", "Nikkei 225"],[m
[32m+[m[32m        ["Bank of Japan policy", "Inflation", "Rate expectations", "Growth", "Liquidity"],[m
[32m+[m[32m    ),[m
[32m+[m[32m    "Japan 3Y": bond_entry([m
[32m+[m[32m        get_japan_3yr_yield_data,[m
[32m+[m[32m        "Japan 3-Year JGB Yield",[m
[32m+[m[32m        "Japan JGBs",[m
[32m+[m[32m        JAPAN_DESCRIPTION,[m
[32m+[m[32m        "Source: Japan Ministry of Finance (MOF)",[m
[32m+[m[32m        ["Japan 2Y", "Japan 5Y", "Japan 10Y", "USD/JPY", "Nikkei 225"],[m
[32m+[m[32m        ["Bank of Japan policy", "Inflation", "Rate expectations", "Growth", "Liquidity"],[m
[32m+[m[32m    ),[m
[32m+[m[32m    "Japan 5Y": bond_entry([m
[32m+[m[32m        get_japan_5yr_yield_data,[m
[32m+[m[32m        "Japan 5-Year JGB Yield",[m
[32m+[m[32m        "Japan JGBs",[m
[32m+[m[32m        JAPAN_DESCRIPTION,[m
[32m+[m[32m        "Source: Japan Ministry of Finance (MOF)",[m
[32m+[m[32m        ["Japan 2Y", "Japan 10Y", "USD/JPY", "Nikkei 225", "US 5Y"],[m
[32m+[m[32m        ["Bank of Japan policy", "Inflation", "Growth", "Term premium", "Global yields"],[m
[32m+[m[32m    ),[m
[32m+[m[32m    "Japan 7Y": bond_entry([m
[32m+[m[32m        get_japan_7yr_yield_data,[m
[32m+[m[32m        "Japan 7-Year JGB Yield",[m
[32m+[m[32m        "Japan JGBs",[m
[32m+[m[32m        JAPAN_DESCRIPTION,[m
[32m+[m[32m        "Source: Japan Ministry of Finance (MOF)",[m
[32m+[m[32m        ["Japan 5Y", "Japan 10Y", "USD/JPY", "Nikkei 225", "US 7Y"],[m
[32m+[m[32m        ["Bank of Japan policy", "Inflation", "Growth", "Term premium", "Global yields"],[m
[32m+[m[32m    ),[m
[32m+[m[32m    "Japan 10Y": bond_entry([m
[32m+[m[32m        get_japan_10yr_yield_data,[m
[32m+[m[32m        "Japan 10-Year JGB Yield",[m
[32m+[m[32m        "Japan JGBs",[m
[32m+[m[32m        JAPAN_DESCRIPTION,[m
[32m+[m[32m        "Source: Japan Ministry of Finance (MOF)",[m
[32m+[m[32m        ["Japan 5Y", "Japan 30Y", "USD/JPY", "Nikkei 225", "US 10Y"],[m
[32m+[m[32m        ["Bank of Japan policy", "Inflation", "Yield-curve policy", "Term premium", "Global yields"],[m
[32m+[m[32m    ),[m
[32m+[m[32m    "Japan 20Y": bond_entry([m
[32m+[m[32m        get_japan_20yr_yield_data,[m
[32m+[m[32m        "Japan 20-Year JGB Yield",[m
[32m+[m[32m        "Japan JGBs",[m
[32m+[m[32m        JAPAN_DESCRIPTION,[m
[32m+[m[32m        "Source: Japan Ministry of Finance (MOF)",[m
[32m+[m[32m        ["Japan 10Y", "Japan 30Y", "USD/JPY", "Nikkei 225", "US 20Y"],[m
[32m+[m[32m        ["Long-term inflation", "Fiscal outlook", "JGB supply", "Term premium", "Global yields"],[m
[32m+[m[32m    ),[m
[32m+[m[32m    "Japan 30Y": bond_entry([m
[32m+[m[32m        get_japan_30yr_yield_data,[m
[32m+[m[32m        "Japan 30-Year JGB Yield",[m
[32m+[m[32m        "Japan JGBs",[m
[32m+[m[32m        JAPAN_DESCRIPTION,[m
[32m+[m[32m        "Source: Japan Ministry of Finance (MOF)",[m
[32m+[m[32m        ["Japan 10Y", "Japan 20Y", "Japan 40Y", "USD/JPY", "US 30Y"],[m
[32m+[m[32m        ["Long-term inflation", "Fiscal outlook", "JGB supply", "Term premium", "Global yields"],[m
[32m+[m[32m    ),[m
[32m+[m[32m    "Japan 40Y": bond_entry([m
[32m+[m[32m        get_japan_40yr_yield_data,[m
[32m+[m[32m        "Japan 40-Year JGB Yield",[m
[32m+[m[32m        "Japan JGBs",[m
[32m+[m[32m        JAPAN_DESCRIPTION,[m
[32m+[m[32m        "Source: Japan Ministry of Finance (MOF)",[m
[32m+[m[32m        ["Japan 20Y", "Japan 30Y", "USD/JPY", "Nikkei 225", "US 30Y"],[m
[32m+[m[32m        ["Long-term inflation", "Fiscal sustainability", "JGB supply", "Term premium", "Global yields"],[m
[32m+[m[32m    ),[m
[32m+[m
[32m+[m[32m    "Euro 1Y": bond_entry([m
[32m+[m[32m        get_euro_1yr_yield_data,[m
[32m+[m[32m        "Euro Area 1-Year AAA Yield",[m
[32m+[m[32m        "Euro Area Bonds",[m
[32m+[m[32m        EURO_DESCRIPTION,[m
[32m+[m[32m        "Source: European Central Bank (ECB)",[m
[32m+[m[32m        ["Euro 2Y", "Euro 10Y", "EUR/USD", "DAX", "ECB policy"],[m
[32m+[m[32m        ["ECB policy", "Inflation", "Rate expectations", "Growth", "Liquidity"],[m
[32m+[m[32m    ),[m
[32m+[m[32m    "Euro 2Y": bond_entry([m
[32m+[m[32m        get_euro_2yr_yield_data,[m
[32m+[m[32m        "Euro Area 2-Year AAA Yield",[m
[32m+[m[32m        "Euro Area Bonds",[m
[32m+[m[32m        EURO_DESCRIPTION,[m
[32m+[m[32m        "Source: European Central Bank (ECB)",[m
[32m+[m[32m        ["Euro 1Y", "Euro 5Y", "Euro 10Y", "EUR/USD", "DAX"],[m
[32m+[m[32m        ["ECB policy", "Inflation", "Rate expectations", "Growth", "Liquidity"],[m
[32m+[m[32m    ),[m
[32m+[m[32m    "Euro 3Y": bond_entry([m
[32m+[m[32m        get_euro_3yr_yield_data,[m
[32m+[m[32m        "Euro Area 3-Year AAA Yield",[m
[32m+[m[32m        "Euro Area Bonds",[m
[32m+[m[32m        EURO_DESCRIPTION,[m
[32m+[m[32m        "Source: European Central Bank (ECB)",[m
[32m+[m[32m        ["Euro 2Y", "Euro 5Y", "Euro 10Y", "EUR/USD", "DAX"],[m
[32m+[m[32m        ["ECB policy", "Inflation", "Growth", "Term premium", "Liquidity"],[m
[32m+[m[32m    ),[m
[32m+[m[32m    "Euro 5Y": bond_entry([m
[32m+[m[32m        get_euro_5yr_yield_data,[m
[32m+[m[32m        "Euro Area 5-Year AAA Yield",[m
[32m+[m[32m        "Euro Area Bonds",[m
[32m+[m[32m        EURO_DESCRIPTION,[m
[32m+[m[32m        "Source: European Central Bank (ECB)",[m
[32m+[m[32m        ["Euro 2Y", "Euro 10Y", "EUR/USD", "DAX", "US 5Y"],[m
[32m+[m[32m        ["ECB policy", "Inflation expectations", "Growth", "Term premium", "Global yields"],[m
[32m+[m[32m    ),[m
[32m+[m[32m    "Euro 7Y": bond_entry([m
[32m+[m[32m        get_euro_7yr_yield_data,[m
[32m+[m[32m        "Euro Area 7-Year AAA Yield",[m
[32m+[m[32m        "Euro Area Bonds",[m
[32m+[m[32m        EURO_DESCRIPTION,[m
[32m+[m[32m        "Source: European Central Bank (ECB)",[m
[32m+[m[32m        ["Euro 5Y", "Euro 10Y", "EUR/USD", "DAX", "US 7Y"],[m
[32m+[m[32m        ["ECB policy", "Inflation expectations", "Growth", "Term premium", "Global yields"],[m
[32m+[m[32m    ),[m
[32m+[m[32m    "Euro 10Y": bond_entry([m
[32m+[m[32m        get_euro_10yr_yield_data,[m
[32m+[m[32m        "Euro Area 10-Year AAA Yield",[m
[32m+[m[32m        "Euro Area Bonds",[m
[32m+[m[32m        EURO_DESCRIPTION,[m
[32m+[m[32m        "Source: European Central Bank (ECB)",[m
[32m+[m[32m        ["Euro 5Y", "Euro 30Y", "EUR/USD", "DAX", "US 10Y"],[m
[32m+[m[32m        ["ECB policy", "Inflation expectations", "Growth", "Term premium", "Sovereign risk"],[m
[32m+[m[32m    ),[m
[32m+[m[32m    "Euro 20Y": bond_entry([m
[32m+[m[32m        get_euro_20yr_yield_data,[m
[32m+[m[32m        "Euro Area 20-Year AAA Yield",[m
[32m+[m[32m        "Euro Area Bonds",[m
[32m+[m[32m        EURO_DESCRIPTION,[m
[32m+[m[32m        "Source: European Central Bank (ECB)",[m
[32m+[m[32m        ["Euro 10Y", "Euro 30Y", "EUR/USD", "DAX", "US 20Y"],[m
[32m+[m[32m        ["Long-term inflation", "Fiscal conditions", "Term premium", "Sovereign risk", "Global yields"],[m
[32m+[m[32m    ),[m
[32m+[m[32m    "Euro 30Y": bond_entry([m
[32m+[m[32m        get_euro_30yr_yield_data,[m
[32m+[m[32m        "Euro Area 30-Year AAA Yield",[m
[32m+[m[32m        "Euro Area Bonds",[m
[32m+[m[32m        EURO_DESCRIPTION,[m
[32m+[m[32m        "Source: European Central Bank (ECB)",[m
[32m+[m[32m        ["Euro 10Y", "Euro 20Y", "EUR/USD", "DAX", "US 30Y"],[m
[32m+[m[32m        ["Long-term inflation", "Fiscal conditions", "Term premium", "Sovereign risk", "Global yields"],[m
[32m+[m[32m    ),[m
[32m+[m[32m}[m
[32m+[m
[32m+[m
[32m+[m[32mRATES_BONDS_CATEGORY_MAP = {[m
[32m+[m[32m    "US Treasuries": [[m
[32m+[m[32m        "US 1M",[m
[32m+[m[32m        "US 3M",[m
[32m+[m[32m        "US 6M",[m
[32m+[m[32m        "US 1Y",[m
[32m+[m[32m        "US 2Y",[m
[32m+[m[32m        "US 3Y",[m
[32m+[m[32m        "US 5Y",[m
[32m+[m[32m        "US 7Y",[m
[32m+[m[32m        "US 10Y",[m
[32m+[m[32m        "US 20Y",[m
[32m+[m[32m        "US 30Y",[m
[32m+[m[32m    ],[m
[32m+[m[32m    "UK Gilts": [[m
[32m+[m[32m        "UK 5Y",[m
[32m+[m[32m        "UK 10Y",[m
[32m+[m[32m        "UK 20Y",[m
[32m+[m[32m    ],[m
[32m+[m[32m    "Japan JGBs": [[m
[32m+[m[32m        "Japan 1Y",[m
[32m+[m[32m        "Japan 2Y",[m
[32m+[m[32m        "Japan 3Y",[m
[32m+[m[32m        "Japan 5Y",[m
[32m+[m[32m        "Japan 7Y",[m
[32m+[m[32m        "Japan 10Y",[m
[32m+[m[32m        "Japan 20Y",[m
[32m+[m[32m        "Japan 30Y",[m
[32m+[m[32m        "Japan 40Y",[m
[32m+[m[32m    ],[m
[32m+[m[32m    "Euro Area Bonds": [[m
[32m+[m[32m        "Euro 1Y",[m
[32m+[m[32m        "Euro 2Y",[m
[32m+[m[32m        "Euro 3Y",[m
[32m+[m[32m        "Euro 5Y",[m
[32m+[m[32m        "Euro 7Y",[m
[32m+[m[32m        "Euro 10Y",[m
[32m+[m[32m        "Euro 20Y",[m
[32m+[m[32m        "Euro 30Y",[m
[32m+[m[32m    ],[m
[32m+[m[32m}[m
[32m+[m
[32m+[m
[32m+[m[32mRATES_BONDS_COMPARE_MAP = {[m
[32m+[m[32m    "Compare +": None,[m
[32m+[m[32m    **{[m
[32m+[m[32m        name: config["data_func"][m
[32m+[m[32m        for name, config in RATES_BONDS_MAP.items()[m
[32m+[m[32m    },[m
[32m+[m[32m}[m
\ No newline at end of file[m
