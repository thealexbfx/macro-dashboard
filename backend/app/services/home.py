from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

from backend.app.registry.markets import MarketRegistry
from backend.app.services.direct_answers import PublicTimeSeriesProvider, TimeSeriesProvider
from backend.app.services.macro import MacroService


@dataclass(frozen=True)
class HomeService:
    provider: TimeSeriesProvider
    macro: MacroService
    today_fn: callable

    def __init__(self, provider: TimeSeriesProvider | None = None, macro: MacroService | None = None, today_fn=None):
        object.__setattr__(self, "provider", provider or PublicTimeSeriesProvider(timeout_seconds=4.0))
        object.__setattr__(self, "macro", macro or MacroService())
        object.__setattr__(self, "today_fn", today_fn or date.today)

    def _move(self, key: str) -> dict:
        spec = MarketRegistry().get(key)
        if spec is None:
            raise ValueError(key)
        end = self.today_fn()
        rows = self.provider.market_series(spec, end - timedelta(days=12), end)
        if len(rows) < 2:
            raise RuntimeError(f"Not enough observations for {spec.name}.")
        (prev_date, prev), (as_of, latest) = rows[-2], rows[-1]
        if spec.kind == "yield":
            change = (latest - prev) * 100
            unit = "bp"
        else:
            change = (latest / prev - 1) * 100
            unit = "%"
        return {
            "key": key, "name": spec.name, "value": latest, "kind": spec.kind,
            "change": round(change, 2), "unit": unit, "as_of_date": as_of.isoformat(),
            "previous_date": prev_date.isoformat(), "question": f"Why is {spec.name} moving?",
        }

    def snapshot(self) -> dict:
        keys = ("gold", "us2y", "us30y", "sp500", "dxy")
        moves, errors = [], []
        with ThreadPoolExecutor(max_workers=5) as pool:
            jobs = {pool.submit(self._move, key): key for key in keys}
            for future in as_completed(jobs):
                try:
                    moves.append(future.result())
                except Exception as exc:
                    errors.append({"key": jobs[future], "message": str(exc)})
        order = {key: i for i, key in enumerate(keys)}
        moves.sort(key=lambda item: order[item["key"]])

        macro = None
        try:
            payload = self.macro.get_current_environment("usa")
            macro = {
                "economy": payload.get("economy", "United States"),
                "as_of_date": payload.get("as_of_date"),
                "environment_label": payload.get("environment_label"),
                "activity_label": payload.get("activity_label"),
                "inflation_impulse_label": payload.get("inflation_impulse_label"),
                "financial_impulse_label": payload.get("financial_impulse_label"),
            }
        except Exception as exc:
            errors.append({"key": "usa_macro", "message": str(exc)})

        return {"status": "ok" if (moves or macro) else "unavailable", "moves": moves, "macro": macro, "errors": errors}
