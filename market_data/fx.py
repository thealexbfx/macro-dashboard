FX_MAP = {
    "EUR/USD": {
        "ticker": "EURUSD=X",
        "category": "Major Pairs",
        "description": (
            "The EUR/USD currency pair reflects the relative economic "
            "performance, interest-rate expectations, and monetary-policy "
            "outlooks of the Euro Area and the United States. Movements are "
            "influenced by ECB and Federal Reserve decisions, economic data, "
            "and global risk sentiment."
        ),
        "related": [
            "DXY",
            "US 10Y Yield",
            "German 10Y Yield",
            "S&P 500",
            "Gold",
        ],
        "drivers": [
            "Fed policy expectations",
            "ECB policy expectations",
            "Interest-rate differentials",
            "Relative economic growth",
            "Global risk sentiment",
        ],
    },
    "GBP/USD": {
        "ticker": "GBPUSD=X",
        "category": "Major Pairs",
        "description": (
            "The GBP/USD pair is influenced by UK economic indicators, Bank "
            "of England policy decisions, and U.S. economic conditions. It "
            "often reacts to interest-rate differentials, inflation data, "
            "and political developments in both regions."
        ),
        "related": [
            "DXY",
            "UK 10Y Yield",
            "US 10Y Yield",
            "FTSE 100",
            "EUR/GBP",
        ],
        "drivers": [
            "Bank of England policy",
            "Federal Reserve policy",
            "Interest-rate differentials",
            "UK economic growth",
            "Political developments",
        ],
    },
    "USD/JPY": {
        "ticker": "USDJPY=X",
        "category": "Major Pairs",
        "description": (
            "The USD/JPY pair is sensitive to U.S. Treasury yields, Bank of "
            "Japan policy, and global risk sentiment. The yen often "
            "strengthens during periods of market uncertainty."
        ),
        "related": [
            "US 10Y Yield",
            "Japan 10Y Yield",
            "Nikkei 225",
            "DXY",
            "Gold",
        ],
        "drivers": [
            "Bank of Japan policy",
            "Federal Reserve policy",
            "Yield differentials",
            "Japanese intervention risk",
            "Global risk sentiment",
        ],
    },
    "DXY": {
        "ticker": "DX-Y.NYB",
        "category": "Major Pairs",
        "description": (
            "The U.S. Dollar Index measures the strength of the dollar "
            "against a basket of major currencies. It reacts to U.S. "
            "interest-rate expectations, economic data, geopolitical "
            "developments, and global demand for dollar liquidity."
        ),
        "related": [
            "EUR/USD",
            "US 10Y Yield",
            "Gold",
            "S&P 500",
            "Bitcoin",
        ],
        "drivers": [
            "Federal Reserve policy",
            "U.S. economic growth",
            "Interest-rate differentials",
            "Safe-haven demand",
            "Global dollar liquidity",
        ],
    },
    "EUR/GBP": {
        "ticker": "EURGBP=X",
        "category": "Cross Pairs",
        "description": (
            "EUR/GBP reflects differences in economic conditions and "
            "monetary-policy outlooks between the Euro Area and the United "
            "Kingdom. It is influenced by relative interest-rate expectations, "
            "trade developments, and growth trends."
        ),
        "related": [
            "EUR/USD",
            "GBP/USD",
            "UK 10Y Yield",
            "German 10Y Yield",
            "FTSE 100",
        ],
        "drivers": [
            "ECB policy expectations",
            "Bank of England policy",
            "Relative economic growth",
            "Interest-rate differentials",
            "UK and European politics",
        ],
    },
    "EUR/JPY": {
        "ticker": "EURJPY=X",
        "category": "Cross Pairs",
        "description": (
            "EUR/JPY is driven by differences between ECB and Bank of Japan "
            "policy, as well as global risk appetite. It often rises when the "
            "euro strengthens or risk sentiment improves and falls when the "
            "yen benefits from safe-haven demand."
        ),
        "related": [
            "EUR/USD",
            "USD/JPY",
            "Nikkei 225",
            "German 10Y Yield",
            "Japan 10Y Yield",
        ],
        "drivers": [
            "ECB policy",
            "Bank of Japan policy",
            "Yield differentials",
            "Euro Area growth",
            "Global risk appetite",
        ],
    },
    "GBP/JPY": {
        "ticker": "GBPJPY=X",
        "category": "Cross Pairs",
        "description": (
            "GBP/JPY is highly sensitive to global risk sentiment and "
            "monetary-policy differences between the United Kingdom and Japan. "
            "It is often used as a barometer for risk-on and risk-off market "
            "conditions."
        ),
        "related": [
            "GBP/USD",
            "USD/JPY",
            "Nikkei 225",
            "UK 10Y Yield",
            "Japan 10Y Yield",
        ],
        "drivers": [
            "Bank of England policy",
            "Bank of Japan policy",
            "Yield differentials",
            "Global risk appetite",
            "Market volatility",
        ],
    },
}


FX_CATEGORY_MAP = {
    "Major Pairs": [
        "EUR/USD",
        "GBP/USD",
        "USD/JPY",
        "DXY",
    ],
    "Cross Pairs": [
        "EUR/GBP",
        "EUR/JPY",
        "GBP/JPY",
    ],
}


FX_COMPARE_MAP = {
    "Compare +": None,
    "EUR/USD": "EURUSD=X",
    "GBP/USD": "GBPUSD=X",
    "USD/JPY": "USDJPY=X",
    "EUR/GBP": "EURGBP=X",
    "EUR/JPY": "EURJPY=X",
    "GBP/JPY": "GBPJPY=X",
    "DXY": "DX-Y.NYB",
    "S&P 500": "^GSPC",
    "Gold": "GC=F",
    "US 10Y Yield": "^TNX",
    "Bitcoin": "BTC-USD",
}