CRYPTO_MAP = {
    "Bitcoin": {
        "ticker": "BTC-USD",
        "category": "Major Coins",
        "description": (
            "Bitcoin is the largest cryptocurrency by market capitalization "
            "and is often described as digital gold. Its price is influenced "
            "by investor sentiment, institutional adoption, regulation, "
            "macroeconomic conditions, liquidity, and the supply dynamics "
            "created by its fixed issuance schedule."
        ),
        "related": [
            "Ethereum",
            "DXY",
            "Gold",
            "NASDAQ",
            "US 10Y Yield",
        ],
        "drivers": [
            "Global liquidity",
            "Institutional adoption",
            "Regulatory developments",
            "Risk sentiment",
            "Dollar strength",
        ],
    },
    "Ethereum": {
        "ticker": "ETH-USD",
        "category": "Major Coins",
        "description": (
            "Ethereum is the leading smart-contract platform, supporting "
            "decentralized applications, decentralized finance, tokenized "
            "assets, and other blockchain-based activity. Its value is "
            "influenced by network usage, technological upgrades, transaction "
            "fees, developer activity, and wider crypto-market sentiment."
        ),
        "related": [
            "Bitcoin",
            "NASDAQ",
            "DXY",
            "Crypto market activity",
            "Decentralized finance",
        ],
        "drivers": [
            "Network activity",
            "Protocol upgrades",
            "Transaction fees",
            "Developer adoption",
            "Crypto risk sentiment",
        ],
    },
}


CRYPTO_CATEGORY_MAP = {
    "Major Coins": [
        "Bitcoin",
        "Ethereum",
    ],
}


CRYPTO_COMPARE_MAP = {
    "Compare +": None,
    "Bitcoin": "BTC-USD",
    "Ethereum": "ETH-USD",
    "S&P 500": "^GSPC",
    "NASDAQ": "^IXIC",
    "Gold": "GC=F",
    "DXY": "DX-Y.NYB",
    "US 10Y Yield": "^TNX",
}
for _config in CRYPTO_MAP.values():
    _config.update(unit_label="USD per coin", representation="price", frequency="daily",
                   can_be_nonpositive=False, source="Yahoo Finance closing quotes")
