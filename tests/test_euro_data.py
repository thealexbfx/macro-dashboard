import pandas as pd

from indicators.euro import get_euro_economic_sentiment_data


def test_euro_economic_sentiment_data_is_continuous():
    df = get_euro_economic_sentiment_data()

    assert len(df) >= 240
    assert df["date"].is_monotonic_increasing
    assert not df["date"].duplicated().any()
    assert df["value"].notna().all()
    assert df["date"].min() <= pd.Timestamp("2006-07-01")
    assert df["date"].max() >= pd.Timestamp("2026-06-01")