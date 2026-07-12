COMMODITY_MAP = {
    "Gold": {
        "ticker": "GC=F",
        "category": "Metals",
        "description": (
            "Gold is a safe-haven asset that reacts to inflation "
            "expectations, USD strength, interest rates, real yields, "
            "and geopolitical uncertainty."
        ),
        "related": [
            "DXY",
            "US 10Y Real Yield",
            "FedWatch",
            "Silver",
            "Oil",
        ],
        "drivers": [
            "Dollar strength",
            "Real yields",
            "Fed expectations",
            "Inflation expectations",
            "Geopolitical risk",
        ],
    },
    "Silver": {
        "ticker": "SI=F",
        "category": "Metals",
        "description": (
            "Silver acts both as a precious metal and industrial "
            "commodity, reacting to real yields, risk appetite, "
            "and manufacturing demand."
        ),
        "related": [
            "Gold",
            "DXY",
            "Copper",
            "Real Yields",
            "Industrial metals",
        ],
        "drivers": [
            "Gold trend",
            "Industrial demand",
            "Real yields",
            "Dollar strength",
            "Risk sentiment",
        ],
    },
    "Copper": {
        "ticker": "HG=F",
        "category": "Metals",
        "description": (
            "Copper is a key industrial metal closely linked to global "
            "manufacturing, construction, China demand, and the growth cycle."
        ),
        "related": [
            "China data",
            "DXY",
            "Industrial production",
            "Equities",
            "Oil",
        ],
        "drivers": [
            "Global growth",
            "China demand",
            "Manufacturing activity",
            "Supply disruptions",
            "Dollar strength",
        ],
    },
    "Crude Oil": {
        "ticker": "CL=F",
        "category": "Energy",
        "description": (
            "Crude oil prices reflect global supply and demand dynamics, "
            "OPEC production decisions, inventories, and geopolitical risk."
        ),
        "related": [
            "Brent Oil",
            "DXY",
            "Energy equities",
            "Inflation expectations",
            "10Y Yield",
        ],
        "drivers": [
            "Global growth",
            "OPEC supply",
            "Inventories",
            "Geopolitics",
            "Dollar strength",
        ],
    },
    "Brent Oil": {
        "ticker": "BZ=F",
        "category": "Energy",
        "description": (
            "Brent crude is a global oil benchmark influenced by "
            "international demand, OPEC policy, supply risk, and "
            "geopolitical events."
        ),
        "related": [
            "Crude Oil",
            "DXY",
            "Inflation expectations",
            "Energy equities",
            "10Y Yield",
        ],
        "drivers": [
            "Global demand",
            "OPEC supply",
            "Middle East risk",
            "Inventories",
            "Dollar strength",
        ],
    },
    "Natural Gas": {
        "ticker": "NG=F",
        "category": "Energy",
        "description": (
            "Natural gas prices are sensitive to weather, storage levels, "
            "LNG flows, production, and seasonal demand."
        ),
        "related": [
            "Crude Oil",
            "Power prices",
            "Weather",
            "Inventories",
            "Energy equities",
        ],
        "drivers": [
            "Weather",
            "Storage",
            "LNG exports",
            "Production",
            "Seasonal demand",
        ],
    },
    "Wheat": {
        "ticker": "ZW=F",
        "category": "Agriculture",
        "description": (
            "Wheat prices respond to weather, crop yields, export policy, "
            "global demand, and geopolitical supply disruptions."
        ),
        "related": [
            "Corn",
            "Soybeans",
            "DXY",
            "Food inflation",
            "Weather",
        ],
        "drivers": [
            "Weather",
            "Crop yields",
            "Export policy",
            "Global demand",
            "Geopolitical supply risk",
        ],
    },
    "Corn": {
        "ticker": "ZC=F",
        "category": "Agriculture",
        "description": (
            "Corn prices are driven by crop conditions, ethanol demand, "
            "livestock feed demand, weather, and global trade flows."
        ),
        "related": [
            "Wheat",
            "Soybeans",
            "Ethanol",
            "DXY",
            "Weather",
        ],
        "drivers": [
            "Weather",
            "Ethanol demand",
            "Feed demand",
            "Crop yields",
            "Trade policy",
        ],
    },
    "Soybeans": {
        "ticker": "ZS=F",
        "category": "Agriculture",
        "description": (
            "Soybean prices track crop supply, global demand, China imports, "
            "biofuel demand, and trade policy."
        ),
        "related": [
            "Corn",
            "Wheat",
            "China demand",
            "DXY",
            "Biofuels",
        ],
        "drivers": [
            "China demand",
            "Weather",
            "Crop yields",
            "Biofuel demand",
            "Trade policy",
        ],
    },
}


COMMODITY_CATEGORY_MAP = {
    "Metals": [
        "Gold",
        "Silver",
        "Copper",
    ],
    "Energy": [
        "Crude Oil",
        "Brent Oil",
        "Natural Gas",
    ],
    "Agriculture": [
        "Wheat",
        "Corn",
        "Soybeans",
    ],
}


COMMODITY_COMPARE_MAP = {
    "Compare +": None,
    "Gold": "GC=F",
    "Silver": "SI=F",
    "Copper": "HG=F",
    "Crude Oil": "CL=F",
    "Brent Oil": "BZ=F",
    "Natural Gas": "NG=F",
    "DXY": "DX-Y.NYB",
    "S&P 500": "^GSPC",
    "Nasdaq": "^IXIC",
    "Bitcoin": "BTC-USD",
}