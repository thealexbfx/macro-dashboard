import pandas as pd
import pytest
from components.chart_workspace import plain_finding


@pytest.mark.parametrize(
    "r,text",
    [
        (None, "not enough"),
        (0.01, "little connection"),
        (-0.16, "opposite directions"),
        (0.6, "same direction"),
    ],
)
def test_plain_finding(r, text):
    assert text in plain_finding(r)


def test_chart_only_investigation_and_repeat_save(monkeypatch):
    from streamlit.testing.v1 import AppTest
    import components.chart_workspace as charts

    dates = pd.date_range("2023-01-01", periods=400, freq="B")
    monkeypatch.setattr(
        charts,
        "load_series",
        lambda *args: pd.DataFrame(
            {"date": dates, "value": [100 + i + i % 3 for i in range(400)]}
        ),
    )
    monkeypatch.setattr(charts, "load_investigations", lambda: [])
    calls = []

    def save(payload, investigation_id=None):
        calls.append((payload, investigation_id))
        return {"id": "11111111-1111-4111-8111-111111111111"}

    monkeypatch.setattr(charts, "save_investigation", save)
    app = AppTest.from_string(
        "from components.chart_workspace import render_investigate;render_investigate()"
    ).run(timeout=20)
    assert not app.exception
    assert len(app.get("plotly_chart")) == 1
    assert len(app.selectbox) == 3
    assert (
        not app.text_input
        and not app.text_area
        and not app.date_input
        and not app.number_input
    )
    app.button[0].click().run(timeout=20)
    app.button[0].click().run(timeout=20)
    assert len(calls) == 2 and calls[1][1] == "11111111-1111-4111-8111-111111111111"
    assert "source_csv" in calls[0][0]["evidence"]


def test_chart_failure_has_no_form(monkeypatch):
    from streamlit.testing.v1 import AppTest
    import components.chart_workspace as charts

    monkeypatch.setattr(
        charts,
        "load_series",
        lambda *args: (_ for _ in ()).throw(RuntimeError("offline")),
    )
    monkeypatch.setattr(charts, "load_investigations", lambda: [])
    app = AppTest.from_string(
        "from components.chart_workspace import render_investigate;render_investigate()"
    ).run(timeout=20)
    assert not app.exception and app.info
    assert not app.text_input and not app.text_area


def test_saved_research_chart_reopens_without_providers(monkeypatch):
    from streamlit.testing.v1 import AppTest
    import components.chart_workspace as charts

    frame = pd.DataFrame(
        {
            "date": pd.date_range("2020-01-01", periods=40, freq="B"),
            "value": range(100, 140),
        }
    )
    record = dict(
        id="a",
        title="Earlier question",
        left="Commodities · Gold",
        right="Rates & Bonds · US 10Y",
        start="2020-01-01",
        end="2020-04-01",
        supporting="A previous conclusion",
        evidence={
            "source_csv": {
                side: frame.to_csv(index=False) for side in ["left", "right"]
            }
        },
    )
    monkeypatch.setattr(charts, "load_investigations", lambda: [record])
    monkeypatch.setattr(
        charts,
        "load_series",
        lambda *args: (_ for _ in ()).throw(AssertionError("no provider")),
    )
    app = AppTest.from_string(
        "from components.chart_workspace import render_chart_research;render_chart_research()"
    ).run(timeout=20)
    assert not app.exception
    assert len(app.get("plotly_chart")) == 1
    assert not app.text_input and not app.text_area
