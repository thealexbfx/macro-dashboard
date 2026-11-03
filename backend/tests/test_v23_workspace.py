from datetime import date

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from backend.app.v2 import main as v2
from backend.app.v2.workspace import RecessionContext, prepare_series, recession_periods


class LagProvider:
    def fred_series(self, series_id, start, end):
        dates = pd.date_range("2018-01-01", "2025-12-01", freq="MS")
        if series_id == "A191RL1Q225SBEA":
            dates = dates[dates.month.isin([1, 4, 7, 10])]
        return [
            (
                d.date(),
                float(100 + ((i - (6 if series_id == "UNRATE" else 0)) * 17) % 53),
            )
            for i, d in enumerate(dates)
            if not (series_id == "UNRATE" and d == pd.Timestamp("2023-06-01"))
        ]


def compare(**extra):
    service = v2.DataService(LagProvider(), lambda: date(2026, 10, 24))
    args = {
        "datasets": ["cpi", "unemployment"],
        "start": "2020-01-01",
        "end": "2025-12-31",
        **extra,
    }
    return v2.compare(service, v2.ComparisonRequest(**args))


def test_positive_monthly_shift_recomputes_known_correlation():
    result = compare(lead_lag={"dataset_id": "cpi", "periods": 6, "unit": "months"})
    assert result.statistics[0]["correlation"] == pytest.approx(1)
    assert compare().statistics[0]["correlation"] < 0.9
    chart = result.series[0]
    assert chart.source_dates["2020-07-01"] == "2020-01-01"
    assert chart.shift_periods == 6
    assert result.lead_lag["dataset_id"] == "cpi"
    assert any("not predictive evidence" in warning for warning in result.warnings)


def test_negative_shift_retains_sources_and_correct_direction():
    result = compare(
        lead_lag={"dataset_id": "unemployment", "periods": -6, "unit": "months"}
    )
    assert result.statistics[0]["correlation"] == pytest.approx(1)
    assert result.series[1].source_dates["2020-01-01"] == "2020-07-01"


def test_shifted_scatter_and_statistics_use_identical_pairs():
    result = compare(lead_lag={"dataset_id": "cpi", "periods": 6, "unit": "months"})
    points = result.scatter
    assert len(points) == result.statistics[0]["observations"]
    assert all(p["x"] == p["y"] for p in points)
    assert points[0]["date"] == "2020-07-01"
    assert points[0]["x_source_date"] == "2020-01-01"
    assert points[0]["y_source_date"] == "2020-07-01"
    assert not any(p["date"] == "2023-06-30" for p in points)


def test_unshifted_scatter_keeps_native_source_labels():
    result = compare()
    assert result.scatter[0]["x_source_date"] == "2020-01-01"
    assert result.scatter[0]["y_source_date"] == "2020-01-01"
    assert result.scatter[0]["date"] == "2020-01-01"


@pytest.mark.parametrize("periods", [-12, -1, 0, 1, 12])
def test_timeframe_bounds_both_analytical_and_source_dates(periods):
    result = compare(
        start="2022-01-01",
        end="2024-09-23",
        lead_lag={"dataset_id": "cpi", "periods": periods, "unit": "months"},
    )
    for s in result.series:
        assert all("2022-01-01" <= o.date <= "2024-09-23" for o in s.observations)
        assert all(
            v is None or "2022-01-01" <= v <= "2024-09-23"
            for v in s.source_dates.values()
        )
    assert all(p["date"] <= "2024-09-23" for p in result.scatter)  # period-end labels


def test_missing_month_is_not_shifted_by_available_row_position():
    result = compare(
        lead_lag={"dataset_id": "unemployment", "periods": 6, "unit": "months"}
    )
    series = result.series[1]
    assert next(o for o in series.observations if o.date == "2023-12-01").value is None
    assert series.source_dates["2023-12-01"] is None
    assert series.source_dates["2024-01-01"] == "2023-07-01"


@pytest.mark.parametrize("mode", ["indexed", "standardized"])
def test_common_transformations_are_computed_before_shift(mode):
    base = compare(
        datasets=["cpi", "core_cpi"], transformations={"cpi": mode, "core_cpi": mode}
    )
    shifted = compare(
        datasets=["cpi", "core_cpi"],
        transformations={"cpi": mode, "core_cpi": mode},
        lead_lag={"dataset_id": "cpi", "periods": 6, "unit": "months"},
    )
    assert (
        base.series[0].observations[0].value == shifted.series[0].observations[0].value
    )
    if mode == "indexed":
        assert shifted.series[0].observations[0].value == 100
    else:
        values = [o.value for o in base.series[0].observations]
        assert sum(values) / len(values) == pytest.approx(0, abs=1e-12)


@pytest.mark.parametrize(
    "shift",
    [
        {"dataset_id": "gold", "periods": 1, "unit": "months"},
        {"dataset_id": "cpi", "periods": 1, "unit": "calendar_days"},
    ],
)
def test_incompatible_shift_rejected(shift):
    with pytest.raises(ValueError, match="Lead-lag"):
        compare(lead_lag=shift)


def test_mixed_frequencies_require_documented_alignment():
    with pytest.raises(ValueError, match="Mixed frequencies"):
        compare(
            datasets=["cpi", "real_gdp_growth"],
            lead_lag={"dataset_id": "cpi", "periods": 1, "unit": "quarters"},
        )
    result = compare(
        datasets=["cpi", "real_gdp_growth"],
        alignment="period_end",
        lead_lag={"dataset_id": "cpi", "periods": 1, "unit": "quarters"},
    )
    assert result.series[0].source_dates["2020-06-30"] == "2020-03-01"
    assert result.statistics[0]["frequency"] == "quarterly"


def test_daily_shift_means_calendar_days_not_trading_rows():
    values = pd.Series([1.0, 2.0], index=pd.to_datetime(["2024-01-05", "2024-01-08"]))
    shifted, sources = prepare_series(
        values, "daily", "native", "2024-01-01", "2024-01-31", 1
    )
    assert list(shifted.index.strftime("%Y-%m-%d")) == ["2024-01-06", "2024-01-09"]
    assert sources["2024-01-06"] == "2024-01-05"


def test_period_end_sampling_retains_last_source_and_null():
    values = pd.Series(
        [2.0, 3.0, None],
        index=pd.to_datetime(["2024-01-05", "2024-01-26", "2024-02-28"]),
    )
    sampled, sources = prepare_series(
        values, "monthly", "period_end", "2024-01-01", "2024-03-01"
    )
    assert sampled.iloc[0] == 3
    assert pd.isna(sampled.iloc[1])
    assert sources["2024-01-31"] == "2024-01-26"


def test_no_coverage_does_not_erase_other_series():
    result = compare(start="2025-12-02", end="2025-12-20")
    assert result.statistics[0]["correlation"] is None
    assert result.statistics[0]["observations"] == 0
    assert result.scatter == []


@pytest.mark.parametrize("mode", ["level", "indexed", "standardized"])
def test_range_before_source_coverage_returns_empty_not_fabricated_values(mode):
    result = compare(
        datasets=["cpi", "core_cpi"],
        start="1990-01-01",
        end="1995-12-31",
        transformations={"cpi": mode, "core_cpi": mode},
    )
    assert all(s.observations == [] for s in result.series)
    assert result.statistics[0]["observations"] == 0
    assert result.statistics[0]["correlation"] is None


def test_recession_months_are_clipped_to_requested_bounds():
    rows = [("2020-01-01", 0), ("2020-02-01", 1), ("2020-03-01", 1), ("2020-04-01", 0)]
    spans = recession_periods(rows, date(2020, 2, 15), date(2020, 3, 15))
    assert spans[0]["start"] == "2020-02-15"
    assert spans[0]["end"] == "2020-03-15"
    assert spans[0]["original_start"] == "2020-02-01"
    assert spans[0]["original_end"] == "2020-03-31"


def test_unknown_recession_month_is_not_filled():
    rows = [
        ("2020-01-01", 1),
        ("2020-02-01", None),
        ("2020-03-01", 1),
        ("2020-05-01", 1),
    ]
    assert len(recession_periods(rows, date(2020, 1, 1), date(2020, 6, 1))) == 3


@pytest.mark.parametrize(
    "rows",
    [
        [("2020-01-01", 2)],
        [("2020-01-01", 1), ("2020-01-01", 0)],
        [("2020-02-01", 1), ("2020-01-01", 0)],
    ],
)
def test_invalid_context_rejected(rows):
    with pytest.raises(ValueError):
        recession_periods(rows, date(2020, 1, 1), date(2020, 6, 1))


def test_context_outage_is_explicit_and_retains_original_timestamp():
    class Provider:
        fail = False

        def fred_series(self, *args):
            if self.fail:
                raise RuntimeError("offline")
            return [(date(2026, 9, 1), 0)]

    provider = Provider()
    service = RecessionContext(provider, lambda: date(2026, 10, 24), ttl=0)
    first = service.get(date(2020, 1, 1), date(2026, 10, 23))
    provider.fail = True
    stale = service.get(date(2020, 1, 1), date(2026, 10, 23))
    assert stale["status"] == "stale"
    assert stale["retrieved_at"] == first["retrieved_at"]
    with pytest.raises(RuntimeError, match="no shading substituted"):
        RecessionContext(provider, lambda: date(2026, 10, 24)).get(
            date(2020, 1, 1), date(2026, 10, 23)
        )


def test_api_rejects_out_of_range_shifts():
    result = TestClient(v2.app).post(
        "/api/v2/compare",
        json={
            "datasets": ["cpi", "unemployment"],
            "start": "2020-01-01",
            "end": "2025-12-31",
            "lead_lag": {"dataset_id": "cpi", "periods": 13, "unit": "months"},
        },
    )
    assert result.status_code == 422
