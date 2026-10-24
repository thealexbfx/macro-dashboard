"""Radar data integration and UI-independent selection logic. No invented data."""
from datetime import datetime, timezone
import pandas as pd
from .engine import Dataset, analyze

CATALOG = {
 'gold': ('Gold futures','Markets','GC=F','B','USD','futures'),
 'bitcoin': ('Bitcoin','Markets','BTC-USD','D','USD','crypto'),
 'sp500': ('S&P 500','Markets','^GSPC','B','USD','index'),
 'unemployment': ('US unemployment','Economy','LNS14000000','M','percent',None),
 'inflation': ('US CPI inflation YoY','Economy','CUUR0000SA0','M','percent',None),
 'dollar': ('US Dollar Index','Markets','DX-Y.NYB','B','USD','index'),
 'silver': ('Silver futures','Markets','SI=F','B','USD','futures'),
 'real_yield': ('10-year real Treasury yield','Economy','DFII10','B','percent',None),
 'expectations': ('10-year breakeven inflation','Economy','T10YIE','B','percent',None),
}
RELATIONSHIPS = {
 'gold': [('dollar','Dollar pricing can influence gold affordability; examine co-movement, not causation.'),('real_yield','Real yields represent an opportunity-cost context for non-yielding gold.'),('silver','Shared precious-metal exposure may provide context; industrial demand differs.'),('expectations','Breakevens provide a market inflation-expectations proxy, also affected by liquidity and risk premia.')],
 'bitcoin': [('sp500','Compare risk-asset co-movement; relationships vary across regimes.'),('dollar','Dollar conditions may provide context without establishing causality.')],
 'sp500': [('real_yield','Discount-rate context may be relevant to equity valuations.')],
 'inflation': [('expectations','Compare realized inflation with market expectations; horizons differ.')],
 'unemployment': [('inflation','Labor and price trends can be investigated jointly; no fixed tradeoff is assumed.')],
}

def load_series(key, start, end):
    name,category,code,freq,unit,kind=CATALOG[key]
    if category=='Markets':
        import yfinance as yf
        yf.set_tz_cache_location('data_cache/yahoo')
        from data.yahoo import get_fx_data_yahoo
        f=get_fx_data_yahoo(code,start,end)
        source='Yahoo Finance'
    elif key in ('real_yield','expectations'):
        from data.fred import get_fred_series
        f=get_fred_series(code)
        source='FRED'
    else:
        from data.bls import get_bls_series
        f=get_bls_series(code,start_year=pd.Timestamp(start).year-1)
        source='BLS'
        if key=='inflation':
            # Match months rather than exact month-end dates across leap years.
            f=f.copy()
            f.index=pd.to_datetime(f.date).dt.to_period('M')
            if f.index.duplicated().any(): raise ValueError('Duplicate CPI months')
            f=f.reindex(pd.period_range(f.index.min(),f.index.max(),freq='M'))
            f['value']=f.value.div(f.value.shift(12)).sub(1)*100
            f['date']=f.index.to_timestamp('M')
            f=f.reset_index(drop=True)
    if f.empty: raise ValueError('Provider returned no observations')
    f=f.copy()
    f['date']=pd.to_datetime(f.date).dt.tz_localize(None)
    f=f[(f.date>=pd.Timestamp(start)) & (f.date<pd.Timestamp(end)) & (f.date.dt.normalize()<pd.Timestamp.now(tz='UTC').tz_localize(None).normalize())]
    if f.empty or not f.value.notna().any(): raise ValueError('No usable observations in range')
    return f,source

def collect(start, end, loader=load_series, now=None):
    now=pd.Timestamp(now or datetime.now(timezone.utc)).tz_convert('UTC').tz_localize(None)
    frames,signals,status={},{},{}
    for key in ('gold','bitcoin','sp500','unemployment','inflation'):
        try:
            f,source=loader(key,start,end)
            f=f[f.date.dt.normalize()<now.normalize()]
            if f.empty: raise ValueError('No completed observations')
            frames[key]=f
            name,category,code,freq,unit,kind=CATALOG[key]
            latest=f.loc[f.value.notna(),'date'].max()
            age=(now-latest).days
            stale=age > (60 if freq=='M' else 4)
            d=Dataset(key,freq,unit,source,name,kind,code,'USD' if kind else None,adjustment='unadjusted futures/index/aggregate close' if kind else None,ingestion_timestamp=now.isoformat())
            _,found=analyze(f,d,market=bool(kind))
            # Most recent snapshot per episode; retain recent discoveries for browsing.
            for s in found:
                s['category']=category
                s['freshness']={'latest_observation':str(latest.date()),'age_days':age,'stale':stale}
                signals[s['signal_id']]=s
            status[key]={'latest':str(latest.date()),'stale':stale,'source':source}
        except Exception as exc:
            status[key]={'error':str(exc)}
    return frames,list(signals.values()),status

def select_discoveries(signals, categories, types, start, end, limit=5):
    found=[s for s in signals if s['category'] in categories and s['signal_type'] in types and str(start)<=s['observation_date']<=str(end)]
    # Distinct datasets by default: one asset cannot occupy the whole radar.
    ranked=sorted(found,key=lambda s:(s['research_priority']['score'],s['observation_date']),reverse=True)
    result=[]
    seen=set()
    for s in ranked:
        if s['dataset_id'] not in seen:
            result.append(s); seen.add(s['dataset_id'])
    return result[:limit]
