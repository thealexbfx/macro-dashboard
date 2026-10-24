import numpy as np
import pandas as pd
import pytest

from macro_engine.research.analytics import relationship
from macro_engine.research.presentation import (
    correlation_label,
    evidence_summary,
    rolling_diagnostics,
    stability_rows,
)


@pytest.mark.parametrize(
    "r,label",
    [
        (None, "Unavailable"),
        (float("nan"), "Unavailable"),
        (0, "Zero"),
        (-0.08, "Very weak negative"),
        (-0.16, "Weak negative"),
        (0.3, "Moderate positive"),
        (-0.5, "Strong negative"),
        (0.7, "Very strong positive"),
    ],
)
def test_labels(r, label):
    assert correlation_label(r) == label


def test_rolling_missing_windows_and_terminal_gap():
    frame = pd.DataFrame(
        {"left": np.arange(15.0), "right": np.arange(15.0) ** 2},
        index=pd.date_range("2020-01-01", periods=15),
    )
    frame.loc[frame.index[-2], "right"] = np.nan
    result = relationship(frame, window=3, minimum=3)
    d = rolling_diagnostics(frame, result["rolling"], 3)
    assert d["warmup_periods"] == 2
    assert d["incomplete_windows"] == 2
    assert d["valid_windows"] == 11
    assert not d["latest_period_available"]
    assert d["latest_valid_date"] == "2020-01-13"
    assert frame.isna().sum().sum() == 1


def test_constant_windows_and_empty_results():
    frame = pd.DataFrame(
        {"left": [1.0] * 5, "right": [2.0] * 5},
        index=pd.date_range("2020-01-01", periods=5),
    )
    r = relationship(frame, window=3, minimum=3)
    assert (
        rolling_diagnostics(frame, r["rolling"], 3)["undefined_complete_windows"] == 3
    )
    stability = {k: r[k] for k in ("full_sample", "first_half", "second_half")}
    assert "Insufficient" in evidence_summary(stability, r["lead_lag"])
    assert stability_rows(stability)[0]["Interpretation"] == "Unavailable"


def test_summary_does_not_imply_nonzero_predictive_lead():
    stats = {
        "observations": 30,
        "correlation": -0.16,
        "start": "2020-01-01",
        "end": "2020-02-01",
    }
    text = evidence_summary(
        {k: stats for k in ("full_sample", "first_half", "second_half")},
        [{"lag": 0, "correlation": -0.16}, {"lag": 1, "correlation": 0.03}],
    )
    assert "weak negative" in text
    assert "contemporaneous" in text
    assert "does not establish predictive" in text
    assert "n=30" in text




def test_historical_horizon_uses_calendar_month_not_next_available_row():
    from macro_engine.research.environment_validation import add_forward_outcomes

    frame = pd.DataFrame(
        {
            "month": pd.PeriodIndex(["2020-01", "2020-03", "2020-04"], freq="M"),
            "asset_close": [100.0, 120.0, 132.0],
        }
    )
    result = add_forward_outcomes(frame, [1, 2])
    assert pd.isna(result.forward_outcome_1m.iloc[0])
    assert result.forward_outcome_1m.iloc[1] == pytest.approx(0.1)
    assert result.forward_outcome_2m.iloc[0] == pytest.approx(0.2)
    assert pd.isna(result.forward_outcome_2m.iloc[-1])
    yields = add_forward_outcomes(
        frame.assign(asset_close=[2.0, 2.2, 2.1]),
        [1],
        outcome_mode="absolute_change",
        outcome_multiplier=100,
    )
    assert yields.forward_outcome_1m.iloc[1] == pytest.approx(-10.0)


def test_notebook_frequency_and_window_invalidate_previous_evidence():
    from streamlit.testing.v1 import AppTest

    script = """
import pandas as pd
import components.research.notebook as notebook
from macro_engine.research.analytics import SeriesMetadata
def loader():
    return pd.DataFrame({"date":pd.date_range("2020-01-01",periods=400,freq="B"),"value":[100+i+i%3 for i in range(400)]})
meta=SeriesMetadata(frequency="daily",representation="price",can_be_nonpositive=False)
notebook.COMPARISON_REGISTRY={n:{"kind":"function","loader":loader,"metadata":meta} for n in ["A","B"]}
notebook.load_investigations=lambda:[]
notebook.render_notebook()
"""
    app = AppTest.from_string(script).run(timeout=20)
    app.selectbox(key="freq_new").set_value("weekly").run()
    app.button[0].click().run(timeout=20)
    assert not app.exception
    assert len(app.get("plotly_chart")) == 1
    assert any("Weekly comparison" in x.value for x in app.caption)
    app.number_input(key="window_new").set_value(20).run()
    assert len(app.get("plotly_chart")) == 0
    app.button[0].click().run(timeout=20)
    assert len(app.get("plotly_chart")) == 1
    app.selectbox(key="freq_new").set_value("monthly").run()
    assert len(app.get("plotly_chart")) == 0

    failed_script = script.replace(
        "notebook.render_notebook()",
        "notebook.save_investigation=lambda *args, **kwargs: (_ for _ in ()).throw(OSError('disk unavailable'))\nnotebook.render_notebook()",
    )
    failed = AppTest.from_string(failed_script).run(timeout=20)
    failed.button[0].click().run(timeout=20)
    failed.button[1].click().run(timeout=20)
    assert not failed.exception
    assert failed.error
    assert len(failed.get("download_button")) == 4
