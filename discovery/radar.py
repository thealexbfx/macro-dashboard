"""Registry adapter and ranking. The caller supplies the existing cached loader."""
from datetime import date, timedelta
import pandas as pd
from .engine import Dataset, analyze

SPECS = {
    'gold': ('Commodities · Gold', 'B', 'USD / troy oz', 'futures', 'GC=F'),
    'bitcoin': ('Crypto · Bitcoin', 'D', 'USD', 'crypto', 'BTC-USD'),
    'sp500': ('Equities · S&P 500', 'B', 'index points', 'index', '^GSPC'),
    'us_cpi_sa_yoy': ('United States · CPI YoY', 'M', 'percent', None, 'CPIAUCSL'),
    'unemployment_sa': ('United States · Unemployment Rate', 'M', 'percent', None, 'UNRATE'),
}
DEFINITIONS = {
    'us_cpi_sa_yoy': 'Seasonally adjusted CPI-U all-items index CPIAUCSL, transformed to 12-month percent change by the existing loader. Changes in that rate are percentage points. Not the NSA CPIAUCNS series used in the earlier prototype.',
    'unemployment_sa': 'UNRATE: seasonally adjusted U-3 unemployment rate, percent of civilian labor force age 16+. Changes are percentage points.',
}
RELATED = {
    'gold': [('FX · DXY', 'Dollar pricing offers exchange-rate context; co-movement does not establish causation.'),
             ('Commodities · Silver', 'Shared precious-metal exposure offers context, while industrial demand differs.'),
             ('Rates & Bonds · US 10Y', 'Nominal Treasury yields offer rates context; they are not real yields.')],
    'bitcoin': [('Equities · S&P 500', 'Compare risk-asset co-movement; relationships vary over time.'), ('FX · DXY', 'Dollar conditions offer context without establishing a cause.')],
    'sp500': [('Rates & Bonds · US 10Y', 'Nominal rates offer valuation context without isolating discount-rate effects.')],
    'us_cpi_sa_yoy': [('United States · Unemployment Rate', 'Examine labor and price trends without assuming a fixed tradeoff.')],
    'unemployment_sa': [('United States · CPI YoY', 'Compare labor and price conditions without assuming causation.')],
}


def scan(loader, registry, as_of=None):
    today = as_of or date.today()
    start, end = today-timedelta(days=1095), today-timedelta(days=1)
    signals, status = {}, {}
    for key, (name, frequency, unit, kind, ticker) in SPECS.items():
        try:
            if name not in registry:
                raise ValueError('Not registered in the current comparison catalogue')
            frame = loader(name, start, end).copy()
            frame['date'] = pd.to_datetime(frame.date, utc=True).dt.tz_convert(None).dt.normalize()
            frame = frame[(frame.date >= pd.Timestamp(start)) & (frame.date <= pd.Timestamp(end))]
            if frame.empty or not frame.value.notna().any():
                raise ValueError('No completed usable observations')
            latest = frame.loc[frame.value.notna(), 'date'].max().date()
            source = 'Yahoo Finance unadjusted close' if kind else f'FRED / BLS {ticker}'
            dataset = Dataset(key, frequency, unit, source, name, kind, ticker,
                              'USD' if kind else None, adjustment='Unadjusted provider close; futures rolls may cause discontinuities' if kind else None)
            _, found = analyze(frame, dataset, market=bool(kind))
            age = (today-latest).days
            state = {'latest':str(latest), 'age_days':age, 'stale':age>(60 if frequency=='M' else 4),
                     'source':source, 'definition':DEFINITIONS.get(key),
                     'cache':'Existing chart-workspace cache, up to 15 minutes; upstream cache provenance unavailable',
                     'release_timestamp':'unavailable'}
            for signal in found:
                signal.update(name=name, freshness=state, start=str(start), end=str(end))
                signal['calculation_methodology']['series_definition'] = DEFINITIONS.get(key)
                signals[signal['signal_id']] = signal
            status[key] = state
        except Exception as exc:
            # Do not render raw provider errors: URLs may contain API credentials.
            status[key] = {'unavailable':True, 'reason':type(exc).__name__,
                           'action':'Provider data unavailable or invalid. Check existing provider configuration and retry after the cache expires.'}
    return list(signals.values()), status


def ranked(signals, mode='Latest', since=None, limit=5):
    if mode not in ('Latest', 'Most unusual'):
        raise ValueError('Unknown ranking')
    def unusual(s):
        return (s['statistical_unusualness']['absolute_change_percentile'] if s['family']=='single_series_anomaly'
                else s['trend_context'].get('cumulative_magnitude_percentile')) or 0
    candidates = [s for s in signals if since is None or s['observation_date'] >= str(since)]
    candidates.sort(key=lambda s: (s['observation_date'],s['research_priority']['score']) if mode=='Latest'
                    else (unusual(s),s['observation_date']), reverse=True)
    result, seen = [], set()
    for s in candidates:
        if s['dataset_id'] not in seen:
            result.append(s); seen.add(s['dataset_id'])
    return result[:limit]
