from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any, Callable

import pandas as pd

from backend.app.infrastructure.cache import load_macro_cache
from backend.app.registry.economic_indicators import EconomicIndicatorRegistry
from backend.app.registry.markets import MarketRegistry, MarketSpec
from backend.app.schemas.customer_answer import (
    AnswerBlock,
    CustomerAnswer,
    ExperienceLink,
)
from backend.app.services.direct_answers import (
    PublicTimeSeriesProvider,
    TimeSeriesProvider,
)
from macro_engine.research.analytics import (
    LIMITATION,
    SeriesMetadata,
    analyze,
    relationship,
)

EXTRA_SERIES: dict[str, MarketSpec] = {
    "us10y_real": MarketSpec("us10y_real", "US 10Y real yield", "fred", "DFII10", "yield", ("real yields", "real yield", "10y real yield", "10 year real yield")),
    "us5y_breakeven": MarketSpec("us5y_breakeven", "US 5Y breakeven inflation", "fred", "T5YIE", "yield", ("5y breakeven", "5 year breakeven")),
    "us10y_breakeven": MarketSpec("us10y_breakeven", "US 10Y breakeven inflation", "fred", "T10YIE", "yield", ("10y breakeven", "10 year breakeven", "inflation expectations")),
}


class RelationshipSeriesRegistry:
    def __init__(self) -> None:
        base = MarketRegistry()
        self._specs = {s.key: s for s in base.specs}
        self._specs.update(EXTRA_SERIES)
        self.economic = {spec.key: spec for spec in EconomicIndicatorRegistry().specs}
        for spec in self.economic.values():
            self._specs[spec.key] = MarketSpec(spec.key, spec.name, "fred", spec.series_id, "economic", spec.aliases)

    def get(self, key: str) -> MarketSpec | None:
        return self._specs.get(key)

    def resolve_all(self, text: str) -> tuple[MarketSpec, ...]:
        q = " ".join(text.lower().split())
        hits: list[tuple[int, MarketSpec]] = []
        for spec in self._specs.values():
            best = max((len(a) for a in spec.aliases if a in q), default=0)
            if best:
                hits.append((best, spec))
        hits.sort(key=lambda x: -x[0])
        out, seen = [], set()
        for _, spec in hits:
            if spec.key not in seen:
                out.append(spec); seen.add(spec.key)
        return tuple(out)


class MacroRegimeHistoryProvider:
    CACHE_NAMES = {"usa": "usa_environment_history", "uk": "uk_environment_history", "euro": "euro_environment_history", "japan": "japan_environment_history"}

    def __init__(self, cache_loader: Callable[[str], Any] = load_macro_cache) -> None:
        self._loader = cache_loader

    def snapshots(self, economy: str = "usa") -> tuple[Any, ...]:
        name = self.CACHE_NAMES.get(economy)
        if not name:
            return ()
        try:
            cached = self._loader(name)
            history = getattr(cached, "history", None) or cached
            snaps = tuple(getattr(history, "snapshots", ()) or ())
            return tuple(sorted(snaps, key=lambda x: x.as_of_date))
        except Exception:
            return ()


@dataclass
class HistoricalRelationshipService:
    provider: TimeSeriesProvider
    regimes: MacroRegimeHistoryProvider
    today_fn: Callable[[], date]
    registry: RelationshipSeriesRegistry

    def __init__(self, provider: TimeSeriesProvider | None = None, regimes: MacroRegimeHistoryProvider | None = None, today_fn=None) -> None:
        self.provider = provider or PublicTimeSeriesProvider()
        self.regimes = regimes or MacroRegimeHistoryProvider()
        self.today_fn = today_fn or date.today
        self.registry = RelationshipSeriesRegistry()

    @staticmethod
    def _days(timeframe: str | None) -> int:
        return {"6_months": 210, "1_year": 390, "3_years": 1120, "5_years": 1850, "10_years": 3700}.get(timeframe or "", 1850)

    def _rows(self, spec: MarketSpec, start: date, end: date):
        return self.provider.fred_series(spec.provider_id, start, end) if spec.provider == "fred" else self.provider.market_series(spec, start, end)

    @staticmethod
    def _transform(rows, kind: str) -> pd.Series:
        s = pd.Series({pd.Timestamp(d): float(v) for d, v in rows}).sort_index()
        if kind == "yield":
            return s.diff() * 100.0
        if (s.dropna() <= 0).any():
            raise ValueError("Percentage returns require positive prices; select absolute changes for signed series.")
        return s.pct_change(fill_method=None) * 100.0

    @staticmethod
    def _label(corr: float) -> tuple[str, str]:
        direction = "inverse" if corr < -0.15 else "positive" if corr > 0.15 else "weak/mixed"
        strength = "strong" if abs(corr) >= .6 else "moderate" if abs(corr) >= .35 else "mild" if abs(corr) >= .15 else "weak"
        return strength, direction

    def _regime_context(self, frame: pd.DataFrame, economy: str) -> dict[str, Any] | None:
        snaps = self.regimes.snapshots(economy)
        rows = []
        for s in snaps:
            try:
                rows.append({"regime_date": pd.Timestamp(s.as_of_date), "environment": str(s.environment_label), "activity": str(s.activity_label), "inflation": str(s.inflation_impulse_label), "financial": str(s.financial_impulse_label)})
            except Exception:
                continue
        if not rows:
            return None
        regimes = pd.DataFrame(rows).drop_duplicates("regime_date").sort_values("regime_date")
        regimes = regimes[regimes.regime_date <= frame.index.max()]
        if regimes.empty:
            return None
        if frame.index.max() - regimes.regime_date.max() > pd.Timedelta(days=100):
            return None
        obs = frame.reset_index().rename(columns={frame.index.name or "index": "market_date"}).sort_values("market_date")
        obs["market_date"] = obs.market_date.astype("datetime64[ns]")
        regimes["regime_date"] = regimes.regime_date.astype("datetime64[ns]")
        tagged = pd.merge_asof(obs, regimes, left_on="market_date", right_on="regime_date", direction="backward", tolerance=pd.Timedelta(days=100)).dropna(subset=["environment"])
        if len(tagged) < 30:
            return None

        def groups(field: str):
            out = []
            for label, group in tagged.groupby(field, sort=False):
                if len(group) < 30:
                    continue
                corr = group.target.corr(group.driver)
                if pd.isna(corr):
                    continue
                strength, direction = self._label(float(corr))
                out.append({"label": str(label), "observations": int(len(group)), "start": str(group.market_date.min().date()), "end": str(group.market_date.max().date()), "correlation": round(float(corr), 4), "strength": strength, "direction": direction})
            return sorted(out, key=lambda x: x["observations"], reverse=True)

        current = regimes.iloc[-1]
        by_env = groups("environment")
        current_stats = next((x for x in by_env if x["label"] == str(current.environment)), None)
        return {
            "method": "backward as-of join to MacroLens historical regimes; max age 100 days",
            "definitions": "Existing Growth/Labour activity, Inflation, and Policy/Liquidity financial impulses use +/-0.15 direction thresholds; classify_macro_environment in macro_engine.engine.environment_engine defines each named environment.",
            "limitation": "Reconstructed regime inputs are not verified historical vintages; descriptive evidence only.",
            "current_environment": {"label": str(current.environment), "activity": str(current.activity), "inflation": str(current.inflation), "financial": str(current.financial), "relationship": current_stats},
            "by_environment": by_env,
            "by_dimension": {"activity": groups("activity"), "inflation": groups("inflation"), "financial": groups("financial")},
        }

    def analyze(self, target: str, driver: str, timeframe: str | None = None, economy: str = "usa") -> CustomerAnswer:
        a, b = self.registry.get(target), self.registry.get(driver)
        if not a or not b or target == driver:
            raise ValueError("Choose two different supported market series.")
        end = self.today_fn(); start = end - timedelta(days=self._days(timeframe))
        def prepared(spec):
            economic = self.registry.economic.get(spec.key)
            fetch_start = start - timedelta(days=400) if economic and economic.transform == "yoy" else start
            raw = pd.DataFrame(self._rows(spec, fetch_start, end), columns=["date", "value"])
            if raw.empty:
                raise RuntimeError("No source observations returned.")
            if economic:
                raw["date"] = pd.to_datetime(raw.date)
                alias = "Q" if economic.frequency == "quarterly" else "M"
                indexed = raw.set_index(raw.date.dt.to_period(alias)).value
                if indexed.index.duplicated().any():
                    raise ValueError("Economic provider returned duplicate periods; select vintages explicitly.")
                indexed = indexed.reindex(pd.period_range(indexed.index.min(), indexed.index.max(), freq=alias))
                if economic.transform == "yoy":
                    indexed = indexed.pct_change(4 if alias == "Q" else 12, fill_method=None) * 100
                elif economic.transform == "change":
                    indexed = indexed.diff()
                raw = pd.DataFrame({"date": indexed.index.to_timestamp(), "value": indexed.values})
                rep = "growth_rate" if economic.transform == "yoy" or economic.unit == "percent_saar" else "rate" if economic.unit == "percent" else "signed_flow"
                meta = SeriesMetadata(units="%" if rep in {"rate", "growth_rate"} else economic.unit,
                                      frequency=economic.frequency, representation=rep, source=economic.source_label)
            else:
                meta = spec.research_metadata
            raw["date"] = pd.to_datetime(raw.date)
            raw = raw[(raw.date >= pd.Timestamp(start)) & (raw.date <= pd.Timestamp(end))]
            return raw, meta
        raw_a, meta_a = prepared(a)
        raw_b, meta_b = prepared(b)
        aligned, methodology = analyze(raw_a, raw_b, meta_a, meta_b, "Changes")
        stability = relationship(aligned, window=30, minimum=12)
        frame = aligned.rename(columns={"left": "target", "right": "driver"}).dropna()
        frame.index.name = "market_date"
        if len(frame) < 30:
            raise RuntimeError("Not enough overlapping observations for a reliable relationship test.")
        corr = float(frame.target.corr(frame.driver))
        if pd.isna(corr):
            raise RuntimeError("Correlation is undefined for constant or insufficient inputs.")
        strength, direction = self._label(corr)
        down = frame[frame.driver < 0].target; up = frame[frame.driver > 0].target
        regime = self._regime_context(frame, economy)
        evidence = {
            "target": target, "driver": driver, "target_name": a.name, "driver_name": b.name,
            "timeframe": timeframe or "5_years", "observations": int(len(frame)), "correlation": round(corr, 4),
            "strength": strength, "direction": direction,
            "when_driver_falls": {"observations": int(len(down)), "target_average": round(float(down.mean()), 4) if len(down) else None, "target_positive_share": round(float((down > 0).mean()), 4) if len(down) else None},
            "when_driver_rises": {"observations": int(len(up)), "target_average": round(float(up.mean()), 4) if len(up) else None, "target_positive_share": round(float((up > 0).mean()), 4) if len(up) else None},
            "regime_context": regime,
            "methodology": methodology,
            "lead_lag": stability["lead_lag"],
            "stability": {**{key: stability[key] for key in ("full_sample", "first_half", "second_half", "window")},
                          "rolling": [{"date": str(d.date()), "correlation": float(v)} for d, v in stability["rolling"].dropna().items()]},
        }
        sentence = f"Across {len(frame):,} overlapping {methodology['frequency']} observations, {a.name} and {b.name} show a {strength} {direction} relationship (correlation {corr:+.2f})."
        if regime and regime["current_environment"].get("relationship"):
            cr = regime["current_environment"]["relationship"]
            sentence += f" In the current MacroLens environment ({regime['current_environment']['label']}), the historical correlation was {cr['correlation']:+.2f} across {cr['observations']} observations."
        return CustomerAnswer(
            status="ok", answer=sentence, confidence="moderate" if abs(corr) >= .15 else "low",
            blocks=(AnswerBlock("historical_relationship", f"{a.name} vs {b.name}", evidence),),
            limitations=("Historical association is not proof of causation.", LIMITATION,
                         "Regime labels use backward as-of joins but reconstructed input vintages are unverified.",
                         "Regime-conditioned results require at least 30 tagged observations.",
                         *stability["limitations"]),
            sources=tuple({"name": "FRED" if s.provider == "fred" else "Yahoo Finance", "series": s.provider_id} for s in (a,b)),
            follow_up_questions=(f"When does the {a.name} / {b.name} relationship break down?", "How does this relationship change across MacroLens inflation regimes?"),
            explore=(ExperienceLink("Compare across MacroLens regimes", "See how this relationship changes with Growth, Inflation and Financial conditions.", f"/research/relationships?target={target}&driver={driver}", "Explore regimes"),),
        )
