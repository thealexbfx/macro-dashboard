from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from io import StringIO
from typing import Protocol
from urllib.parse import quote
import requests

from backend.app.registry.economic_indicators import EconomicIndicatorRegistry
from backend.app.registry.markets import MarketRegistry, MarketSpec
from backend.app.schemas.customer_answer import AnswerBlock, CustomerAnswer, ExperienceLink


class TimeSeriesProvider(Protocol):
    def market_series(self, spec: MarketSpec, start: date, end: date) -> list[tuple[date, float]]: ...
    def fred_series(self, series_id: str, start: date, end: date) -> list[tuple[date, float]]: ...


class PublicTimeSeriesProvider:
    """Small production provider boundary with no Streamlit dependency."""

    def __init__(self, timeout_seconds: float = 8.0) -> None:
        self.timeout_seconds = timeout_seconds

    def _get(self, url: str) -> bytes:
        response = requests.get(url, headers={"User-Agent": "MacroLensResearch/1.0"}, timeout=self.timeout_seconds)
        response.raise_for_status()
        return response.content

    def market_series(self, spec: MarketSpec, start: date, end: date) -> list[tuple[date, float]]:
        if spec.provider == "fred":
            return self.fred_series(spec.provider_id, start, end)
        p1 = int(datetime.combine(start, datetime.min.time(), tzinfo=timezone.utc).timestamp())
        p2 = int(datetime.combine(end + timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc).timestamp())
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{quote(spec.provider_id, safe='')}?period1={p1}&period2={p2}&interval=1d&events=history"
        raw = json.loads(self._get(url).decode("utf-8"))
        result = (raw.get("chart", {}).get("result") or [None])[0]
        if not result:
            raise RuntimeError(f"No market data returned for {spec.name}.")
        timestamps = result.get("timestamp") or []
        closes = ((result.get("indicators") or {}).get("quote") or [{}])[0].get("close") or []
        rows: list[tuple[date, float]] = []
        for stamp, close in zip(timestamps, closes):
            if close is not None:
                rows.append((datetime.fromtimestamp(stamp, tz=timezone.utc).date(), float(close)))
        if not rows:
            raise RuntimeError(f"No usable market observations returned for {spec.name}.")
        return rows

    def fred_series(self, series_id: str, start: date, end: date) -> list[tuple[date, float]]:
        url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={quote(series_id)}&cosd={start.isoformat()}&coed={end.isoformat()}"
        text = self._get(url).decode("utf-8")
        reader = csv.DictReader(StringIO(text))
        rows: list[tuple[date, float]] = []
        for row in reader:
            raw_date = row.get("DATE") or row.get("observation_date")
            raw_value = row.get(series_id)
            if not raw_date or not raw_value or raw_value == ".":
                continue
            try:
                rows.append((date.fromisoformat(raw_date), float(raw_value)))
            except ValueError:
                continue
        if not rows:
            raise RuntimeError(f"No usable FRED observations returned for {series_id}.")
        return rows


@dataclass(frozen=True)
class DirectAnswerService:
    provider: TimeSeriesProvider
    markets: MarketRegistry
    indicators: EconomicIndicatorRegistry
    today_fn: callable

    def __init__(self, provider: TimeSeriesProvider | None = None, today_fn=None) -> None:
        object.__setattr__(self, "provider", provider or PublicTimeSeriesProvider())
        object.__setattr__(self, "markets", MarketRegistry())
        object.__setattr__(self, "indicators", EconomicIndicatorRegistry())
        object.__setattr__(self, "today_fn", today_fn or date.today)

    @staticmethod
    def _fmt_market(value: float, kind: str) -> str:
        return f"{value:.2f}%" if kind == "yield" else f"{value:,.2f}"

    def market_lookup(self, asset: str) -> CustomerAnswer:
        spec = self.markets.get(asset)
        if spec is None:
            raise ValueError(f"Unknown market '{asset}'.")
        end = self.today_fn()
        rows = self.provider.market_series(spec, end - timedelta(days=14), end)
        as_of, latest = rows[-1]
        source = "FRED" if spec.provider == "fred" else "Yahoo Finance"
        return CustomerAnswer(
            status="ok",
            answer=f"{spec.name} is {self._fmt_market(latest, spec.kind)} as of {as_of.isoformat()}.",
            blocks=(AnswerBlock("market_metric", spec.name, {"asset": spec.key, "value": latest, "kind": spec.kind, "as_of_date": as_of.isoformat()}),),
            limitations=("This is a direct market-data lookup, not a causal interpretation of the move.",),
            sources=({"name": source, "series": spec.provider_id},),
            follow_up_questions=(f"How much has {spec.name} moved over six months?", f"Why is {spec.name} moving?"),
            explore=(ExperienceLink(f"Explore {spec.name}", "Open the relevant MacroLens market evidence after getting the answer here.", f"/markets/{spec.key}", "Explore market"),),
        )

    @staticmethod
    def _start_for_timeframe(end: date, timeframe: str | None) -> date:
        if timeframe == "1_week": return end - timedelta(days=10)
        if timeframe == "1_month": return end - timedelta(days=40)
        if timeframe == "3_months": return end - timedelta(days=110)
        if timeframe == "6_months": return end - timedelta(days=210)
        if timeframe == "1_year": return end - timedelta(days=380)
        if timeframe == "ytd": return date(end.year, 1, 1) - timedelta(days=7)
        return end - timedelta(days=210)

    def market_calculation(self, asset: str, timeframe: str | None) -> CustomerAnswer:
        spec = self.markets.get(asset)
        if spec is None:
            raise ValueError(f"Unknown market '{asset}'.")
        end = self.today_fn()
        rows = self.provider.market_series(spec, self._start_for_timeframe(end, timeframe), end)
        if len(rows) < 2:
            raise RuntimeError(f"Not enough observations to calculate {spec.name} performance.")
        start_date, start_value = rows[0]
        end_date, end_value = rows[-1]
        if spec.kind == "yield":
            change_bps = (end_value - start_value) * 100.0
            answer = f"{spec.name} changed {change_bps:+.0f} bp from {start_date.isoformat()} to {end_date.isoformat()} ({start_value:.2f}% to {end_value:.2f}%)."
            metric = {"change_bps": change_bps}
        else:
            pct = (end_value / start_value - 1.0) * 100.0
            answer = f"{spec.name} moved {pct:+.1f}% from {start_date.isoformat()} to {end_date.isoformat()} ({start_value:,.2f} to {end_value:,.2f})."
            metric = {"return_pct": pct}
        return CustomerAnswer(
            status="ok",
            answer=answer,
            blocks=(AnswerBlock("period_change", f"{spec.name} performance", {"asset": spec.key, "timeframe": timeframe, "start_date": start_date.isoformat(), "end_date": end_date.isoformat(), "start_value": start_value, "end_value": end_value, **metric}),),
            limitations=("This calculation describes what happened; it does not identify why it happened.",),
            sources=({"name": "FRED" if spec.provider == "fred" else "Yahoo Finance", "series": spec.provider_id},),
            follow_up_questions=(f"Why did {spec.name} move over this period?",),
            explore=(ExperienceLink(f"Explore {spec.name} history", "Inspect the underlying series and related MacroLens evidence.", f"/markets/{spec.key}?view=history", "Explore history"),),
        )

    def economic_lookup(self, economy: str, indicator_key: str) -> CustomerAnswer:
        spec = self.indicators.get(economy, indicator_key)
        if spec is None:
            raise ValueError(f"Indicator '{indicator_key}' is not registered for {economy}.")
        end = self.today_fn()
        lookback = 800 if spec.frequency == "quarterly" else 550 if spec.transform == "yoy" else 220
        rows = self.provider.fred_series(spec.series_id, end - timedelta(days=lookback), end)
        rows = sorted(rows)
        minimum = 14 if spec.transform == "yoy" else 3 if spec.transform == "change" else 2
        if len(rows) < minimum:
            raise RuntimeError(f"Not enough observations for {spec.name}.")
        latest_date, latest_raw = rows[-1]
        previous_raw = rows[-2][1]
        if spec.transform == "yoy":
            value = (latest_raw / rows[-13][1] - 1.0) * 100.0
            previous = (previous_raw / rows[-14][1] - 1.0) * 100.0
        elif spec.transform == "change":
            value = latest_raw - previous_raw
            previous = rows[-2][1] - rows[-3][1]
        else:
            value, previous = latest_raw, previous_raw
        fmt = (lambda v: f"{v:+,.0f}k") if spec.unit == "thousand_jobs" else (lambda v: f"{v:.1f}%")
        direction = "higher" if value > previous else "lower" if value < previous else "unchanged"
        answer = f"Latest {spec.name} is {fmt(value)} for {latest_date.strftime('%B %Y')}. The previous reading was {fmt(previous)}, so the latest reading is {direction}."
        return CustomerAnswer(
            status="ok",
            answer=answer,
            blocks=(AnswerBlock("economic_indicator", spec.name, {"indicator": spec.key, "economy": spec.economy, "value": value, "previous_value": previous, "direction_vs_previous": direction, "period": latest_date.isoformat(), "unit": spec.unit, "macro_pillar": spec.macro_pillar, "why_it_matters": spec.why_it_matters}),),
            limitations=("This is a direct data answer. MacroLens has not inferred a market impact or causal explanation from this reading alone.",),
            sources=({"name": spec.source_label, "series": spec.series_id},),
            follow_up_questions=(f"What is driving {spec.macro_pillar.lower()} now?", "What does this mean for Fed policy?" if spec.macro_pillar in {"Inflation", "Labour", "Growth"} else "What has changed recently?"),
            explore=(ExperienceLink(f"Explore US {spec.macro_pillar}", spec.why_it_matters, f"/macro/usa?pillar={spec.macro_pillar.lower()}", "Explore MacroLens evidence"),),
        )
