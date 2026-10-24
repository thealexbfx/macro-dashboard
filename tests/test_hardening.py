import unittest
from dataclasses import replace
import numpy as np
import pandas as pd
from discovery import Dataset, Config, analyze, SignalStore
from discovery.scan import scan

class HardeningTests(unittest.TestCase):
    def frame(self, values):
        return pd.DataFrame({'date':pd.date_range('2020-01-31',periods=len(values),freq='ME'),'value':values})

    def test_episode_grouping_and_repeated_scans(self):
        d=Dataset('u','M','percent','test')
        f=self.frame([1,2,3,4,5,4,3,2])
        _,signals=analyze(f,d)
        trends=[s for s in signals if s['signal_type'].startswith('consecutive')]
        self.assertEqual(trends[0]['signal_id'],trends[1]['signal_id'])
        self.assertNotEqual(trends[1]['signal_id'],trends[2]['signal_id'])
        self.assertEqual(len(trends[1]['trend_context']['observation_history']),4)
        store=SignalStore(':memory:')
        self.assertEqual(store.upsert(trends[0]),'created')
        self.assertEqual(store.upsert(trends[1]),'updated')
        self.assertEqual(store.upsert(trends[0]),'historical')
        self.assertEqual(store.upsert(trends[1]),'unchanged')
        self.assertEqual(store.db.execute('SELECT COUNT(*) FROM signal_history').fetchone()[0],2)
        store.close()

    def test_reversal_significance_and_floor(self):
        values=np.cumsum([0]+[1,-1]*40+[.01,-.01])
        d=Dataset('x','M','level','test')
        _,s=analyze(self.frame(values),d)
        self.assertFalse(any(x['signal_type']=='direction_reversal' for x in s))
        f=self.frame(np.cumsum([0]+[1,-1]*40+[5]))
        _,s=analyze(f,d)
        self.assertTrue(any(x['signal_type']=='direction_reversal' for x in s))
        _,s=analyze(f,d,replace(Config(),reversal_minimum=6))
        self.assertFalse(any(x['signal_type']=='direction_reversal' for x in s))

    def test_trend_magnitude_ranking(self):
        d=Dataset('x','M','percent','test')
        def rank(step):
            values=np.cumsum([10]+[.1,-.1]*40+[step]*3)
            _,s=analyze(self.frame(values),d)
            return [x for x in s if x['signal_type']=='consecutive_increases'][-1]
        small,big=rank(.001),rank(1)
        self.assertGreater(big['research_priority']['score'],small['research_priority']['score'])
        self.assertEqual(big['research_priority']['method'],'trend')
        _,s=analyze(self.frame(np.cumsum([10]+[.1,-.1]*40+[3])),d)
        anomaly=next(x for x in s if x['family']=='single_series_anomaly')
        self.assertNotIn('persistence',anomaly['research_priority']['components'])

    def test_current_completion_failure_isolation_and_history(self):
        calls=[]
        def provider(ticker,start,end):
            calls.append((start,end))
            if ticker=='GC=F': raise RuntimeError('provider outage')
            dates=pd.date_range('2024-01-01',periods=5,freq='D') if ticker=='BTC-USD' else pd.bdate_range('2024-01-01',periods=5)
            return pd.DataFrame({'date':dates,'value':[1,2,3,4,500]})
        store=SignalStore(':memory:')
        report=scan(provider,store,as_of='2024-01-05T23:00:00Z',start='2024-01-01')
        self.assertEqual(len(report['failures']),1)
        self.assertEqual(len(report['verified_provider_runs']),2)
        for run in report['verified_provider_runs']:
            self.assertEqual(run['latest_completed_observation'],'2024-01-04')
            self.assertTrue(all(s['observation_date']=='2024-01-04' for s in run['signals']))
        again=scan(provider,store,as_of='2024-01-05T23:00:00Z',start='2024-01-01')
        self.assertTrue(all(status=='unchanged' for r in again['verified_provider_runs'] for status in r['storage_statuses']))
        hist=scan(provider,store,mode='historical',start='2024-01-01',end='2024-01-04',as_of='2024-02-01T00:00:00Z')
        self.assertEqual(hist['verified_provider_runs'][0]['latest_completed_observation'],'2024-01-03')
        store.close()

    def test_gaps_break_episodes_and_momentum(self):
        f=self.frame([1,2,3,4,np.nan,6,7,8,9])
        m,s=analyze(f,Dataset('x','M','level','test'))
        trends=[x for x in s if x['signal_type']=='consecutive_increases']
        self.assertNotEqual(trends[0]['signal_id'],trends[-1]['signal_id'])
        self.assertTrue(pd.isna(m.momentum_5.iloc[-1]))

    def test_weekend_rejected(self):
        f=pd.DataFrame({'date':pd.to_datetime(['2024-01-05','2024-01-06']),'value':[1,2]})
        with self.assertRaises(ValueError): analyze(f,Dataset('x','B','level','test'))
