"""Public-series definitions checked against FRED metadata on 2026-10-25.

Distributor update times are not claimed as primary publication timestamps.
"""

from __future__ import annotations

# key, FRED id, name, category, frequency, units, adjustment, representation,
# description, recommended transform, native weekday (None when historical labels vary).
ROWS = [
    (
        "initial_claims",
        "ICSA",
        "Initial unemployment claims",
        "Labour",
        "weekly",
        "Number of claims",
        "Seasonally adjusted",
        "level",
        "New unemployment-insurance claims, seasonally adjusted, week ending Saturday; not continuing claims.",
        "percent",
        5,
    ),
    (
        "job_openings",
        "JTSJOL",
        "Job openings, total nonfarm",
        "Labour",
        "monthly",
        "Thousands of job openings",
        "Seasonally adjusted",
        "level",
        "JOLTS total nonfarm job openings, level in thousands, seasonally adjusted; distinct from payroll job creation.",
        "mom",
        None,
    ),
    (
        "participation",
        "CIVPART",
        "Labour-force participation rate",
        "Labour",
        "monthly",
        "Percent",
        "Seasonally adjusted",
        "rate",
        "Civilian labour force as a share of civilian noninstitutional population aged 16+, seasonally adjusted.",
        "level",
        None,
    ),
    (
        "hourly_earnings",
        "CES0500000003",
        "Average hourly earnings, total private",
        "Wages",
        "monthly",
        "Dollars per hour",
        "Seasonally adjusted",
        "level",
        "Average nominal hourly earnings of all private employees; excludes benefits and is not inflation-adjusted or a fixed-composition wage index.",
        "yoy",
        None,
    ),
    (
        "breakeven_5y",
        "T5YIE",
        "5-year breakeven inflation rate",
        "Inflation expectations",
        "daily",
        "Percent",
        "Not seasonally adjusted",
        "rate",
        "Nominal-minus-inflation-indexed 5-year Treasury yield spread. Includes inflation risk and liquidity premia; not pure expected inflation.",
        "level",
        None,
    ),
    (
        "retail_sales",
        "RSAFS",
        "Retail and food-services sales",
        "Consumer",
        "monthly",
        "Millions of dollars",
        "Seasonally adjusted",
        "level",
        "Advance nominal retail and food-services sales, seasonally adjusted, not price-adjusted consumption.",
        "mom",
        None,
    ),
    (
        "real_consumption",
        "PCEC96",
        "Real personal consumption expenditures",
        "Consumer",
        "monthly",
        "Billions of chained 2017 dollars",
        "Seasonally adjusted annual rate",
        "level",
        "Real personal consumption expenditures, chained 2017 dollars at seasonally adjusted annual rate; monthly growth is not annualized.",
        "mom",
        None,
    ),
    (
        "consumer_sentiment",
        "UMCSENT",
        "University of Michigan consumer sentiment",
        "Consumer",
        "monthly",
        "Index 1966:Q1=100",
        "Not seasonally adjusted",
        "index",
        "University of Michigan survey sentiment index; FRED availability may lag the survey release and licensing applies.",
        "percent",
        None,
    ),
    (
        "housing_starts",
        "HOUST",
        "Housing starts, total units",
        "Housing",
        "monthly",
        "Thousands of units",
        "Seasonally adjusted annual rate",
        "level",
        "New privately-owned housing units started, thousands at SAAR; not the count physically started during that month.",
        "mom",
        None,
    ),
    (
        "building_permits",
        "PERMIT",
        "Building permits, total units",
        "Housing",
        "monthly",
        "Thousands of units",
        "Seasonally adjusted annual rate",
        "level",
        "New privately-owned housing units authorized in permit-issuing places, thousands at SAAR; not completed construction.",
        "mom",
        None,
    ),
    (
        "mortgage_30y",
        "MORTGAGE30US",
        "30-year fixed mortgage rate",
        "Housing",
        "weekly",
        "Percent",
        "Not seasonally adjusted",
        "rate",
        "Freddie Mac PMMS 30-year fixed mortgage average; weekly provider labels, usually Thursday with historical Friday labels. Methodology changed in November 2022; not an individual borrower quote.",
        "level",
        None,
    ),
    (
        "industrial_production",
        "INDPRO",
        "Industrial production, total index",
        "Activity",
        "monthly",
        "Index 2017=100 (industrial output)",
        "Seasonally adjusted",
        "index",
        "Federal Reserve total industrial production index, 2017=100, seasonally adjusted; distinct from price indexes using the same base year.",
        "mom",
        None,
    ),
    (
        "yield_curve",
        "T10Y2Y",
        "10-year minus 2-year Treasury spread",
        "Financial conditions",
        "daily",
        "Percent",
        "Not seasonally adjusted",
        "rate",
        "10-year minus 2-year nominal constant-maturity Treasury yields, quoted in percentage points; can be negative. Not a recession forecast.",
        "level",
        None,
    ),
    (
        "high_yield_spread",
        "BAMLH0A0HYM2",
        "US high-yield credit spread",
        "Financial conditions",
        "daily",
        "Percent",
        "Not seasonally adjusted",
        "rate",
        "ICE BofA US high-yield option-adjusted spread over a spot Treasury curve, percent. Not default probability; FRED currently provides about three years of history and ICE licensing applies.",
        "level",
        None,
    ),
    (
        "investment_grade_spread",
        "BAMLC0A0CM",
        "US investment-grade corporate spread",
        "Financial conditions",
        "daily",
        "Percent",
        "Not seasonally adjusted",
        "rate",
        "ICE BofA US corporate index option-adjusted spread, percent; investment-grade corporate universe. Not a credit default probability; limited FRED history and ICE licensing apply.",
        "level",
        None,
    ),
]
WEEKDAYS = {r[0]: r[-1] for r in ROWS}
# Only prospective distributor schedule hints. No primary publication dates inferred.
SCHEDULES = {
    "initial_claims": ("2026-10-17", "2026-10-29"),
    "job_openings": ("2026-08-01", "2026-11-03"),
    "participation": ("2026-09-01", "2026-11-06"),
    "hourly_earnings": ("2026-09-01", "2026-11-06"),
    "retail_sales": ("2026-09-01", "2026-11-17"),
    "real_consumption": ("2026-08-01", "2026-10-29"),
    "consumer_sentiment": ("2026-09-01", "2026-11-20"),
    "housing_starts": ("2026-09-01", "2026-10-27"),
    "building_permits": ("2026-09-01", "2026-10-27"),
    "mortgage_30y": ("2026-10-22", "2026-10-29"),
    "industrial_production": ("2026-09-01", "2026-11-17"),
}


def extend(out, spec_class):
    for (
        key,
        fred_id,
        name,
        category,
        frequency,
        units,
        adjustment,
        representation,
        definition,
        headline,
        _,
    ) in ROWS:
        allowed = (
            ("level", "pp", "standardized")
            if representation == "rate"
            else ("level", "percent", "indexed", "standardized")
            if frequency == "weekly" or key == "consumer_sentiment"
            else ("level", "percent", "mom", "yoy", "indexed", "standardized")
        )
        out[key] = spec_class(
            id=key,
            name=name,
            provider_id=fred_id,
            source="FRED / "
            + (
                "BLS"
                if key in {"job_openings", "participation", "hourly_earnings"}
                else "BEA"
                if key == "real_consumption"
                else "Census Bureau"
                if key in {"retail_sales", "housing_starts", "building_permits"}
                else "Federal Reserve"
                if key in {"industrial_production", "breakeven_5y", "yield_curve"}
                else "US Department of Labor"
                if key == "initial_claims"
                else "Freddie Mac"
                if key == "mortgage_30y"
                else "University of Michigan"
                if key == "consumer_sentiment"
                else "ICE BofA"
            ),
            category=category,
            region="United States",
            frequency=frequency,
            units=units,
            seasonal_adjustment=adjustment,
            representation=representation,
            original_transformation="Original provider level; definition verified against FRED metadata",
            source_url=f"https://fred.stlouisfed.org/series/{fred_id}",
            allowed_transformations=allowed,
            definition=definition,
            source_type="Official or licensed series distributed by FRED",
            observation_type="rate"
            if representation == "rate"
            else "index"
            if representation == "index"
            else "level",
            recommended_headline_transformation=headline,
            headline_name=name,
            primary_source_url=f"https://fred.stlouisfed.org/series/{fred_id}",
            freshness_expectation="Native release frequency; distributor schedule hints are not guaranteed release timestamps.",
            known_limitations=(
                "Latest revised data; observation reference dates are not primary publication dates. Metadata checked 2026-10-25; current values are not independently reconciled to primary releases.",
                definition,
            )
            if key
            in {
                "mortgage_30y",
                "consumer_sentiment",
                "high_yield_spread",
                "investment_grade_spread",
                "breakeven_5y",
            }
            else (
                "Latest revised data; reference dates are not primary publication dates. Metadata checked 2026-10-25; current values are not independently reconciled to primary releases.",
            ),
        )
    return out
