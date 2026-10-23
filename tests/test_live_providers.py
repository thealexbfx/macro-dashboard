"""Explicit real-network smoke checks. Never substituted by synthetic fixtures."""

import pytest

pytestmark = pytest.mark.live


@pytest.mark.parametrize(
    "loader_name",
    [
        "get_ecb_negotiated_wages_data",
        "get_ecb_total_employment_yoy_data",
        "get_ecb_m3_yoy_data",
    ],
)
def test_live_ecb(loader_name):
    import data.ecb as ecb

    result = getattr(ecb, loader_name).__wrapped__()
    assert len(result) >= 36
    assert result.date.is_monotonic_increasing
    assert not result.date.duplicated().any()


def test_live_eurostat_sentiment():
    from indicators.euro import get_euro_economic_sentiment_data

    result = get_euro_economic_sentiment_data()
    assert len(result) >= 240
    assert result.date.min().year <= 2006
    assert result.date.is_monotonic_increasing


def test_live_fred():
    import data.fred as fred

    if not fred.FRED_API_KEY:
        pytest.skip(
            "FRED_API_KEY is not configured; authenticated FRED remains unverified."
        )
    result = fred.get_fred_series.__wrapped__("UNRATE")
    assert len(result) >= 36
