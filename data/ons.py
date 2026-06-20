import pandas as pd
import requests
import streamlit as st


def parse_ons_date(x):
    x = str(x).strip()

    # Monthly format: 2026 APR
    try:
        return pd.to_datetime(x, format="%Y %b")
    except Exception:
        pass

    # Quarterly format: 2026 Q1
    if "Q" in x:
        try:
            year, quarter = x.split()

            month_map = {
                "Q1": 3,
                "Q2": 6,
                "Q3": 9,
                "Q4": 12,
            }

            month = month_map.get(quarter)

            if month:
                return (
                    pd.Timestamp(
                        year=int(year),
                        month=month,
                        day=1
                    )
                    + pd.offsets.MonthEnd(0)
                )
        except Exception:
            pass

    # Fallback
    return pd.to_datetime(x, errors="coerce")


@st.cache_data(ttl=1800)
def get_ons_timeseries(cdid: str, dataset_id: str, path: str):
    """
    Generic ONS timeseries loader.

    Examples:
    CPI:
    cdid="D7G7"
    dataset_id="MM23"
    path="economy/inflationandpriceindices"

    Unemployment:
    cdid="MGSX"
    dataset_id="LMS"
    path="employmentandlabourmarket/peoplenotinwork/unemployment"
    """

    cdid = cdid.lower()
    dataset_id = dataset_id.lower()

    url = (
        f"https://www.ons.gov.uk/"
        f"{path}/timeseries/{cdid}/{dataset_id}/data"
    )

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    r = requests.get(
        url,
        headers=headers,
        timeout=20
    )

    if r.status_code != 200:
        raise RuntimeError(
            f"ONS timeseries request failed: "
            f"{r.status_code} - {r.text[:300]}"
        )

    data = r.json()

    observations = (
        data.get("months")
        or data.get("quarters")
        or data.get("years")
    )

    if not observations:
        return pd.DataFrame(columns=["date", "value"])

    df = pd.DataFrame(observations)

    df["date"] = df["date"].apply(parse_ons_date)
    df["value"] = pd.to_numeric(
        df["value"],
        errors="coerce"
    )

    df = (
        df[["date", "value"]]
        .dropna()
        .sort_values("date")
        .reset_index(drop=True)
    )

    return df
    
@st.cache_data(ttl=86400, show_spinner=False)
def get_uk_services_cpi_yoy_data():
    return get_ons_timeseries(
        "D7NN", "MM23",
        "economy/inflationandpriceindices"
    )


@st.cache_data(ttl=86400, show_spinner=False)
def get_uk_gdp_mom_data():
    return get_ons_timeseries(
        "ECY2", "MGDP",
        "economy/grossdomesticproductgdp"
    )