"""Frequency-aware observations and prior-only statistical comparisons."""
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import hashlib
import numpy as np
import pandas as pd

@dataclass(frozen=True)
class Dataset:
    dataset_id: str
    frequency: str
    unit: str
    source: str
    asset: str = None
    instrument_type: str = None
    ticker: str = None
    currency: str = None
    exchange: str = None
    adjustment: str = None
    release_timestamp: str = None
    ingestion_timestamp: str = None
    revision: str = None

@dataclass(frozen=True)
class Config:
    baseline: int = 252
    minimum_history: int = 30
    anomaly_percentile: float = 0.99
    persistence: int = 3
    trend_window: int = 3
    unusualness_weight: float = .6
    persistence_weight: float = .3
    quality_weight: float = .1

def analyze(frame, dataset, config=Config(), market=False, transformation='difference'):
    """Return metrics and signals. Rates use percentage-point differences.

    D means calendar daily; B means weekdays (supply explicit NaN rows for
    exchange sessions missing in the provider). No observations are filled.
    Percentile uses the empirical midrank of absolute prior changes.
    """
    c, d = config, dataset
    if d.frequency not in ('D', 'B', 'W', 'M', 'Q'):
        raise ValueError('Unsupported source frequency')
    if c.minimum_history < 2 or c.baseline < c.minimum_history or c.persistence < 1 or c.trend_window < 2 or not 0 < c.anomaly_percentile <= 1:
        raise ValueError('Invalid configuration')
    weights = [c.unusualness_weight, c.persistence_weight, c.quality_weight]
    if min(weights) < 0 or sum(weights) <= 0:
        raise ValueError('Invalid ranking weights')
    if market and (d.frequency not in ('D','B') or not all((d.asset,d.instrument_type,d.ticker,d.currency,d.adjustment))):
        raise ValueError('Market identity and adjustment are required')
    if transformation not in ('difference','percent') or (d.unit in ('percent','growth_rate') and transformation == 'percent'):
        raise ValueError('Invalid transformation for metric')
    f = frame[['date','value']].copy()
    f['date'] = pd.to_datetime(f.date, errors='raise')
    if f.date.isna().any() or f.date.duplicated().any() or not f.date.is_monotonic_increasing:
        raise ValueError('Dates must be unique, valid and ordered')
    f['value'] = pd.to_numeric(f.value, errors='raise')
    if np.isinf(f.value).any():
        raise ValueError('Infinite values')
    freq = {'D':'D','B':'B','W':'W','M':'M','Q':'Q'}[d.frequency]
    periods = f.date.dt.to_period(freq)
    if periods.duplicated().any():
        raise ValueError('Frequency mismatch: multiple observations per period')
    f.index = periods
    if len(f):
        f = f.reindex(pd.period_range(periods.iloc[0], periods.iloc[-1], freq=freq))
    v = f.value
    if market and (v.dropna() <= 0).any():
        raise ValueError('Returns require positive prices')
    change = v.diff()
    if market or transformation == 'percent':
        change = v.div(v.shift().where(v.shift() > 0)).sub(1).mul(100)
    m = pd.DataFrame({'value':v,'change':change})
    prior = change.shift().rolling(c.baseline, min_periods=c.minimum_history)
    m['prior_mean'] = prior.mean()
    m['prior_volatility'] = prior.std(ddof=1)
    scale = m.prior_volatility.where(m.prior_volatility > 0)
    m['standardized_return'] = change / scale if market else np.nan
    m['z_score'] = (change-m.prior_mean)/scale
    m['percentile'] = np.nan
    for i in range(len(m)):
        h = change.iloc[max(0,i-c.baseline):i].dropna().abs()
        if len(h) >= c.minimum_history and pd.notna(change.iloc[i]):
            m.iloc[i,m.columns.get_loc('percentile')] = ((h < abs(change.iloc[i])).sum() + .5*(h == abs(change.iloc[i])).sum())/len(h)
    for n in (20,50,200):
        m[f'ma_{n}'] = v.rolling(n,min_periods=n).mean()
    for n in (5,20):
        m[f'momentum_{n}'] = v.div(v.shift(n).where(v.shift(n)>0)).sub(1)*100 if market else v.diff(n)
    lag = {'M':12,'Q':4,'W':52}.get(d.frequency)
    if lag:
        m['year_over_year'] = v.diff(lag) if d.unit in ('percent','growth_rate') else v.div(v.shift(lag).where(v.shift(lag)>0)).sub(1)*100
    m['rolling_trend'] = change.rolling(c.trend_window,min_periods=c.trend_window).mean()
    m['acceleration'] = change.diff()
    m['cumulative_change'] = v.diff(c.trend_window)
    signals=[]
    run=0
    now=datetime.now(timezone.utc).isoformat()
    for i in range(len(m)):
        row=m.iloc[i]
        x=row['change']
        prev=change.iloc[i-1] if i else np.nan
        run = 0 if pd.isna(x) or x == 0 else (run+int(np.sign(x)) if pd.notna(prev) and np.sign(prev)==np.sign(x) else int(np.sign(x)))
        types=[]
        if pd.notna(row.percentile) and row.percentile >= c.anomaly_percentile:
            types.append(('single_series_anomaly','unusual_increase' if x>0 else 'unusual_decrease'))
        if abs(run)>=c.persistence:
            types.append(('sustained_trend','consecutive_increases' if run>0 else 'consecutive_decreases'))
        if i and pd.notna(x) and pd.notna(prev) and x*prev<0:
            types.append(('sustained_trend','direction_reversal'))
        for fast,slow in ((20,50),(50,200)):
            spread=m[f'ma_{fast}']-m[f'ma_{slow}']
            if i and pd.notna(spread.iloc[i-1]) and spread.iloc[i]*spread.iloc[i-1]<0:
                types.append(('sustained_trend',f'ma_{fast}_{slow}_crossover'))
        for family,kind in types:
            warnings=[f'{k}_unavailable' for k in ('release_timestamp','ingestion_timestamp','revision') if getattr(d,k) is None]
            if v.iloc[max(0,i-c.baseline):i+1].isna().any(): warnings.append('missing_observations_in_window')
            if pd.isna(row.percentile): warnings.append('insufficient_history')
            if row.prior_volatility == 0: warnings.append('zero_volatility')
            if market and not d.exchange: warnings.append('exchange_unavailable')
            quality=max(0,1-.1*len(warnings))
            unusualness=0 if pd.isna(row.percentile) else float(row.percentile)
            components=dict(unusualness=unusualness,persistence=min(1,abs(run)/c.persistence),quality=quality)
            score=100*sum(a*b for a,b in zip(weights,components.values()))/sum(weights)
            date=str(f.date.iloc[i].date()) if pd.notna(f.date.iloc[i]) else str(m.index[i].start_time.date())
            sid=hashlib.sha256(f'{d.dataset_id}|{kind}|{date}'.encode()).hexdigest()[:24]
            clean=lambda x: None if pd.isna(x) else float(x)
            signals.append(dict(schema_version=1,signal_id=sid,dataset_id=d.dataset_id,dataset_ids=[d.dataset_id],family=family,signal_type=kind,observation_date=date,detection_timestamp=now,actual_measured_change={'value':clean(x),'unit':'percent' if market or transformation=='percent' else 'percentage_points' if d.unit in ('percent','growth_rate') else d.unit},historical_comparison={'mean':clean(row.prior_mean),'volatility':clean(row.prior_volatility),'prior_observations':int(change.iloc[max(0,i-c.baseline):i].count())},statistical_unusualness={'absolute_change_percentile':clean(row.percentile),'standardized_return':clean(row.standardized_return),'z_score':clean(row.z_score)},trend_context={'consecutive_movements':run,'rolling_change':clean(row.rolling_trend),'acceleration':clean(row.acceleration),'cumulative_change':clean(row.cumulative_change)},research_priority={'score':score,'components':components,'weights':weights,'interpretation':'Research triage, not predictive probability'},calculation_methodology={'version':'1','baseline':'prior observations only','transformation':'percent' if market else transformation,'config':asdict(c)},data_source=asdict(d),data_quality_warnings=warnings,relationship_definition=None,supporting_evidence=[]))
    return m, signals
