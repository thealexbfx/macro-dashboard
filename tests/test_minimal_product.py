from datetime import date
from unittest.mock import Mock
import numpy as np
import pandas as pd
import pytest
from components.layout import NAV_ITEMS, resolve_page
from components.product import daily_reading, investigation_url, validate_restore
from macro_engine.research.analytics import SeriesMetadata


def test_three_routes_and_legacy_migration():
    assert [k for k, _ in NAV_ITEMS["MacroLens"]] == [
        "Today",
        "Investigate",
        "MyResearch",
    ]
    assert resolve_page("ResearchWorkspace") == "Investigate"
    assert resolve_page("RatesBonds") == "Investigate"
    assert resolve_page("ResearchNotes") == "MyResearch"
    assert resolve_page("MacroEngineUSA") == "Today"
    assert "left=Commodities" in investigation_url(
        "Commodities · Gold", "Rates & Bonds · US 10Y"
    )


def test_daily_units_missing_and_stale():
    frame = pd.DataFrame(
        {"date": pd.to_datetime(["2020-01-01", "2020-01-02"]), "value": [2.0, 2.1]}
    )
    result = daily_reading(
        frame,
        SeriesMetadata(representation="yield", frequency="daily", units="%"),
        date(2020, 1, 10),
    )
    assert result["change"] == pytest.approx(10)
    assert result["age"] == 8
    frame.loc[0, "value"] = np.nan
    assert daily_reading(frame, SeriesMetadata(), date(2020, 1, 10))["change"] is None


def test_restore_rejects_invalid_fields():
    record = dict(
        title="Question",
        left="A",
        right="B",
        start="2020-01-01",
        end="2021-01-01",
        mode="Changes",
        window=12,
    )
    assert validate_restore(record) == record
    for bad in [
        [],
        {**record, "window": True},
        {**record, "start": "invalid"},
        {**record, "mode": "Forecast"},
        {**record, "evidence": {"csv": "bad"}},
    ]:
        with pytest.raises((ValueError, TypeError)):
            validate_restore(bad)


def test_today_failure_and_library_empty_states(monkeypatch):
    from streamlit.testing.v1 import AppTest

    script = """
import components.product as product
import components.chart_workspace as charts
charts.load_series=lambda *args: (_ for _ in ()).throw(RuntimeError('offline'))
product.load_investigations=lambda:[]
product.render_today()
product.render_research()
"""
    import components.product as product

    import components.chart_workspace as charts

    monkeypatch.setattr(charts, "load_series", charts.load_series)
    monkeypatch.setattr(product, "load_investigations", product.load_investigations)
    app = AppTest.from_string(script).run(timeout=20)
    assert not app.exception
    assert sum("Source unavailable" in item.value for item in app.info) == 4
    assert any("No investigations" in item.value for item in app.info)


def test_today_real_calculation_with_provider_fixture(monkeypatch):
    from streamlit.testing.v1 import AppTest

    script = """
import pandas as pd
from datetime import date,timedelta
import components.product as product
import components.chart_workspace as charts
charts.load_series=lambda *args: pd.DataFrame({'date':pd.to_datetime([date.today()-timedelta(days=2),date.today()-timedelta(days=1)]),'value':[100.,101.]})
product.load_investigations=lambda:[]
product.render_today()
"""
    import components.product as product

    import components.chart_workspace as charts

    monkeypatch.setattr(charts, "load_series", charts.load_series)
    monkeypatch.setattr(product, "load_investigations", product.load_investigations)
    app = AppTest.from_string(script).run(timeout=20)
    assert not app.exception
    assert len(app.metric) == 4
    assert len(app.get("plotly_chart")) == 6
    assert not app.text_input and not app.text_area and not app.number_input


def test_yahoo_missing_observations_preserved_and_tls_verified(monkeypatch):
    import requests
    from data.yahoo import get_fx_data_yahoo

    response = Mock()
    response.json.return_value = {
        "chart": {
            "result": [
                {
                    "timestamp": [1577836800, 1577923200],
                    "indicators": {"quote": [{"close": [100, None]}]},
                }
            ]
        }
    }
    get = Mock(return_value=response)
    monkeypatch.setattr(requests, "get", get)
    frame = get_fx_data_yahoo("GC=F", date(2020, 1, 1), date(2020, 1, 3))
    assert len(frame) == 2 and pd.isna(frame.value.iloc[-1])
    assert get.call_args.kwargs["timeout"] == (10, 20)
    assert "verify" not in get.call_args.kwargs
    response.raise_for_status.assert_called_once()
