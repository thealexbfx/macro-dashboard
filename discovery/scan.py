"""Completed daily observation scanning; historical scans are explicitly separate."""
import argparse
import json
from datetime import datetime, timezone, timedelta
import pandas as pd
from .engine import Dataset, analyze
from .store import SignalStore

INSTRUMENTS = [('GC=F','Gold','futures','B','unadjusted continuous futures; roll discontinuities possible'),('BTC-USD','Bitcoin','crypto','D','unadjusted aggregate spot'),('^GSPC','S&P 500','index','B','price index; no dividends')]

def scan(provider, store, mode='current', start=None, end=None, as_of=None):
    if mode not in ('current','historical'):
        raise ValueError('Unknown scan mode')
    now = pd.Timestamp(as_of or datetime.now(timezone.utc))
    if now.tzinfo is None:
        raise ValueError('as_of must include a timezone')
    # Conservative completion rule: exclude the entire current UTC date for
    # every instrument, even when an exchange session has already closed.
    cutoff = now.tz_convert('UTC').date()
    start = start or str(cutoff-timedelta(days=730))
    end = end or str(cutoff)
    if pd.Timestamp(start) >= pd.Timestamp(end):
        raise ValueError('start must precede exclusive end')
    report = {'mode':mode,'as_of':now.isoformat(),'completion_rule':'observation date before current UTC date','verified_provider_runs':[],'failures':[]}
    for ticker,asset,kind,freq,adjustment in INSTRUMENTS:
        try:
            f = provider(ticker,start,end).copy()
            if f.empty: raise ValueError('Provider returned no observations')
            dates = pd.to_datetime(f.date)
            # Preserve source calendar date even for timezone-aware market bars.
            days = dates.dt.date
            f = f[(days < cutoff) & (days >= pd.Timestamp(start).date()) & (days < pd.Timestamp(end).date())].copy()
            if f.empty: raise ValueError('No completed observations')
            f['date'] = pd.to_datetime(f.date).dt.tz_localize(None)
            d = Dataset(ticker,freq,'USD','Yahoo Finance via existing data.yahoo',asset,kind,ticker,'USD',adjustment=adjustment,ingestion_timestamp=now.isoformat())
            _, signals = analyze(f,d,market=True)
            if mode == 'current':
                latest = str(f.date.max().date())
                signals = [s for s in signals if s['observation_date']==latest]
            # Collapse snapshots to latest per episode before persistence.
            grouped = {s['signal_id']:s for s in signals}
            signals = list(grouped.values())
            statuses = [store.upsert(s) for s in signals]
            report['verified_provider_runs'].append({'dataset':ticker,'latest_completed_observation':str(f.date.max().date()),'observations':len(f),'signals':signals,'storage_statuses':statuses})
        except Exception as exc:
            report['failures'].append({'dataset':ticker,'error':str(exc)})
    return report

def main():
    p = argparse.ArgumentParser(__doc__)
    p.add_argument('--mode',choices=['current','historical'],default='current')
    p.add_argument('--start')
    p.add_argument('--end',help='Exclusive end date')
    p.add_argument('--output',default='signals.json')
    p.add_argument('--database',default='discovery.sqlite3')
    p.add_argument('--cache-dir',default='data_cache/yahoo')
    args = p.parse_args()
    import yfinance as yf
    yf.set_tz_cache_location(args.cache_dir)
    from data.yahoo import get_fx_data_yahoo
    store = SignalStore(args.database)
    try:
        report = scan(get_fx_data_yahoo,store,args.mode,args.start,args.end)
    finally:
        store.close()
    with open(args.output,'w',encoding='utf-8') as out:
        json.dump(report,out,indent=2,allow_nan=False)
    print(json.dumps({'verified':[r['dataset'] for r in report['verified_provider_runs']],'failures':report['failures']}))
    return 0 if report['verified_provider_runs'] else 1

if __name__=='__main__':
    raise SystemExit(main())
