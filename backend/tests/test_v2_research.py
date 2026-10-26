import math
from datetime import date

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from backend.app.v2 import main as v2


class FixtureProvider:
    def __init__(self):
        self.fail = False
        self.calls = 0

    def fred_series(self, series_id, start, end):
        self.calls += 1
        if self.fail:
            raise RuntimeError("provider down")
        dates = pd.date_range("2018-01-01", "2025-12-01", freq="MS")
        if series_id == "A191RL1Q225SBEA":
            dates = pd.date_range("2018-01-01", "2025-10-01", freq="QS")
        return [
            (
                d.date(),
                100
                + i * 0.4
                + math.sin(i * 0.25) * (2 if series_id == "UNRATE" else 5),
            )
            for i, d in enumerate(dates)
            if not (series_id == "UNRATE" and d == pd.Timestamp("2023-06-01"))
        ]

    def market_series(self, spec, start, end):
        if self.fail:
            raise RuntimeError("down")
        return [
            (date(2026, 10, 22), 100),
            (date(2026, 10, 23), 101),
            (date(2026, 10, 24), 500),
        ]


@pytest.fixture
def service():
    return v2.DataService(FixtureProvider(), lambda: date(2026, 10, 24))


def req(**kwargs):
    return v2.ComparisonRequest(
        **dict(
            {
                "datasets": ["cpi", "unemployment"],
                "start": "2020-01-01",
                "end": "2025-12-31",
            },
            **kwargs,
        )
    )


def test_workflow_real_contract(service):
    result = v2.compare(
        service, req(transformations={"cpi": "yoy", "unemployment": "pp"})
    )
    assert result.statistics[0]["observations"] > 50
    assert result.statistics[0]["missing_periods"] >= 1
    assert result.series[0].units == "Percent YoY"
    assert result.series[1].units == "Percentage points per observation"
    assert "cpi" in result.raw_observations
    assert result.datasets[0].publication_date is None
    assert result.statistics[0]["rolling"]
    assert result.model_dump(mode="json")


@pytest.mark.parametrize(
    "key,mode",
    [
        ("unemployment", "percent"),
        ("real_gdp_growth", "indexed"),
        ("gold", "mom"),
        ("wti", "percent"),
    ],
)
def test_incompatible(service, key, mode):
    with pytest.raises(ValueError, match="incompatible"):
        v2.compare(service, req(datasets=[key], transformations={key: mode}))


def test_frequency_requires_consent(service):
    with pytest.raises(ValueError, match="Mixed frequencies"):
        v2.compare(service, req(datasets=["cpi", "real_gdp_growth"]))
    r = v2.compare(
        service, req(datasets=["cpi", "real_gdp_growth"], alignment="period_end")
    )
    assert r.statistics[0]["frequency"] == "quarterly"
    assert all(
        o.date.endswith(("03-31", "06-30", "09-30", "12-31"))
        for o in r.series[0].observations
    )


def test_missing_period_not_bridged(service):
    r = v2.compare(service, req(transformations={"unemployment": "pp"}))
    july = next(o for o in r.series[1].observations if o.date == "2023-07-01")
    assert july.value is None
    assert r.statistics[0]["observations"] < 72


@pytest.mark.parametrize(
    "mode", ["level", "percent", "yoy", "mom", "indexed", "standardized"]
)
def test_index_transforms(service, mode):
    r = v2.compare(service, req(datasets=["cpi"], transformations={"cpi": mode}))
    assert any(o.value is not None for o in r.series[0].observations)
    if mode == "indexed":
        assert r.series[0].observations[0].value == 100
    if mode == "standardized":
        assert (
            abs(
                sum(o.value for o in r.series[0].observations)
                / len(r.series[0].observations)
            )
            < 1e-10
        )


def test_cache_outage_and_no_fake(service):
    first = service.get("cpi")
    calls = service.provider.calls
    assert service.get("cpi") == first and service.provider.calls == calls
    service.ttl = -1
    service.provider.fail = True
    stale = service.get("cpi")
    assert stale.status == "stale" and stale.retrieved_at == first.retrieved_at
    assert service.get("unemployment").status == "unavailable"
    with pytest.raises(RuntimeError):
        v2.compare(service, req())


def test_current_market_bar_excluded(service):
    d = service.get("gold")
    assert d.latest_observation_date == "2026-10-23"
    assert d.latest_value == 101 and d.change == pytest.approx(1)


@pytest.mark.parametrize(
    "patch",
    [
        {"end": "2026-10-24"},
        {"end": "2019-01-01"},
        {"start": "1900-01-01"},
        {"datasets": ["unknown"]},
        {"datasets": ["cpi", "cpi"]},
    ],
)
def test_validation(service, patch):
    with pytest.raises(ValueError):
        v2.compare(service, req(**patch))


def test_routes(monkeypatch, service):
    monkeypatch.setattr(v2, "service", service)
    client = TestClient(v2.app)
    assert client.get("/health").status_code == 200
    catalogue = client.get("/api/v2/datasets").json()
    assert len(catalogue) == 30
    assert {"cpi","unemployment","gold","initial_claims","mortgage_30y"}.issubset({d["id"] for d in catalogue})
    assert all("provider_id" in d and "seasonal_adjustment" in d for d in catalogue)
    assert (
        client.post("/api/v2/compare", json=req().model_dump(mode="json")).status_code
        == 200
    )
    assert (
        client.post(
            "/api/v2/compare",
            json=req(datasets=["gold"], transformations={"gold": "mom"}).model_dump(
                mode="json"
            ),
        ).status_code
        == 422
    )
    assert client.post("/api/v2/compare", json={"datasets": []}).status_code == 422


def test_three_series_share_chart_and_statistics_frequency(service):
    r = v2.compare(
        service,
        req(
            datasets=["cpi", "unemployment", "real_gdp_growth"], alignment="period_end"
        ),
    )
    assert len(r.statistics) == 3
    assert all(s["frequency"] == "quarterly" for s in r.statistics)
    assert all(
        o.date.endswith(("03-31", "06-30", "09-30", "12-31"))
        for s in r.series
        for o in s.observations
    )


def test_zero_and_constant_transform_rejected():
    frame = pd.DataFrame(
        {"date": pd.date_range("2020-01-01", periods=3, freq="MS"), "value": [0, 1, 2]}
    )
    with pytest.raises(ValueError, match="positive"):
        v2.transform(frame, v2.SPECS["cpi"], "percent", date(2020, 1, 1))
    frame["value"] = 1
    with pytest.raises(ValueError, match="nonconstant"):
        v2.transform(frame, v2.SPECS["cpi"], "standardized", date(2020, 1, 1))
