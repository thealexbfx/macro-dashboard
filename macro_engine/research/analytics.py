"""Pure research calculations. No UI, network, cache, or investment conclusions."""

from dataclasses import asdict, dataclass
from typing import Mapping

import numpy as np
import pandas as pd

FREQUENCIES = {
    "daily": ("D", 252),
    "weekly": ("W-FRI", 52),
    "monthly": ("M", 12),
    "quarterly": ("Q", 4),
    "annual": ("Y", 1),
}
LIMITATION = (
    "Observation-date analysis using latest available values; release dates and "
    "historical revisions are unverified. This is not a point-in-time backtest."
)


@dataclass(frozen=True)
class SeriesMetadata:
    category: str = "economic"
    units: str = "unspecified"
    frequency: str = "monthly"
    representation: str = "level"
    can_be_nonpositive: bool = True
    source: str = "unspecified"
    date_convention: str = "observation date; publication availability unverified"
    ratio_group: str = ""
    carry_forward_days: int = 0

    def __post_init__(self):
        if self.frequency not in FREQUENCIES:
            raise ValueError("Unsupported observation frequency.")
        if self.carry_forward_days < 0:
            raise ValueError("Carry-forward bounds cannot be negative.")
        if self.representation not in {
            "price",
            "index",
            "yield",
            "rate",
            "growth_rate",
            "spread",
            "signed_flow",
            "level",
        }:
            raise ValueError("Unsupported series representation.")

    @property
    def return_eligible(self):
        return self.representation in {"price", "index"} and not self.can_be_nonpositive

    @property
    def change_unit(self):
        if self.representation == "yield":
            return "basis points"
        if self.representation in {"rate", "growth_rate"}:
            return "percentage points"
        return "%" if self.return_eligible else self.units


def metadata(config: Mapping, name="", group="") -> SeriesMetadata:
    """Adapt existing registry fields conservatively; explicit fields take precedence."""
    unit = config.get("unit_type") or config.get("unit") or "unspecified"
    title = (name + " " + config.get("title", "")).lower()
    category = config.get("group", group) or "economic"
    market = category in {"FX", "Equities", "Commodities", "Crypto"}
    if category == "Rates & Bonds" or config.get("is_yield"):
        representation = "yield"
    elif unit == "percent" or config.get("change_type") == "percentage_points":
        representation = (
            "growth_rate"
            if any(t in title for t in ("yoy", "mom", "growth", "qoq"))
            else "rate"
        )
    elif market:
        representation = "price"
    else:
        representation = "level"
    # Currency scales and counts are not sufficiently specified for cross-series ratios.
    return SeriesMetadata(
        category=category,
        units=config.get("unit_label") or unit,
        frequency=config.get("frequency")
        or ("daily" if market or representation == "yield" else "monthly"),
        representation=config.get("representation", representation),
        can_be_nonpositive=config.get(
            "can_be_nonpositive", not market or category == "Commodities"
        ),
        source=config.get("source", "Yahoo Finance" if market else "unspecified"),
        date_convention=config.get("date_convention", SeriesMetadata.date_convention),
        ratio_group=config.get("ratio_group", ""),
        carry_forward_days=config.get("carry_forward_days", 0),
    )


def clean(frame):
    if not {"date", "value"}.issubset(frame.columns):
        raise ValueError("Each series requires date and value columns.")
    out = frame.copy()
    out["date"] = pd.to_datetime(out["date"], errors="raise", utc=True).dt.tz_convert(
        None
    )
    if out.date.isna().any():
        raise ValueError("Observation dates cannot be missing.")
    out["value"] = pd.to_numeric(out["value"], errors="coerce").replace(
        [np.inf, -np.inf], np.nan
    )
    if out["date"].duplicated().any():
        raise ValueError(
            "Duplicate observation dates require an explicit vintage selection."
        )
    return out.sort_values("date")


def align(left, right, left_meta, right_meta, *, availability=False, max_age_days=None):
    """Period-end last observation; filling requires explicit state-series metadata.

    Availability mode requires publication_date and a finite staleness bound. It
    uses backward as-of joins; callers still must supply unrevised vintages.
    """
    if (
        left_meta.frequency not in FREQUENCIES
        or right_meta.frequency not in FREQUENCIES
    ):
        raise ValueError("Unsupported observation frequency.")
    frequency = max(
        (left_meta.frequency, right_meta.frequency), key=list(FREQUENCIES).index
    )
    alias = FREQUENCIES[frequency][0]
    a, b = clean(left), clean(right)
    if a.empty or b.empty:
        raise ValueError("Both series require observations.")
    start = max(a.date.min().to_period(alias), b.date.min().to_period(alias))
    end = min(a.date.max().to_period(alias), b.date.max().to_period(alias))
    grid = pd.period_range(start, end, freq=alias).to_timestamp(how="end").normalize()
    if frequency == "daily":
        # Use observed trading sessions, retaining dates missing on only one side.
        # Calendar weekends would otherwise break every financial rolling window.
        grid = pd.DatetimeIndex(sorted(set(a.date) | set(b.date)))
        grid = grid[
            (grid >= max(a.date.min(), b.date.min()))
            & (grid <= min(a.date.max(), b.date.max()))
        ]
        if (left_meta.category == "Crypto") != (right_meta.category == "Crypto"):
            grid = grid[grid.dayofweek < 5]
    if availability:
        if max_age_days is None or max_age_days <= 0:
            raise ValueError("Availability alignment requires positive max_age_days.")
        cols = []
        for frame, name in ((a, "left"), (b, "right")):
            if "publication_date" not in frame or frame.publication_date.isna().any():
                raise ValueError(
                    "Actual publication dates are required for availability alignment."
                )
            frame["publication_date"] = (
                pd.to_datetime(frame.publication_date, utc=True)
                .dt.tz_convert(None)
                .astype("datetime64[ns]")
            )
            if (frame.publication_date < frame.date).any():
                raise ValueError("Publication dates cannot precede observation dates.")
            if frame.publication_date.duplicated().any():
                raise ValueError(
                    "Resolve simultaneous releases explicitly before alignment."
                )
            joined = pd.merge_asof(
                pd.DataFrame({"date": grid.astype("datetime64[ns]")}),
                frame.sort_values("publication_date"),
                left_on="date",
                right_on="publication_date",
                direction="backward",
                tolerance=pd.Timedelta(days=max_age_days),
                suffixes=("", "_observation"),
            )
            cols.append(joined.set_index("date").value.rename(name))
        result = pd.concat(cols, axis=1)
    else:

        def sample(frame, name, meta):
            frame = frame.assign(period=frame.date.dt.to_period(alias))
            # tail preserves a reported missing value, unlike groupby.last().
            sampled = frame.groupby("period").tail(1).set_index("period").value
            sampled.index = sampled.index.to_timestamp(how="end").normalize()
            if meta.carry_forward_days:
                # Explicit effective-state series only; reported NaNs remain unknown.
                return sampled.reindex(
                    grid,
                    method="ffill",
                    tolerance=pd.Timedelta(days=meta.carry_forward_days),
                ).rename(name)
            return sampled.reindex(grid).rename(name)

        result = pd.concat(
            [sample(a, "left", left_meta), sample(b, "right", right_meta)], axis=1
        )
    valid = result.dropna()
    details = {
        "frequency": frequency,
        "observations": len(valid),
        "start": str(valid.index.min().date()) if len(valid) else None,
        "end": str(valid.index.max().date()) if len(valid) else None,
        "missing_periods": int(result.isna().any(axis=1).sum()),
        "left_last_observation": str(a.date.max().date()),
        "right_last_observation": str(b.date.max().date()),
        "period_label_convention": "Period-end labels are not publication dates; terminal period may be incomplete.",
        "alignment": "backward publication-date as-of"
        if availability
        else "period-end last observation; bounded persistence only for declared state series"
        if left_meta.carry_forward_days or right_meta.carry_forward_days
        else "period-end last observation; no filling",
        "state_carry_forward_days": {
            "left": left_meta.carry_forward_days,
            "right": right_meta.carry_forward_days,
        },
        "daily_calendar": "observed sessions; weekday sampling for mixed crypto comparisons"
        if frequency == "daily"
        else None,
        "limitation": "Release dates used; revision/vintage provenance still requires verification."
        if availability
        else LIMITATION,
    }
    return result, details


def changes(series, meta):
    if meta.return_eligible:
        if (series.dropna() <= 0).any():
            raise ValueError(
                "Percentage returns require strictly positive observations."
            )
        return series.pct_change(fill_method=None) * 100
    if meta.representation == "yield":
        if meta.units not in {"%", "percent"}:
            raise ValueError(
                "Yield basis-point conversion requires yields quoted in percent."
            )
        return series.diff() * 100
    return series.diff()


def analyze(left, right, left_meta, right_meta, mode="Price", window=None, **alignment):
    frame, details = align(left, right, left_meta, right_meta, **alignment)
    a, b = frame.left, frame.right
    details.update(
        mode=mode,
        left_units=left_meta.units,
        right_units=right_meta.units,
        left_source=left_meta.source,
        right_source=right_meta.source,
        left_change_unit=left_meta.change_unit,
        right_change_unit=right_meta.change_unit,
        left_metadata=asdict(left_meta),
        right_metadata=asdict(right_meta),
    )
    unit = "original units (separate panels)"
    if mode == "Price":
        result = frame
    elif mode in {"Percentage Change", "Relative Performance", "Drawdown"}:
        if not all(m.return_eligible for m in (left_meta, right_meta)):
            raise ValueError(
                f"{mode} requires positive price/index series with meaningful relative changes. Use changes instead."
            )
        if frame.dropna().empty or (frame <= 0).any().any():
            raise ValueError("Strictly positive overlapping observations are required.")
        first = frame.dropna().iloc[0]
        result = (frame / first - 1) * 100
        unit = "% since first overlapping observation"
        if mode == "Relative Performance":
            result = (result.left - result.right).to_frame("relative_performance")
            unit = "percentage-point performance difference"
        elif mode == "Drawdown":
            result = (frame / frame.cummax() - 1) * 100
            unit = "% below peak within selected sample"
    elif mode == "Ratio":
        if (
            not left_meta.ratio_group
            or left_meta.ratio_group != right_meta.ratio_group
            or left_meta.units != right_meta.units
        ):
            raise ValueError(
                "Ratio requires explicitly compatible units and ratio_group metadata."
            )
        if (b.dropna() == 0).any():
            raise ValueError(
                "Ratio denominator contains zero; no observations were silently removed."
            )
        result = (a / b).to_frame("ratio")
        unit = "ratio"
    elif mode == "Yield Spread":
        if any(
            m.representation != "yield" or m.units not in {"%", "percent"}
            for m in (left_meta, right_meta)
        ):
            raise ValueError("Yield spread requires two yields quoted in percent.")
        result = ((a - b) * 100).to_frame("spread")
        unit = "basis points"
    elif mode == "Changes":
        result = pd.DataFrame(
            {"left": changes(a, left_meta), "right": changes(b, right_meta)}
        )
        unit = f"left: {left_meta.change_unit}; right: {right_meta.change_unit}"
    elif mode in {"Rolling Correlation", "Rolling Volatility"}:
        window = window or (60 if mode == "Rolling Correlation" else 30)
        if not isinstance(window, int) or window < 3:
            raise ValueError("Rolling windows require at least three observations.")
        ca, cb = changes(a, left_meta), changes(b, right_meta)
        details.update(
            window=window,
            transformations=f"left: {left_meta.change_unit} changes; right: {right_meta.change_unit} changes",
        )
        if mode == "Rolling Correlation":
            result = (
                ca.rolling(window, min_periods=window).corr(cb).to_frame("correlation")
            )
            unit = "Pearson correlation of changes"
        else:
            annualizer = FREQUENCIES[details["frequency"]][1]
            if (
                left_meta.category == right_meta.category == "Crypto"
                and details["frequency"] == "daily"
            ):
                annualizer = 365
            result = pd.DataFrame(
                {"left": ca.rolling(window).std(), "right": cb.rolling(window).std()}
            ) * np.sqrt(annualizer)
            unit = f"annualized change standard deviation; left: {left_meta.change_unit}; right: {right_meta.change_unit}"
            details["annualization_periods"] = annualizer
            details["annualization_assumption"] = (
                "Square-root-of-time scaling is descriptive and assumes comparable independent period changes."
            )
    else:
        raise ValueError(f"Unsupported analysis mode: {mode}")
    result = result.replace([np.inf, -np.inf], np.nan)
    valid = result.dropna()
    details.update(
        output_units=unit,
        valid_statistics=len(valid),
        statistic_start=str(valid.index.min().date()) if len(valid) else None,
        statistic_end=str(valid.index.max().date()) if len(valid) else None,
    )
    if valid.empty:
        details["warning"] = (
            "Insufficient observations or constant inputs; no valid statistic."
        )
    return result, details


def relationship(frame, lags=range(-6, 7), window=12, minimum=12):
    """Positive lag: left at t versus right at t+h. Keep missing grid cells."""
    if window < 3 or minimum < 3:
        raise ValueError("Relationship windows require at least three observations.")

    def stats(pair):
        pair = pair.dropna()
        corr = (
            pair.iloc[:, 0].corr(pair.iloc[:, 1])
            if len(pair) >= minimum
            and pair.iloc[:, 0].std() > 0
            and pair.iloc[:, 1].std() > 0
            else np.nan
        )
        return {
            "observations": len(pair),
            "correlation": None if pd.isna(corr) else float(corr),
            "start": str(pair.index.min().date()) if len(pair) else None,
            "end": str(pair.index.max().date()) if len(pair) else None,
            "direction": "unavailable"
            if pd.isna(corr)
            else "positive"
            if corr > 0
            else "inverse"
            if corr < 0
            else "zero",
        }

    lagged = []
    for lag in lags:
        pair = pd.concat([frame.left, frame.right.shift(-lag)], axis=1)
        lagged.append({"lag": int(lag), **stats(pair)})
    midpoint = len(frame) // 2
    rolling = frame.left.rolling(window, min_periods=window).corr(frame.right)
    return {
        "lead_lag": lagged,
        "full_sample": stats(frame),
        "first_half": stats(frame.iloc[:midpoint]),
        "second_half": stats(frame.iloc[midpoint:]),
        "rolling": rolling,
        "window": window,
        "limitations": [
            "Positive lag means left leads right by h comparison periods.",
            "Exploratory correlations are sample-sensitive and not predictive validation.",
            "Lag scanning entails multiple comparisons; no significance or causal claims.",
            "Autocorrelation, overlapping windows and revised macro data affect interpretation.",
        ],
    }
