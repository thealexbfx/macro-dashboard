import json
from dataclasses import replace
from datetime import UTC, date, datetime

import pandas as pd
import pytest

from backend.app.registry.markets import MarketRegistry
from backend.app.v2.definitions import SPECS
from backend.app.v2.integrity import assess_freshness, market_change, validate_frame
from backend.app.v2.main import (
    ComparisonRequest,
    DataService,
    V2PublicProvider,
    compare,
    transform,
)


class Rows:
    def __init__(self, rows):
        self.rows = rows

    def fred_series(self, *args):
        return self.rows

    def market_series(self, *args):
        return self.rows


def service(rows):
    return DataService(Rows(rows), lambda: date(2026, 10, 24), ttl=-1)


def monthly(values, start="2025-01-01"):
    return list(zip(pd.date_range(start, periods=len(values), freq="MS").date, values))


def test_payroll_jobs_scale_and_release_reconciliation():
    d = service(monthly([159015, 159044], "2026-08-01")).get("payrolls")
    assert d.latest_value == 159044
    assert d.headline["value"] == 29000
    assert d.headline["units"] == "Jobs per month"
    assert d.verification["headline_status"] == "Verified against primary source"
    assert (
        d.verification["headline_reconciliation"]["difference_at_release_precision"]
        == 0
    )
    assert d.publication_date == "2026-10-02"


@pytest.mark.parametrize(
    "values,expected", [([100, 101], 1000), ([100, 100], 0), ([100, 99], -1000)]
)
def test_payroll_sign_and_rounding(values, expected):
    assert service(monthly(values)).get("payrolls").headline["value"] == expected


def test_revision_not_silently_forced_to_published_headline():
    s = service(monthly([159015, 159044], "2026-08-01"))
    s.get("payrolls")
    s.provider.rows = monthly([159010, 159044], "2026-08-01")
    d = s.get("payrolls")
    assert d.headline["value"] == 34000 and d.revision_count == 1
    assert d.verification["status"] == "Discrepancy"
    assert (
        d.verification["headline_reconciliation"]["difference_at_release_precision"]
        == 5000
    )


def test_missing_prior_payroll_month_not_bridged():
    d = service([(date(2026, 7, 1), 158882), (date(2026, 9, 1), 159044)]).get(
        "payrolls"
    )
    assert d.headline["value"] is None
    assert d.headline["reference_period"] == "2026-09-01"
    assert any("missing reference" in w for w in d.quality_warnings)


def test_cpi_yoy_uses_calendar_endpoints_not_row_lag():
    rows = monthly([100] + [105] * 11 + [120])
    rows.pop(4)
    frame, _ = validate_frame(rows, SPECS["cpi_nsa"])
    yoy, _ = transform(frame, SPECS["cpi_nsa"], "yoy", date(2025, 1, 1))
    assert yoy.loc["2026-01-01"] == pytest.approx(20)
    mom, _ = transform(frame, SPECS["cpi_nsa"], "mom", date(2025, 1, 1))
    assert pd.isna(mom.loc["2025-06-01"])


def test_sa_and_nsa_headline_definitions_cannot_be_interchanged():
    assert (
        SPECS["cpi"].provider_id == "CPIAUCSL"
        and SPECS["cpi"].recommended_headline_transformation == "mom"
    )
    assert (
        SPECS["cpi_nsa"].provider_id == "CPIAUCNS"
        and SPECS["cpi_nsa"].recommended_headline_transformation == "yoy"
    )
    assert SPECS["core_cpi_nsa"].provider_id == "CPILFENS"
    assert SPECS["cpi_nsa"].seasonal_adjustment == "Not seasonally adjusted"
    assert SPECS["pce"].recommended_headline_transformation == "yoy"


def test_monthly_cpi_percent_and_rate_percentage_points_are_distinct():
    frame, _ = validate_frame(monthly([100, 101]), SPECS["cpi"])
    result, _ = transform(frame, SPECS["cpi"], "mom", date(2025, 1, 1))
    assert result.iloc[-1] == pytest.approx(1)
    frame, _ = validate_frame(monthly([4, 5]), SPECS["unemployment"])
    result, _ = transform(frame, SPECS["unemployment"], "pp", date(2025, 1, 1))
    assert result.iloc[-1] == 1
    with pytest.raises(ValueError):
        transform(frame, SPECS["unemployment"], "percent", date(2025, 1, 1))


def test_gdp_is_already_annualized_growth_not_stale_quarter_start():
    spec = SPECS["real_gdp_growth"]
    assert spec.observation_type == "growth rate"
    assert spec.recommended_headline_transformation == "level"
    assert not assess_freshness(spec, date(2026, 4, 1), date(2026, 10, 24))[0]
    assert assess_freshness(spec, date(2026, 4, 1), date(2026, 11, 4))[0]
    assert "annualized" in spec.name


def test_monthly_average_effective_funds_is_not_target_range():
    assert "Monthly average effective" in SPECS["fed_funds"].name
    assert "not the FOMC target range" in SPECS["fed_funds"].definition


@pytest.mark.parametrize(
    "key,values,unit,expected",
    [
        ("us10y", [5.13, 4.96], "bp", -17),
        ("gold", [4060.4, 4007.9], "%", (4007.9 / 4060.4 - 1) * 100),
        ("wti", [-10, 5], "USD / barrel", 15),
    ],
)
def test_market_changes_and_yield_bp(key, values, unit, expected):
    frame, _ = validate_frame(
        [(date(2026, 10, 21), values[0]), (date(2026, 10, 22), values[1])], SPECS[key]
    )
    *_, movement = market_change(frame, SPECS[key])
    assert movement["unit"] == unit and movement["value"] == pytest.approx(expected)


@pytest.mark.parametrize(
    "rows",
    [
        [("2025-02-01", 2), ("2025-01-01", 1)],
        [("2025-01-01", 1), ("2025-01-01", 2)],
        [("2025-01-01", 1), ("2025-01-15", 2)],
        [("2025-01-01", float("inf"))],
        [("2025-01-01", "invalid")],
    ],
)
def test_bad_order_duplicate_frequency_and_values_rejected(rows):
    with pytest.raises(ValueError):
        validate_frame(rows, SPECS["cpi"])


def test_invalid_definition_units_rejected():
    with pytest.raises(ValueError):
        replace(SPECS["cpi"], units="bananas")
    with pytest.raises(ValueError):
        replace(SPECS["cpi"], allowed_transformations=("jobs",))


def test_shocks_are_flagged_but_not_discarded():
    frame, warnings = validate_frame(monthly([100, 150]), SPECS["payrolls"])
    assert frame.iloc[-1].value == 150 and any("retained" in w for w in warnings)


def test_invalid_refresh_retains_prior_dated_observation_as_stale():
    s = service(monthly([159015, 159044], "2026-08-01"))
    old = s.get("payrolls")
    s.provider.rows = [(date(2026, 9, 1), 159044), (date(2026, 8, 1), 159015)]
    new = s.get("payrolls")
    assert new.status == "stale" and new.retrieved_at == old.retrieved_at
    assert (
        new.latest_observation_date == old.latest_observation_date
        and new.quality_warnings
    )


def test_new_vintage_does_not_inherit_old_primary_verification():
    d = service(monthly([159044, 159050], "2026-09-01")).get("payrolls")
    assert d.verification["status"] == "Unverified" and d.publication_date is None


def test_today_and_investigate_share_exact_transformation():
    s = service(monthly([159015, 159044], "2026-08-01"))
    d = s.get("payrolls")
    r = compare(
        s,
        ComparisonRequest(
            datasets=["payrolls"],
            start="2026-08-01",
            end="2026-10-23",
            transformations={"payrolls": "jobs"},
        ),
    )
    assert r.series[0].observations[-1].value == d.headline["value"]


def test_fred_parser_preserves_explicit_missing_observations():
    p = V2PublicProvider()
    p._get = lambda _: (
        b"observation_date,CPIAUCSL\n2026-07-01,1\n2026-08-01,.\n2026-09-01,2\n"
    )
    assert p.fred_series("CPIAUCSL", date(2026, 1, 1), date(2026, 10, 23))[1][1] is None
    with pytest.raises(ValueError):
        p.fred_series("WRONG", date(2026, 1, 1), date(2026, 10, 23))


def yahoo_payload(symbol="GC=F", currency="USD", kind="FUTURE"):
    stamps = [
        int(datetime(2026, 10, 23, 0, 30, tzinfo=UTC).timestamp()),
        int(datetime(2026, 10, 23, 4, tzinfo=UTC).timestamp()),
    ]
    return {
        "chart": {
            "result": [
                {
                    "meta": {
                        "symbol": symbol,
                        "instrumentType": kind,
                        "currency": currency,
                        "exchangeTimezoneName": "America/New_York",
                    },
                    "timestamp": stamps,
                    "indicators": {"quote": [{"close": [100, 101]}]},
                }
            ]
        }
    }


def test_market_local_date_and_incomplete_session_exclusion():
    p = V2PublicProvider(now_fn=lambda: datetime(2026, 10, 24, 2, tzinfo=UTC))
    p._get = lambda _: json.dumps(yahoo_payload()).encode()
    rows = p.market_series(
        MarketRegistry().get("gold"), date(2026, 10, 1), date(2026, 10, 23)
    )
    assert rows == [
        (date(2026, 10, 22), 100)
    ]  # Oct 23 00:30 UTC is still Oct 22 New York.
    p.now_fn = lambda: datetime(2026, 10, 24, 12, tzinfo=UTC)
    assert (
        len(
            p.market_series(
                MarketRegistry().get("gold"), date(2026, 10, 1), date(2026, 10, 23)
            )
        )
        == 2
    )


@pytest.mark.parametrize(
    "patch", [{"symbol": "WRONG"}, {"currency": "EUR"}, {"kind": "INDEX"}]
)
def test_no_silent_market_instrument_substitution(patch):
    p = V2PublicProvider()
    p._get = lambda _: json.dumps(yahoo_payload(**patch)).encode()
    with pytest.raises(ValueError, match="does not match"):
        p.market_series(
            MarketRegistry().get("gold"), date(2026, 1, 1), date(2026, 10, 23)
        )
