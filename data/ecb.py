import pandas as pd
import streamlit as st


@st.cache_data(ttl=60)
def get_ecb_main_refinancing_rate_data():
    """
    ECB Main Refinancing Rate
    Official ECB Data Portal
    """

    url = (
        "https://data-api.ecb.europa.eu/service/data/"
        "FM/B.U2.EUR.4F.KR.MRR_FR.LEV?format=csvdata"
    )

    df = pd.read_csv(url)

    df = df[["TIME_PERIOD", "OBS_VALUE"]].copy()

    df = df.rename(
        columns={
            "TIME_PERIOD": "date",
            "OBS_VALUE": "value"
        }
    )

    df["date"] = pd.to_datetime(df["date"])
    df["value"] = pd.to_numeric(df["value"], errors="coerce")

    df = df.dropna()
    df = df.sort_values("date").reset_index(drop=True)

    return df
    
@st.cache_data(ttl=60)
def get_ecb_negotiated_wages_data():

    url = (
        "https://data-api.ecb.europa.eu/service/data/"
        "EWT/M.U2.N.WT.INWS._T.4F0.GY?format=csvdata"
    )

    df = pd.read_csv(url)

    df = df[["TIME_PERIOD", "OBS_VALUE"]].copy()

    df = df.rename(
        columns={
            "TIME_PERIOD": "date",
            "OBS_VALUE": "value"
        }
    )

    df["date"] = pd.to_datetime(df["date"])
    df["value"] = pd.to_numeric(df["value"], errors="coerce")

    return (
        df.dropna()
        .sort_values("date")
        .reset_index(drop=True)
    )
    
    
@st.cache_data(ttl=60)
def get_ecb_labor_productivity_data():

    url = (
        "https://data-api.ecb.europa.eu/service/data/"
        "MNA/Q.Y.I10.W0.S1.S1._Z.LPR_HW._Z._T._Z.EUR.LR.GY"
        "?format=csvdata"
    )

    df = pd.read_csv(url)

    df = df[["TIME_PERIOD", "OBS_VALUE"]].copy()

    df = df.rename(
        columns={
            "TIME_PERIOD": "date",
            "OBS_VALUE": "value"
        }
    )

    df["date"] = pd.to_datetime(df["date"])
    df["value"] = pd.to_numeric(df["value"], errors="coerce")

    return (
        df.dropna()
        .sort_values("date")
        .reset_index(drop=True)
    )
    
@st.cache_data(ttl=60)
def get_ecb_balance_sheet_data():

    url = (
        "https://data-api.ecb.europa.eu/service/data/"
        "ILM/W.U2.C.T000000.Z5.Z01"
        "?format=csvdata"
    )

    df = pd.read_csv(url)

    df = df[["TIME_PERIOD", "OBS_VALUE"]].copy()

    df = df.rename(columns={
        "TIME_PERIOD": "date",
        "OBS_VALUE": "value"
    })

    df["date"] = pd.to_datetime(
        df["date"].astype(str) + "-1",
        format="%G-W%V-%u",
        errors="coerce"
    )
    df["value"] = pd.to_numeric(df["value"], errors="coerce")

    return (
        df.dropna()
        .sort_values("date")
        .reset_index(drop=True)
    )
    
@st.cache_data(ttl=60)
def get_ecb_house_price_index_data():

    url = (
        "https://data-api.ecb.europa.eu/service/data/"
        "RESR/Q.U2._T.N._TR.TVAL.4D0.TB.N.IX"
        "?format=csvdata"
    )

    df = pd.read_csv(url)

    df = df[["TIME_PERIOD", "OBS_VALUE"]].copy()
    df = df.rename(columns={"TIME_PERIOD": "date", "OBS_VALUE": "value"})

    df["date"] = pd.to_datetime(df["date"])
    df["value"] = pd.to_numeric(df["value"], errors="coerce")

    df = df.dropna().sort_values("date").reset_index(drop=True)

    df["value"] = df["value"].pct_change(4) * 100

    return df.dropna().reset_index(drop=True)
    
@st.cache_data(ttl=60)
def get_ecb_trade_balance_data():

    export_url = (
        "https://data-api.ecb.europa.eu/service/data/"
        "TRD/M.I10.N.X.TTT.J10.4.VAL"
        "?format=csvdata"
    )

    import_url = (
        "https://data-api.ecb.europa.eu/service/data/"
        "TRD/M.I10.N.M.TTT.J10.4.VAL"
        "?format=csvdata"
    )

    exports = pd.read_csv(export_url)[["TIME_PERIOD", "OBS_VALUE"]]
    imports = pd.read_csv(import_url)[["TIME_PERIOD", "OBS_VALUE"]]

    exports = exports.rename(columns={
        "TIME_PERIOD": "date",
        "OBS_VALUE": "exports"
    })

    imports = imports.rename(columns={
        "TIME_PERIOD": "date",
        "OBS_VALUE": "imports"
    })

    df = exports.merge(imports, on="date", how="inner")

    df["date"] = pd.to_datetime(df["date"])
    df["exports"] = pd.to_numeric(df["exports"], errors="coerce")
    df["imports"] = pd.to_numeric(df["imports"], errors="coerce")

    # ECB gives values in thousands of euros
    # convert to millions of euros
    df["value"] = (df["exports"] - df["imports"]) / 1000

    return (
        df[["date", "value"]]
        .dropna()
        .sort_values("date")
        .reset_index(drop=True)
    )