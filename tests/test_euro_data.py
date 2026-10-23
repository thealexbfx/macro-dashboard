"""Euro-area composition splice with fixed, independently inspectable inputs."""

import pandas as pd
import pytest

import indicators.euro as euro


@pytest.mark.parametrize("end", ["2026-06-01", "2029-12-01"])
def test_euro_economic_sentiment_data_is_continuous(monkeypatch, end):
    historical_dates = pd.date_range("2000-01-01", "2026-03-01", freq="MS")
    current_dates = pd.date_range("2025-10-01", end, freq="MS")
    historical = pd.DataFrame({"date": historical_dates, "value": 90.0})
    current = pd.DataFrame({"date": current_dates, "value": 110.0})
    calls = []

    def provider(dataset, params):
        calls.append((dataset, params))
        assert "lastTimePeriod" not in params
        assert params["sinceTimePeriod"] == (
            "2000-01" if params["geo"] == "EA20" else "2026-01"
        )
        frame = historical if params["geo"] == "EA20" else current
        # Unsorted duplicates exercise the real output cleaning path.
        return pd.concat([frame.iloc[::-1], frame.iloc[:1]], ignore_index=True)

    monkeypatch.setattr(euro, "get_eurostat_series", provider)
    df = euro.get_euro_economic_sentiment_data()
    assert len(calls) == 2
    assert df.date.is_monotonic_increasing
    assert not df.date.duplicated().any()
    assert df.value.notna().all()
    assert df.date.min() == pd.Timestamp("2000-01-01")
    assert df.date.max() == pd.Timestamp(end)
    assert len(df) == len(pd.date_range("2000-01-01", end, freq="MS"))
    assert (df.loc[df.date < "2026-01-01", "value"] == 90).all()
    assert (df.loc[df.date >= "2026-01-01", "value"] == 110).all()
