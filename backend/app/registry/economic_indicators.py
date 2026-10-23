from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EconomicIndicatorSpec:
    key: str
    economy: str
    name: str
    series_id: str
    frequency: str
    transform: str
    unit: str
    source_label: str
    aliases: tuple[str, ...]
    macro_pillar: str
    why_it_matters: str


INDICATORS: tuple[EconomicIndicatorSpec, ...] = (
    EconomicIndicatorSpec("cpi", "usa", "US headline CPI", "CPIAUCSL", "monthly", "yoy", "percent", "FRED / BLS", ("headline cpi", "cpi", "headline inflation"), "Inflation", "Tracks the broad consumer price level and is central to inflation and Fed-policy analysis."),
    EconomicIndicatorSpec("core_cpi", "usa", "US core CPI", "CPILFESL", "monthly", "yoy", "percent", "FRED / BLS", ("core cpi", "core inflation"), "Inflation", "Helps judge underlying inflation persistence by excluding food and energy."),
    EconomicIndicatorSpec("pce", "usa", "US headline PCE inflation", "PCEPI", "monthly", "yoy", "percent", "FRED / BEA", ("headline pce", "pce inflation", "pce"), "Inflation", "PCE is the Fed's preferred broad inflation framework."),
    EconomicIndicatorSpec("core_pce", "usa", "US core PCE inflation", "PCEPILFE", "monthly", "yoy", "percent", "FRED / BEA", ("core pce inflation", "core pce"), "Inflation", "Core PCE is closely watched for underlying inflation pressure and Fed policy."),
    EconomicIndicatorSpec("unemployment", "usa", "US unemployment rate", "UNRATE", "monthly", "level", "percent", "FRED / BLS", ("unemployment rate", "jobless rate", "unemployment"), "Labour", "Shows labour-market slack and helps assess whether employment conditions are weakening or overheating."),
    EconomicIndicatorSpec("payrolls", "usa", "US nonfarm payrolls", "PAYEMS", "monthly", "change", "thousand_jobs", "FRED / BLS", ("nonfarm payrolls", "non-farm payrolls", "payrolls", "nfp", "jobs added", "job growth"), "Labour", "Monthly payroll growth is a high-frequency gauge of US labour demand."),
    EconomicIndicatorSpec("real_gdp_growth", "usa", "US real GDP growth", "A191RL1Q225SBEA", "quarterly", "level", "percent_saar", "FRED / BEA", ("real gdp growth", "gdp growth", "real gdp", "gdp"), "Growth", "Real GDP growth summarizes the pace of aggregate economic activity."),
    EconomicIndicatorSpec("fed_funds", "usa", "Federal funds rate", "FEDFUNDS", "monthly", "level", "percent", "FRED / Federal Reserve", ("federal funds rate", "fed funds rate", "fed funds", "policy rate", "fed rate"), "Policy", "The policy rate anchors short-term US rates and financial conditions."),
)


class EconomicIndicatorRegistry:
    def __init__(self, specs: tuple[EconomicIndicatorSpec, ...] = INDICATORS) -> None:
        self.specs = specs
        self._by_key = {(s.economy, s.key): s for s in specs}

    def get(self, economy: str, key: str) -> EconomicIndicatorSpec | None:
        return self._by_key.get((economy, key))

    def resolve(self, text: str, economy: str = "usa") -> EconomicIndicatorSpec | None:
        q = " ".join(text.lower().split())
        hits: list[tuple[int, EconomicIndicatorSpec]] = []
        for spec in self.specs:
            if spec.economy != economy:
                continue
            for alias in spec.aliases:
                if alias in q:
                    hits.append((len(alias), spec))
        return max(hits, key=lambda item: item[0])[1] if hits else None
