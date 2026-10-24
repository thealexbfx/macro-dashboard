import unittest
import tempfile
from dataclasses import replace
import pandas as pd
import numpy as np
from discovery import Dataset, Config, analyze, SignalStore

class EngineTests(unittest.TestCase):
    def frame(self, values, freq='ME'):
        return pd.DataFrame({'date':pd.date_range('2000-01-01',periods=len(values),freq=freq),'value':values})
    def test_inflation(self):
        m,s=analyze(self.frame([3.3,3.5,2.6]),Dataset('cpi','M','percent','synthetic'))
        self.assertAlmostEqual(m.change.iloc[-1],-.9)
        self.assertAlmostEqual(m.acceleration.iloc[-1],-1.1)
        self.assertEqual(s, [])  # insufficient baseline suppresses reversal noise
    def test_unemployment(self):
        m,s=analyze(self.frame([3.5,3.6,3.7,3.8]),Dataset('unemployment','M','percent','synthetic'))
        self.assertEqual(s[-1]['trend_context']['consecutive_movements'],3)
    def test_asset_specific_and_prior_only(self):
        def run(scale):
            returns=np.array([scale,-scale]*40+[-2.5])
            prices=100*np.cumprod(1+np.r_[0,returns]/100)
            return analyze(self.frame(prices,'D'),Dataset('gold','D','USD','synthetic','Gold','ETF','GLD','USD',adjustment='adjusted'),market=True)[0]
        low,high=run(.4),run(4)
        self.assertAlmostEqual(low.change.iloc[-1],-2.5)
        self.assertGreater(abs(low.standardized_return.iloc[-1]),abs(high.standardized_return.iloc[-1]))
        self.assertEqual(low.percentile.iloc[-1],1)
        self.assertEqual(high.percentile.iloc[-1],0)
        self.assertAlmostEqual(low.prior_volatility.iloc[-1],pd.Series([.4,-.4]*40).std())
    def test_missing_and_frequencies(self):
        for freq,rule in [('M','ME'),('Q','QE'),('W','W')]:
            f=self.frame([1,2,3,4],rule).drop(index=2)
            m,_=analyze(f,Dataset('x',freq,'level','synthetic'))
            self.assertTrue(pd.isna(m.change.iloc[-1]))
        with self.assertRaises(ValueError): analyze(self.frame([1,2,3],'D'),Dataset('x','M','level','synthetic'))
    def test_invalid_transform(self):
        with self.assertRaises(ValueError): analyze(self.frame([3,4]),Dataset('x','M','percent','synthetic'),transformation='percent')
    def test_zero_volatility_and_short_history(self):
        m,s=analyze(self.frame([1]*40+[2]),Dataset('x','M','level','synthetic'))
        self.assertTrue(pd.isna(m.z_score.iloc[-1]))
        self.assertIn('zero_volatility',s[-1]['data_quality_warnings'])
        m,_=analyze(self.frame([1,2]),Dataset('x','M','level','synthetic'))
        self.assertTrue(m.percentile.isna().all())
    def test_storage(self):
        _,s=analyze(self.frame([1,2,3,4]),Dataset('x','M','level','synthetic'))
        with tempfile.TemporaryDirectory() as tmp:
            store=SignalStore(tmp+'/signals.db')
            self.assertEqual(store.upsert(s[-1]),'created')
            self.assertEqual(store.upsert(dict(s[-1],detection_timestamp='later')),'unchanged')
            updated=dict(s[-1],actual_measured_change={'value':2,'unit':'level'})
            self.assertEqual(store.upsert(updated),'updated')
            store.feedback(s[-1]['signal_id'],'interesting')
            store.close()
    def test_historical_unemployment_benchmark(self):
        # BLS LNS14000000, published monthly rates, not a vintage backtest.
        f=pd.DataFrame({'date':pd.to_datetime(['2020-01-31','2020-02-29','2020-03-31','2020-04-30']), 'value':[3.6,3.5,4.4,14.7]})
        m,s=analyze(f,Dataset('LNS14000000','M','percent','BLS benchmark'))
        self.assertAlmostEqual(m.change.iloc[-1],10.3)
        self.assertFalse(any(x['family']=='single_series_anomaly' for x in s))
        # Expected detection failure: only three changes, below minimum history.

if __name__=='__main__': unittest.main()
