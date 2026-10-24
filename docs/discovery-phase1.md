# Discovery engine Phase 1

The Streamlit application, routing, existing models and provider defaults are
preserved. `discovery` imports pandas/numpy and standard-library modules only.
The Yahoo loader now optionally selects adjusted close; its default is unchanged.
Never use unadjusted ETF/equity prices for corporate-action-safe returns.
Gold GC=F is a continuous futures series, not spot gold or a gold ETF. Roll
discontinuities are a limitation of this provider series.

## Running

Use the existing requirements.txt environment. Run:

```
python -m unittest discover -s tests -v
python -m discovery.scan --output signals.json --database discovery.sqlite3
```

The CLI fetches 2019–2020 market history through data.yahoo. Provider successes
and failures are recorded separately. Pure functions also accept date/value
frames returned by data.fred, data.bls, data.bea and country indicator modules.
Do not import app.py: it executes the website and requires OpenAI credentials.

## Methodology and schema

Dataset records require explicit frequency and market identity. M/Q/W map to
calendar periods; duplicate periods reject incompatible frequency declarations.
Absent periods become explicit missing rows, never filled prices. D is calendar
daily; B uses weekdays and is conservative around exchange holidays. An exact
exchange-session calendar is not yet implemented. Supply explicit missing rows
for missing expected sessions. A daily series mislabeled as weekly is rejected;
sparse data cannot always distinguish a frequency mismatch from missing data.

Change is a difference for rates (percentage points), or a simple percentage
return for positive prices/levels. Already transformed growth rates must not be
transformed again. Annual comparisons use 12 monthly or 4 quarterly periods;
weekly comparisons use a 52-week lag, not exact calendar-year matching.
Quarterly changes are not implicitly annualized.

Historical mean, sample volatility and absolute-change midrank exclude the
evaluated observation. Standardized return is return / prior standard deviation;
z-score subtracts the prior mean first. Zero volatility produces undefined
standardized statistics and an explicit warning, not infinity. Percentile
thresholds are configurable research policy; they compare each series against
its own history. Default minimum history is 30 valid prior changes.

Metrics include 20/50/200-period means, 5/20-period momentum, cumulative change,
rolling mean change and acceleration. Signals cover tail changes, consecutive
movements, one-period direction reversals and moving-average crossovers.
Acceleration is reported as context, not separately classified as significant.
Reversals are descriptive and can be noisy. Missing baselines are explicitly
flagged. Signals are observations without causal economic explanations.

Each signal contains identity, dataset IDs, family, type, observation/detection
dates, measured change and units, historical sample count/mean/volatility,
percentile/standardized return/z-score, trend context, methodology/config,
source metadata and quality warnings. `relationship_definition`, multiple
`dataset_ids` and `supporting_evidence` reserve cross-series support; no
relationship detection is implemented.

Ranking is 100 times a normalized weighted sum: empirical unusualness (0.6),
capped consecutive persistence (0.3), metadata/data quality (0.1). Quality loses
0.1 per explicit warning. All weights are configurable and stored. This is a
research sorting heuristic, not a predictive probability or calibrated confidence.

Stable IDs hash dataset, signal type and observation date. SQLite upserts ignore
new detection/ingestion timestamps alone; material changes increment the version.
Detection timestamps for versions and feedback are stored separately. Feedback
supports interesting, irrelevant, misleading and already_investigated.
Signals that disappear following revisions are not yet automatically retracted.

## Architecture audit

Streamlit app.py routes app_pages; components owns charts/layout. data contains
Yahoo, FRED, BLS, BEA and international adapters; indicators supplies transformed
country series; models supplies weighted macro pillars and regime scores.
Existing BLS/BEA CSV caches and Streamlit caches are reusable. The inspected
providers generally return only date/value and discard release/vintage metadata.
Missing release, ingestion and revision fields are marked unavailable rather
than inferred. Existing model scores include the current observation and should
not be reused as the scanner's prior-only anomaly baseline.

## Validation and limitations

Synthetic tests cover a -2.5% move in low/high volatility histories, three rises
in unemployment, inflation 3.3/3.5/2.6, missing monthly/weekly/quarterly periods,
frequency mismatches, invalid rate transforms, zero volatility, short history,
deduplication and updates. The BLS unemployment benchmark covers Jan–Apr 2020
(3.6, 3.5, 4.4, 14.7 percent), expected April change +10.3 percentage points.
Its deliberate anomaly detection failure documents insufficient baseline history.
Source: https://data.bls.gov/timeseries/LNS14000000 . These are historical
reference values, not a verified live fetch or a real-time vintage backtest.
The provider demo separately exercises the 2020 market shock period; it is not
a full sensitivity/false-positive benchmark. Broader verified historical event
fixtures and economic live demonstrations remain needed before production use.

## Scheduling and deployment

Run the CLI once after market close using an existing scheduler (Windows Task
Scheduler, cron, or an existing CI schedule). Avoid continuous polling. Place
SQLite and caches on a persistent writable volume and back them up. The existing
Render free web configuration does not guarantee durable local files; SQLite on
ephemeral storage cannot promise cross-restart deduplication. Run the scheduled
scanner on an existing durable host rather than adding a paid database/service.
No schedule or paid infrastructure is provisioned by this change.

Phase 2 should add exchange calendars, vintage/release-aware provider envelopes,
signal retractions, larger historical validation, then availability-aware
cross-series definitions and evidence. Frontend research tools remain deferred.

## Verified execution

Eight unittest cases passed locally. A live provider request successfully retrieved
2019–2020 GC=F, BTC-USD and ^GSPC history and generated signals for all three.
The runtime required a writable Yahoo cache path; set yfinance.set_tz_cache_location
to a writable directory on restricted hosts. No live economic request was verified.
Full Streamlit startup was not exercised because application credentials are absent.
