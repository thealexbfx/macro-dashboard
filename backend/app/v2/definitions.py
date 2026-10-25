from dataclasses import dataclass, replace

from backend.app.registry.economic_indicators import EconomicIndicatorRegistry
from backend.app.registry.markets import MarketRegistry

CANONICAL_UNITS = {
    "CPIAUCSL": "Index 1982–1984=100",
    "CPILFESL": "Index 1982–1984=100",
    "CPIAUCNS": "Index 1982–1984=100",
    "CPILFENS": "Index 1982–1984=100",
    "PCEPI": "Index 2017=100",
    "PCEPILFE": "Index 2017=100",
    "PAYEMS": "Thousands of persons",
    "UNRATE": "Percent",
    "FEDFUNDS": "Percent",
    "A191RL1Q225SBEA": "Percent change, quarterly annualized",
    "DGS10": "Percent",
    "GC=F": "USD / troy oz",
    "CL=F": "USD / barrel",
    "^GSPC": "index points",
    "DX-Y.NYB": "index points",
}


@dataclass(frozen=True)
class Spec:
    id: str
    name: str
    provider_id: str
    source: str
    category: str
    region: str
    frequency: str
    units: str
    seasonal_adjustment: str | None
    representation: str
    original_transformation: str
    source_url: str
    allowed_transformations: tuple[str, ...]
    provider: str = "fred"
    definition: str = ""
    source_type: str = "official distributor"
    observation_type: str = "level"
    recommended_headline_transformation: str = "level"
    headline_name: str = ""
    primary_source_url: str = ""
    freshness_expectation: str = ""
    known_limitations: tuple[str, ...] = ()

    def __post_init__(self):
        if (
            self.provider_id in CANONICAL_UNITS
            and self.units != CANONICAL_UNITS[self.provider_id]
        ):
            raise ValueError(
                "Units conflict with audited canonical provider definition"
            )
        if self.frequency not in ("daily", "monthly", "quarterly") or not self.units:
            raise ValueError("Invalid units or frequency in dataset definition")
        if "pp" in self.allowed_transformations and not self.units.lower().startswith(
            "percent"
        ):
            raise ValueError(
                "Percentage-point changes require percent-quoted rate units"
            )
        if "jobs" in self.allowed_transformations and (
            self.units != "Thousands of persons" or self.frequency != "monthly"
        ):
            raise ValueError(
                "Jobs conversion requires monthly thousands-of-persons levels"
            )


def registry():
    out = {}
    for s in EconomicIndicatorRegistry().specs:
        index = s.key in ("cpi", "core_cpi", "pce", "core_pce")
        rate = s.key in ("unemployment", "fed_funds", "real_gdp_growth")
        units = {
            "CPIAUCSL": "Index 1982–1984=100",
            "CPILFESL": "Index 1982–1984=100",
            "PCEPI": "Index 2017=100",
            "PCEPILFE": "Index 2017=100",
            "PAYEMS": "Thousands of persons",
            "UNRATE": "Percent",
            "FEDFUNDS": "Percent",
            "A191RL1Q225SBEA": "Percent change, quarterly annualized",
        }[s.series_id]
        allowed = (
            ("level", "pp", "standardized")
            if rate
            else ("level", "percent", "yoy", "mom", "indexed", "standardized")
        )
        out[s.key] = Spec(
            s.key,
            {
                "cpi": "US Consumer Price Index (CPI)",
                "core_cpi": "US core Consumer Price Index",
                "pce": "US PCE price index",
                "core_pce": "US core PCE price index",
            }.get(s.key, s.name),
            s.series_id,
            s.source_label,
            s.macro_pillar,
            "United States",
            s.frequency,
            units,
            "Not seasonally adjusted"
            if s.key == "fed_funds"
            else "Seasonally adjusted annual rate"
            if s.key == "real_gdp_growth"
            else "Seasonally adjusted",
            "rate" if rate else "index" if index else "level",
            "Provider-reported quarterly annualized growth"
            if s.key == "real_gdp_growth"
            else "Original provider level",
            f"https://fred.stlouisfed.org/series/{s.series_id}",
            allowed,
        )
    for key in ("sp500", "gold", "us10y", "dxy", "wti"):
        s = MarketRegistry().get(key)
        yield_ = s.kind == "yield"
        out[key] = Spec(
            key,
            s.name + (" — continuous futures" if key in ("gold", "wti") else ""),
            s.provider_id,
            "FRED / Federal Reserve" if yield_ else "Yahoo Finance",
            "Rates"
            if yield_
            else "Commodities"
            if key in ("gold", "wti")
            else "Equities"
            if key == "sp500"
            else "FX",
            "United States" if key in ("sp500", "us10y", "dxy") else "Global",
            "daily",
            "Percent" if yield_ else s.unit,
            "Not seasonally adjusted" if yield_ else None,
            "rate" if yield_ else "signed_flow" if key == "wti" else "price",
            "Daily yield"
            if yield_
            else "Unadjusted close; continuous futures roll effects"
            if key in ("gold", "wti")
            else "Unadjusted price index close",
            f"https://fred.stlouisfed.org/series/{s.provider_id}"
            if yield_
            else f"https://finance.yahoo.com/quote/{s.provider_id}/history/",
            ("level", "pp", "standardized")
            if yield_
            else ("level", "standardized")
            if key == "wti"
            else ("level", "percent", "indexed", "standardized"),
        )
    return enrich(out)


def enrich(out):
    inflation = "https://www.bls.gov/news.release/cpi.htm"
    labour = "https://www.bls.gov/news.release/empsit.nr0.htm"
    pce = "https://www.bea.gov/data/personal-consumption-expenditures-price-index"
    gdp = "https://www.bea.gov/data/gdp/gross-domestic-product"
    fed = "https://www.federalreserve.gov/releases/h15/"
    descriptions = {
        "cpi": (
            "US CPI price index (SA)",
            "All-items CPI-U, seasonally adjusted; monthly percent changes are SA; annual SA changes are not the official NSA headline.",
            "mom",
            "US CPI monthly inflation (SA)",
            inflation,
        ),
        "core_cpi": (
            "US core CPI price index (SA)",
            "CPI-U excluding food and energy, seasonally adjusted.",
            "mom",
            "US core CPI monthly inflation (SA)",
            inflation,
        ),
        "pce": (
            "US PCE price index (SA)",
            "BEA chain-type price index for personal consumption expenditures; annual inflation is the 12-month index change.",
            "yoy",
            "US PCE annual inflation (SA)",
            pce,
        ),
        "core_pce": (
            "US core PCE price index (SA)",
            "BEA chain-type PCE prices excluding food and energy.",
            "yoy",
            "US core PCE annual inflation (SA)",
            pce,
        ),
        "unemployment": (
            "US unemployment rate (U-3, SA)",
            "Civilian unemployed as a percent of the civilian labour force, age 16+, seasonally adjusted.",
            "level",
            "US unemployment rate (U-3)",
            labour,
        ),
        "payrolls": (
            "US total nonfarm payroll employment (level, SA)",
            "CES establishment-survey total nonfarm employment level in thousands of persons; monthly jobs change is adjacent-month difference times 1,000.",
            "jobs",
            "US nonfarm payrolls: monthly jobs change",
            labour,
        ),
        "fed_funds": (
            "Monthly average effective federal funds rate",
            "Monthly average of daily effective federal funds rates, percent, NSA. Not the daily effective rate and not the FOMC target range.",
            "level",
            "Monthly average effective federal funds rate",
            fed,
        ),
        "real_gdp_growth": (
            "US real GDP growth (q/q annualized)",
            "BEA real GDP percent change from preceding quarter, seasonally adjusted at annual rates. Already a growth rate, not a GDP level or YoY change.",
            "level",
            "US real GDP growth (q/q annualized)",
            gdp,
        ),
        "us10y": (
            "US 10Y Treasury constant-maturity yield",
            "H.15 nominal 10-year constant-maturity Treasury yield quoted in percent per annum, not a bond price or total return.",
            "level",
            "US 10Y Treasury yield",
            fed,
        ),
        "sp500": (
            "S&P 500 price index",
            "S&P 500 price index closing value; excludes dividends and is not itself a tradeable security.",
            "level",
            "S&P 500",
            "https://www.spglobal.com/spdji/en/indices/equity/sp-500/",
        ),
        "gold": (
            "Gold — continuous futures",
            "Yahoo GC=F continuous/front-contract history, USD per troy ounce. Neither spot gold nor a verified exchange settlement.",
            "level",
            "Gold futures",
            "https://www.cmegroup.com/markets/metals/precious/gold.contractSpecs.html",
        ),
        "wti": (
            "WTI crude oil — continuous futures",
            "Yahoo CL=F continuous/front-contract history, USD per barrel. Neither spot WTI nor a verified exchange settlement. Signed historical prices are valid.",
            "level",
            "WTI futures",
            "https://www.cmegroup.com/markets/energy/crude-oil/light-sweet-crude.contractSpecs.html",
        ),
        "dxy": (
            "ICE US Dollar Index (price index)",
            "Yahoo DX-Y.NYB index history. Not the dollar-index futures contract, an FX pair or a tradeable total-return product.",
            "level",
            "US Dollar Index",
            "https://www.ice.com/forex/usdx",
        ),
    }
    for key, spec in list(out.items()):
        name, definition, headline, title, primary = descriptions[key]
        provider = "fred" if spec.source.startswith("FRED") else "yahoo"
        limits = (
            [
                "Latest revised observations; publication dates and real-time vintages are not implied by reference dates."
            ]
            if provider == "fred"
            else [
                "Yahoo historical unadjusted closes are secondary market data; independent exchange/index closing-price verification may be unavailable.",
                "Quote timestamps are distinct from daily bar/session labels. No silent instrument substitution.",
            ]
        )
        if key in ("gold", "wti"):
            limits += [
                "Continuous-series roll effects; contract mapping for each historical bar is not independently verified. Close is not asserted to be settlement."
            ]
        if key == "fed_funds":
            limits += [
                "Current FOMC policy stance must not be inferred from this monthly average."
            ]
        out[key] = replace(
            spec,
            name=name,
            definition=definition,
            provider=provider,
            source_type="official data via FRED"
            if provider == "fred"
            else "secondary market-data-derived",
            observation_type="growth rate"
            if key == "real_gdp_growth"
            else "yield"
            if key == "us10y"
            else "rate"
            if key in ("unemployment", "fed_funds")
            else "index"
            if key in ("cpi", "core_cpi", "pce", "core_pce", "sp500", "dxy")
            else "price"
            if key in ("gold", "wti")
            else "level",
            recommended_headline_transformation=headline,
            headline_name=title,
            primary_source_url=primary,
            freshness_expectation="Scheduled release date when audited; otherwise next reference-period end plus publication allowance."
            if spec.frequency != "daily"
            else "Completed provider-local daily bars; business-day publication allowance, no assumed exchange calendar.",
            known_limitations=tuple(limits),
            allowed_transformations=spec.allowed_transformations + ("jobs",)
            if key == "payrolls"
            else spec.allowed_transformations,
            representation="growth_rate"
            if key == "real_gdp_growth"
            else spec.representation,
        )
    for key, provider_id, name in [
        ("cpi_nsa", "CPIAUCNS", "US CPI price index (NSA)"),
        ("core_cpi_nsa", "CPILFENS", "US core CPI price index (NSA)"),
    ]:
        base = out["cpi" if key == "cpi_nsa" else "core_cpi"]
        out[key] = replace(
            base,
            id=key,
            name=name,
            provider_id=provider_id,
            seasonal_adjustment="Not seasonally adjusted",
            source_url=f"https://fred.stlouisfed.org/series/{provider_id}",
            definition="BLS all-items CPI-U, not seasonally adjusted; official annual headline uses comparable month one year earlier."
            if key == "cpi_nsa"
            else "BLS CPI-U excluding food and energy, NSA; official annual core inflation uses comparable month one year earlier.",
            recommended_headline_transformation="yoy",
            headline_name="US CPI annual inflation (NSA)"
            if key == "cpi_nsa"
            else "US core CPI annual inflation (NSA)",
        )
    return out


SPECS = registry()
