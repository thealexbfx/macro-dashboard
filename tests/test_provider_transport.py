"""Verify transport behavior without weakening certificate verification."""

from unittest.mock import Mock

import pytest
import requests

from data.http import read_csv


def test_csv_transport_uses_verified_requests_and_bounds_timeout(monkeypatch):
    get = Mock(return_value=Mock(content=b"TIME_PERIOD,OBS_VALUE\n2025-01,3.5\n"))
    monkeypatch.setattr(requests, "get", get)
    result = read_csv("https://provider.example/series.csv")
    assert result.OBS_VALUE.tolist() == [3.5]
    get.assert_called_once_with("https://provider.example/series.csv", timeout=(10, 60))
    get.return_value.raise_for_status.assert_called_once()


def test_transport_propagates_certificate_errors(monkeypatch):
    monkeypatch.setattr(
        requests, "get", Mock(side_effect=requests.exceptions.SSLError("invalid chain"))
    )
    with pytest.raises(requests.exceptions.SSLError):
        read_csv("https://provider.example/series.csv")


def test_missing_fred_key_fails_before_http(monkeypatch):
    import data.fred as fred

    monkeypatch.setattr(fred, "FRED_API_KEY", None)
    get = Mock(side_effect=AssertionError("must not contact FRED"))
    monkeypatch.setattr(requests, "get", get)
    with pytest.raises(RuntimeError, match="FRED_API_KEY"):
        fred.get_fred_series.__wrapped__("UNRATE")
    get.assert_not_called()
