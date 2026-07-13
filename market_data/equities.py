EQUITIES_MAP = {
    "S&P 500": {
        "ticker": "^GSPC",
        "category": "US",
        "description": (
            "The S&P 500 tracks the performance of 500 large-cap U.S. "
            "companies across various sectors. It is a key benchmark for "
            "the overall health of the U.S. equity market and is widely "
            "used for portfolio performance comparison."
        ),
        "related": [
            "NASDAQ",
            "Dow Jones",
            "VIX",
            "US 10Y Yield",
            "DXY",
        ],
        "drivers": [
            "Corporate earnings",
            "Federal Reserve policy",
            "Economic growth",
            "Interest rates",
            "Risk sentiment",
        ],
    },
    "NASDAQ": {
        "ticker": "^IXIC",
        "category": "US",
        "description": (
            "The NASDAQ Composite is a tech-heavy index representing stocks "
            "listed on the NASDAQ exchange. It is sensitive to technology "
            "sector trends, innovation cycles, and growth-oriented investor "
            "sentiment."
        ),
        "related": [
            "S&P 500",
            "US 10Y Yield",
            "VIX",
            "Semiconductors",
            "DXY",
        ],
        "drivers": [
            "Technology earnings",
            "Interest rates",
            "Growth expectations",
            "Artificial intelligence investment",
            "Risk appetite",
        ],
    },
    "Dow Jones": {
        "ticker": "^DJI",
        "category": "US",
        "description": (
            "The Dow Jones Industrial Average tracks 30 large U.S. industrial "
            "and blue-chip companies. It is often used as a barometer of U.S. "
            "corporate and economic performance, particularly for established "
            "firms."
        ),
        "related": [
            "S&P 500",
            "NASDAQ",
            "VIX",
            "Industrial production",
            "US 10Y Yield",
        ],
        "drivers": [
            "Corporate earnings",
            "Industrial activity",
            "Economic growth",
            "Interest rates",
            "Investor sentiment",
        ],
    },
    "VIX": {
        "ticker": "^VIX",
        "category": "US",
        "description": (
            "The VIX, or Volatility Index, measures the market's expectations "
            "of near-term volatility in the S&P 500. It is often referred to "
            "as the fear gauge, rising during periods of uncertainty or "
            "market stress."
        ),
        "related": [
            "S&P 500",
            "NASDAQ",
            "US 10Y Yield",
            "Gold",
            "Credit spreads",
        ],
        "drivers": [
            "Market uncertainty",
            "Equity volatility",
            "Geopolitical risk",
            "Monetary policy surprises",
            "Investor positioning",
        ],
    },
    "FTSE 100": {
        "ticker": "^FTSE",
        "category": "Europe",
        "description": (
            "The FTSE 100 represents the 100 largest UK companies by market "
            "capitalization. It provides insight into the performance of the "
            "UK's blue-chip sector and is influenced by domestic economic data "
            "and global market trends."
        ),
        "related": [
            "DAX",
            "GBP/USD",
            "Brent Oil",
            "UK 10Y Yield",
            "European equities",
        ],
        "drivers": [
            "Global growth",
            "Commodity prices",
            "Sterling strength",
            "Bank of England policy",
            "Corporate earnings",
        ],
    },
    "DAX": {
        "ticker": "^GDAXI",
        "category": "Europe",
        "description": (
            "The DAX tracks 40 major German companies listed on the Frankfurt "
            "Stock Exchange. It serves as a key indicator of German corporate "
            "and economic health and is sensitive to Eurozone economic "
            "developments."
        ),
        "related": [
            "FTSE 100",
            "EUR/USD",
            "Euro Area growth",
            "Bund yields",
            "European equities",
        ],
        "drivers": [
            "Euro Area growth",
            "German manufacturing",
            "ECB policy",
            "Global trade",
            "Corporate earnings",
        ],
    },
    "Nikkei 225": {
        "ticker": "^N225",
        "category": "Asia",
        "description": (
            "The Nikkei 225 tracks 225 leading Japanese companies listed on "
            "the Tokyo Stock Exchange. It reflects Japan's equity market "
            "performance and is influenced by domestic economic conditions, "
            "corporate earnings, and global trade."
        ),
        "related": [
            "USD/JPY",
            "TOPIX",
            "Japan 10Y Yield",
            "NASDAQ",
            "Global trade",
        ],
        "drivers": [
            "Yen strength",
            "Bank of Japan policy",
            "Corporate earnings",
            "Global trade",
            "Risk sentiment",
        ],
    },
    "MSCI Emerging Markets ETF": {
        "ticker": "EEM",
        "category": "ETFs",
        "description": (
            "This ETF tracks equities in emerging market countries, providing "
            "broad exposure to developing economies. Performance is influenced "
            "by global growth trends, commodity prices, and investor risk "
            "appetite."
        ),
        "related": [
            "DXY",
            "China equities",
            "Copper",
            "US 10Y Yield",
            "S&P 500",
        ],
        "drivers": [
            "Dollar strength",
            "China growth",
            "Commodity prices",
            "Global liquidity",
            "Risk appetite",
        ],
    },
}


EQUITIES_CATEGORY_MAP = {
    "US": [
        "S&P 500",
        "NASDAQ",
        "Dow Jones",
        "VIX",
    ],
    "Europe": [
        "FTSE 100",
        "DAX",
    ],
    "Asia": [
        "Nikkei 225",
    ],
    "ETFs": [
        "MSCI Emerging Markets ETF",
    ],
}


EQUITIES_COMPARE_MAP = {
    "Compare +": None,
    "S&P 500": "^GSPC",
    "NASDAQ": "^IXIC",
    "Dow Jones": "^DJI",
    "VIX": "^VIX",
    "FTSE 100": "^FTSE",
    "DAX": "^GDAXI",
    "Nikkei 225": "^N225",
    "MSCI Emerging Markets ETF": "EEM",
    "Gold": "GC=F",
    "DXY": "DX-Y.NYB",
    "US 10Y Yield": "^TNX",
    "Bitcoin": "BTC-USD",
}