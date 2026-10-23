from datetime import date
from backend.app.services.home import HomeService

class FakeProvider:
    def market_series(self, spec, start, end):
        base = {"gold": 2500, "sp500": 6000, "dxy": 100, "us2y": 4.0, "us30y": 4.5}[spec.key]
        return [(date(2026,8,31), base), (date(2026,9,1), base + (0.05 if spec.kind == "yield" else 10))]
    def fred_series(self, series_id, start, end):
        return []

class FakeMacro:
    def get_current_environment(self, country):
        return {"economy":"United States","as_of_date":"2026-08-01","environment_label":"Resilient expansion","activity_label":"Positive","inflation_impulse_label":"Cooling","financial_impulse_label":"Neutral"}

def test_home_snapshot_is_partial_failure_tolerant():
    data=HomeService(provider=FakeProvider(), macro=FakeMacro(), today_fn=lambda:date(2026,9,2)).snapshot()
    assert data["status"]=="ok"
    assert len(data["moves"])==5
    assert data["moves"][1]["unit"]=="bp"
    assert data["macro"]["environment_label"]=="Resilient expansion"
