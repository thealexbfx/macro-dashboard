from data.eurostat import get_eurostat_series


EURO_AREA_GEO = "EA21"


def get_euro_unemployment_rate_data():
    return get_eurostat_series(
        "une_rt_m",
        {
            "geo": EURO_AREA_GEO,
            "sex": "T",
            "age": "TOTAL",
            "s_adj": "SA",
            "unit": "PC_ACT",
            "freq": "M",
        }
    )


def get_euro_gdp_qoq_data():
    return get_eurostat_series(
        "namq_10_gdp",
        {
            "geo": EURO_AREA_GEO,
            "na_item": "B1GQ",
            "s_adj": "SCA",
            "unit": "CLV_PCH_PRE",
            "freq": "Q",
        }
    )


def get_euro_gdp_yoy_data():
    return get_eurostat_series(
        "namq_10_gdp",
        {
            "geo": EURO_AREA_GEO,
            "na_item": "B1GQ",
            "s_adj": "SCA",
            "unit": "CLV_PCH_SM",
            "freq": "Q",
        }
    )


def get_euro_hicp_yoy_data():
    df = get_eurostat_series(
        "prc_hicp_minr",
        {
            "geo": "EA20",
            "unit": "I15",
            "freq": "M",
        }
    )

    df = df.copy()
    df["value"] = df["value"].pct_change(periods=12) * 100
    df = df.dropna(subset=["value"]).reset_index(drop=True)

    return df

def get_euro_core_hicp_yoy_data():
    df = get_eurostat_series(
        "prc_hicp_minr",
        {
            "geo": "EA20",
            "coicop18": "TOT_X_NRG_FOOD",
            "unit": "I15",
            "freq": "M",
        }
    )

    df = df.copy()
    df["value"] = df["value"].pct_change(periods=12) * 100
    df = df.dropna(subset=["value"]).reset_index(drop=True)

    return df


def get_euro_industrial_production_mom_data():
    return get_eurostat_series(
        "sts_inpr_m",
        {
            "geo": "EA20",
            "indic_bt": "PRD",
            "nace_r2": "B-D",
            "s_adj": "SCA",
            "unit": "PCH_PRE",
            "freq": "M",
        }
    )


def get_euro_retail_sales_mom_data():
    return get_eurostat_series(
        "sts_trtu_m",
        {
            "geo": EURO_AREA_GEO,
            "indic_bt": "VOL_SLS",
            "nace_r2": "G47",
            "s_adj": "SCA",
            "unit": "PCH_PRE",
            "freq": "M",
        }
    )