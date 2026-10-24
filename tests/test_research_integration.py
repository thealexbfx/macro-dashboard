"""Offline integration regressions: real service, registries, charts and local storage."""

from datetime import date
from tempfile import TemporaryDirectory
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services.historical_relationships import (
    HistoricalRelationshipService,
    MacroRegimeHistoryProvider,
)
from components.research.comparison import comparison_figure
from macro_engine.research.analytics import SeriesMetadata, analyze
from macro_engine.research.notebook import load_investigations, save_investigation


class Provider:
    def market_series(self, spec, start, end):
        dates = pd.date_range(start, end, freq="B")
        return [(d.date(), 100 + i + np.sin(i)) for i, d in enumerate(dates)]

    def fred_series(self, series_id, start, end):
        dates = pd.date_range(start, end, freq="MS" if series_id == "UNRATE" else "B")
        return [
            (d.date(), 4 + 0.001 * i + 0.1 * np.sin(i)) for i, d in enumerate(dates)
        ]


def service():
    return HistoricalRelationshipService(
        Provider(), MacroRegimeHistoryProvider(lambda _: None), lambda: date(2025, 1, 1)
    )


def test_production_monthly_market_comparison_is_aligned_before_transform():
    answer = service().analyze("sp500", "unemployment", "5_years")
    evidence = answer.blocks[0].data
    assert evidence["methodology"]["frequency"] == "monthly"
    assert 45 <= evidence["observations"] <= 61
    assert evidence["methodology"]["right_change_unit"] == "percentage points"
    assert evidence["lead_lag"]
    assert evidence["stability"]["rolling"]
    assert "monthly observations" in answer.answer


def test_production_yield_units_and_json_serialization():
    answer = service().analyze("us10y", "sp500")
    evidence = answer.blocks[0].data
    assert evidence["methodology"]["left_change_unit"] == "basis points"
    import json

    json.dumps(answer.to_dict(), allow_nan=False)


def test_notebook_atomic_roundtrip_update_and_path_rejection():
    with TemporaryDirectory() as root:
        record = save_investigation(
            {"title": "Test", "counterarguments": "No causal evidence"}, root
        )
        assert load_investigations(root) == [record]
        changed = save_investigation({"title": "Edited"}, root, record["id"])
        assert load_investigations(root) == [changed]
        with pytest.raises(ValueError):
            save_investigation({}, root, "../../escape")
        with pytest.raises(ValueError):
            save_investigation({"value": float("nan")}, root)


def test_existing_registry_is_enriched_without_duplicate_loaders():
    from app_pages.comparison_registry import COMPARISON_REGISTRY as compat
    from comparison_registry import COMPARISON_REGISTRY

    assert compat is COMPARISON_REGISTRY
    assert len(COMPARISON_REGISTRY) > 100
    for spec in COMPARISON_REGISTRY.values():
        assert spec["metadata"].frequency in {
            "daily",
            "weekly",
            "monthly",
            "quarterly",
            "annual",
        }
    gold = next(v for v in COMPARISON_REGISTRY.values() if v["name"] == "Gold")
    assert gold["metadata"].return_eligible
    assert gold["metadata"].ratio_group


def test_chart_uses_separate_panels_and_embeds_methodology():
    frame = pd.DataFrame(
        {
            "date": pd.date_range("2020-01-01", periods=4, freq="MS"),
            "value": [1, 2, 4, 3],
        }
    )
    values, details = analyze(frame, frame, SeriesMetadata(), SeriesMetadata(), "Price")
    fig = comparison_figure(values, details, "A", "B")
    assert fig.data[0].yaxis != fig.data[1].yaxis
    assert not fig.data[0].connectgaps
    assert any("monthly" in annotation.text for annotation in fig.layout.annotations)


def test_additive_api_and_existing_contracts():
    client = TestClient(app)
    assert client.get("/health").status_code == 200
    assert client.get("/api/research/relationships/series").status_code == 200
    assert (
        client.get(
            "/api/research/relationships", params={"target": "bad", "driver": "gold"}
        ).status_code
        == 422
    )
    with patch(
        "backend.app.api.routes.relationships.HistoricalRelationshipService",
        return_value=service(),
    ):
        response = client.get(
            "/api/research/relationships", params={"target": "us10y", "driver": "sp500"}
        )
    assert response.status_code == 200
    assert response.json()["customer_answer"]["blocks"][0]["data"]["lead_lag"]


def test_weekday_daily_grid_does_not_invent_weekends():
    dates = pd.date_range("2020-01-01", periods=90, freq="B")
    frame = pd.DataFrame(
        {"date": dates, "value": 100 + np.arange(90) + np.sin(np.arange(90))}
    )
    meta = SeriesMetadata(
        frequency="daily", representation="price", can_be_nonpositive=False
    )
    values, details = analyze(
        frame, frame, meta, meta, "Rolling Correlation", window=60
    )
    assert len(values) == 90
    assert details["valid_statistics"] == 30


def test_effective_policy_state_persists_only_when_declared_and_within_bound():
    from dataclasses import replace
    from macro_engine.research.analytics import align

    policy = pd.DataFrame(
        {"date": pd.to_datetime(["2020-01-01", "2020-04-01"]), "value": [1.0, 2.0]}
    )
    monthly = pd.DataFrame(
        {
            "date": pd.date_range("2020-01-01", periods=4, freq="MS"),
            "value": [1, 2, 3, 4],
        }
    )
    meta = SeriesMetadata(frequency="monthly", representation="rate")
    aligned, _ = align(policy, monthly, replace(meta, carry_forward_days=45), meta)
    assert aligned.left.iloc[1] == 1
    assert pd.isna(aligned.left.iloc[2])
    unfilled, _ = align(policy, monthly, meta, meta)
    assert pd.isna(unfilled.left.iloc[1])




def test_notebook_streamlit_smoke():
    from streamlit.testing.v1 import AppTest

    script = """
import pandas as pd
import components.research.notebook as notebook
from macro_engine.research.analytics import SeriesMetadata
def loader():
    return pd.DataFrame({"date": pd.date_range("2020-01-01", periods=50, freq="MS"), "value": [100+i+i%3 for i in range(50)]})
meta = SeriesMetadata(units="%", representation="rate")
notebook.COMPARISON_REGISTRY = {name: {"kind": "function", "loader": loader, "metadata": meta} for name in ["A", "B"]}
notebook.load_investigations = lambda: []
notebook.render_notebook()
"""
    app_test = AppTest.from_string(script).run(timeout=20)
    assert not app_test.exception
    app_test.button[0].click().run(timeout=20)
    assert not app_test.exception
    assert len(app_test.get("plotly_chart")) == 1
    assert {button.label for button in app_test.get("download_button")} == {"Export investigation", "Export observations", "Export rolling correlations", "Export research chart"}


def test_notebook_saves_reopens_and_updates_same_record(tmp_path):
    import json
    from streamlit.testing.v1 import AppTest

    script = """
import pandas as pd
import components.research.notebook as notebook
from macro_engine.research.analytics import SeriesMetadata
from macro_engine.research.notebook import load_investigations, save_investigation
def loader():
    return pd.DataFrame({"date": pd.date_range("2020-01-01", periods=50, freq="MS"), "value": [100+i+i%3 for i in range(50)]})
meta = SeriesMetadata(units="%", representation="rate")
notebook.COMPARISON_REGISTRY = {name: {"kind": "function", "loader": loader, "metadata": meta} for name in ["A", "B"]}
notebook.load_investigations = lambda: load_investigations(ROOT)
notebook.save_investigation = lambda payload, investigation_id=None: save_investigation(payload, ROOT, investigation_id)
notebook.render_notebook()
""".replace("ROOT", repr(str(tmp_path)))
    ui = AppTest.from_string(script).run(timeout=20)
    next(b for b in ui.button if b.label == "Run investigation").click().run(timeout=20)
    next(b for b in ui.button if b.label == "Save investigation locally").click().run(
        timeout=20
    )
    assert not ui.exception
    assert len(list(tmp_path.glob("*.json"))) == 1
    record_path = next(tmp_path.glob("*.json"))
    record = json.loads(record_path.read_text(encoding="utf-8"))
    assert ui.selectbox[0].value == record["id"]
    ui.text_area[2].set_value("Revisions matter.").run(timeout=20)
    next(b for b in ui.button if b.label == "Save investigation locally").click().run(
        timeout=20
    )
    assert len(list(tmp_path.glob("*.json"))) == 1
    assert (
        json.loads(record_path.read_text(encoding="utf-8"))["counterarguments"]
        == "Revisions matter."
    )
    # A fresh page restores saved charts using observations, without providers.
    del ui.session_state[f"evidence_{record['id']}"]
    ui.run(timeout=20)
    assert not ui.exception
    assert len(ui.get("plotly_chart")) == 1




def test_regime_join_never_uses_future_snapshot():
    from types import SimpleNamespace

    regimes = MacroRegimeHistoryProvider(lambda _: None)
    regimes.snapshots = lambda _: (
        SimpleNamespace(
            as_of_date=date(2030, 1, 1),
            environment_label="Future",
            activity_label="Future",
            inflation_impulse_label="Future",
            financial_impulse_label="Future",
        ),
    )
    svc = service()
    svc.regimes = regimes
    answer = svc.analyze("gold", "us10y_real")
    assert answer.blocks[0].data["regime_context"] is None


def test_connector_monthly_growth_does_not_bridge_missing_months():
    from data.transforms import calculate_mom_pct_change, calculate_yoy_from_index

    frame = pd.DataFrame(
        {
            "date": pd.to_datetime(["2020-01-01", "2020-03-01", "2020-04-01"]),
            "value": [100, 120, 132],
        }
    )
    out = calculate_mom_pct_change(frame)
    assert len(out) == 1
    assert out.value.iloc[0] == pytest.approx(10)
    zeros = pd.DataFrame(
        {"date": pd.to_datetime(["2020-01-01", "2021-01-01"]), "value": [0, 100]}
    )
    assert calculate_yoy_from_index(zeros).empty


def test_streamlit_application_starts_without_openai_key(monkeypatch):
    from pathlib import Path

    from streamlit.testing.v1 import AppTest

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    import components.product as product
    monkeypatch.setattr(product,"recent_series",lambda *args: (_ for _ in ()).throw(RuntimeError("offline entry test")))
    app_test = AppTest.from_file(
        str(Path(__file__).resolve().parents[1] / "app.py")
    ).run(timeout=25)
    assert not app_test.exception
    assert not app_test.error


def test_relationship_question_with_rate_is_not_misrouted_as_lookup():
    from backend.app.research.planner import ResearchIntent, ResearchPlanner

    plan = ResearchPlanner().plan(
        "What is the relationship between unemployment rate and gold historically?"
    )
    assert plan.intent == ResearchIntent.HISTORICAL_RELATIONSHIP
    assert set(plan.assets) == {"unemployment", "gold"}
