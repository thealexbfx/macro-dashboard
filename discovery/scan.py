"""Run with python -m discovery.scan --output signals.json --database discovery.sqlite3."""
import argparse
import json
from datetime import datetime, timezone
from .engine import Dataset, analyze
from .store import SignalStore

def main():
    parser=argparse.ArgumentParser(__doc__)
    parser.add_argument('--output',default='signals.json')
    parser.add_argument('--database',default='discovery.sqlite3')
    args=parser.parse_args()
    # Reuse provider without importing app.py or executing UI initialization.
    from data.yahoo import get_fx_data_yahoo
    store=SignalStore(args.database)
    report={'verified_provider_runs':[],'failures':[]}
    for ticker,asset,kind,freq,adjustment in [('GC=F','Gold','futures','B','unadjusted Yahoo continuous futures close; roll discontinuities possible'),('BTC-USD','Bitcoin','crypto','D','unadjusted spot aggregate close'),('^GSPC','S&P 500','index','B','price index close; excludes dividends')]:
        try:
            f=get_fx_data_yahoo(ticker,'2019-01-01','2021-01-01')
            if f.empty: raise RuntimeError('Provider returned no data')
            d=Dataset(ticker,freq,'USD','Yahoo Finance via existing data.yahoo',asset,kind,ticker,'USD',adjustment=adjustment,ingestion_timestamp=datetime.now(timezone.utc).isoformat())
            metrics,signals=analyze(f,d,market=True)
            statuses=[store.upsert(s) for s in signals]
            report['verified_provider_runs'].append({'dataset':ticker,'observations':len(f),'signals':signals,'storage_statuses':statuses})
        except Exception as exc:
            report['failures'].append({'dataset':ticker,'error':str(exc)})
    store.close()
    with open(args.output,'w',encoding='utf-8') as out: json.dump(report,out,indent=2,allow_nan=False)
    print(json.dumps({'verified':[r['dataset'] for r in report['verified_provider_runs']],'failures':report['failures']}))
    return 0 if report['verified_provider_runs'] else 1

if __name__=='__main__':
    raise SystemExit(main())
