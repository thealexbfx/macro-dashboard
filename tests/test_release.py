"""Release integration tests use no live API credentials or external requests."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
import pandas as pd
import requests
from data import bls
from discovery.radar import economic_series, load_series, select_discoveries


class ReleaseTests(unittest.TestCase):
    def response(self, status, data=None):
        r=Mock(status_code=status)
        r.json.return_value=data or {'status':'REQUEST_SUCCEEDED'}
        return r

    def test_retry_transient_then_success(self):
        with patch('data.bls.requests.post',side_effect=[self.response(503),self.response(429),self.response(200)]) as post, patch('data.bls.time.sleep') as sleep:
            self.assertEqual(bls._post_json({})['status'],'REQUEST_SUCCEEDED')
        self.assertEqual(post.call_count,3)
        self.assertEqual([c.args[0] for c in sleep.call_args_list],[1,2])

    def test_retry_exhaustion_timeout_and_no_retry_bad_request(self):
        for outcome,count in [(self.response(503),3),(requests.Timeout(),3),(self.response(400),1)]:
            with patch('data.bls.requests.post',side_effect=outcome if isinstance(outcome,Exception) else None,return_value=outcome) as post, patch('data.bls.time.sleep'):
                with self.assertRaises(RuntimeError): bls._post_json({})
                self.assertEqual(post.call_count,count)

    def test_stale_cache_explicit_and_missing_value_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'series.csv'
            frame=pd.DataFrame({'date':['2024-01-31','2024-02-29'],'value':[4,None]})
            bls._write_cached_series(frame,path)
            with patch('data.bls._post_json',side_effect=RuntimeError('BLS HTTP 503')):
                result=bls._request_or_cache({},path)
            self.assertEqual(result.attrs['retrieval']['cache'],'stale')
            self.assertIn('503',result.attrs['retrieval']['error'])
            self.assertTrue(pd.isna(result.value.iloc[1]))

    def test_fresh_disk_cache_avoids_provider(self):
        bls.get_bls_series.clear()
        with tempfile.TemporaryDirectory() as tmp, patch('data.bls.CACHE_DIR',Path(tmp)), patch('data.bls._post_json') as provider:
            path=bls._cache_path('test',2020)
            bls._write_cached_series(pd.DataFrame({'date':['2020-01-31'],'value':[4]}),path)
            result=bls.get_bls_series('test',2020)
            provider.assert_not_called()
            self.assertEqual(result.attrs['retrieval']['cache'],'fresh')
        bls.get_bls_series.clear()

    def test_exact_fred_mapping_and_month_end_normalization(self):
        f=pd.DataFrame({'date':pd.to_datetime(['2020-01-01','2020-02-01']),'value':[3.5,3.6]})
        with patch('data.bls.get_bls_series',side_effect=RuntimeError('503')), patch('config.FRED_API_KEY','test-only'), patch('data.fred.get_fred_series',return_value=f) as fred:
            result,source=economic_series('unemployment','2020-01-01')
            fred.assert_called_once_with('UNRATE')
        self.assertEqual(str(result.date.iloc[-1].date()),'2020-02-29')
        self.assertIn('fallback',source)
        self.assertEqual(result.value.tolist(),[3.5,3.6])
        self.assertIn('primary_error',result.attrs['retrieval'])

    def test_cpi_fallback_same_nsa_index_and_transformation(self):
        f=pd.DataFrame({'date':pd.date_range('2019-01-01',periods=25,freq='MS'),'value':[100]*12+[110]*13})
        with patch('data.bls.get_bls_series',side_effect=RuntimeError('503')), patch('config.FRED_API_KEY','test-only'), patch('data.fred.get_fred_series',return_value=f) as fred:
            result,source=load_series('inflation','2020-01-01','2021-02-01')
            fred.assert_called_once_with('CPIAUCNS')
        self.assertAlmostEqual(result.value.iloc[1],10)
        self.assertIn('not seasonally adjusted',result.attrs['definition']['definition'])
        self.assertEqual(result.attrs['retrieval']['fallback_series'],'CPIAUCNS')

    def test_missing_key_and_redacted_fred_failure(self):
        with patch('data.bls.get_bls_series',side_effect=RuntimeError('BLS HTTP 503')), patch('config.FRED_API_KEY',None), patch('data.fred.get_fred_series') as fred:
            with self.assertRaisesRegex(RuntimeError,'not configured'): economic_series('inflation','2020-01-01')
            fred.assert_not_called()
        with patch('data.bls.get_bls_series',side_effect=RuntimeError('BLS HTTP 503')), patch('config.FRED_API_KEY','test-only'), patch('data.fred.get_fred_series',side_effect=RuntimeError('secret-key-in-url')):
            with self.assertRaises(RuntimeError) as exc: economic_series('inflation','2020-01-01')
            self.assertNotIn('secret-key',str(exc.exception))

    def test_ordering_latest_vs_unusual(self):
        def signal(identity,date,percentile,family='single_series_anomaly'):
            return {'dataset_id':'gold','signal_id':identity,'category':'Markets','signal_type':'move','observation_date':date,'family':family,'research_priority':{'score':percentile*100},'statistical_unusualness':{'absolute_change_percentile':percentile},'trend_context':{'cumulative_magnitude_percentile':.999}}
        signals=[signal('old','2024-01-01',1),signal('new','2024-02-01',.99)]
        args=(signals,['Markets'],['move'],'2024-01-01','2024-03-01')
        self.assertEqual(select_discoveries(*args)[0]['signal_id'],'new')
        self.assertEqual(select_discoveries(*args,order='Most unusual discoveries')[0]['signal_id'],'old')
        signals=[signal('anomaly','2024-01-01',.99),signal('trend','2024-02-01',.01,'sustained_trend')]
        self.assertEqual(select_discoveries(signals,['Markets'],['move'],'2024-01-01','2024-03-01',order='Most unusual discoveries')[0]['signal_id'],'trend')

    def test_full_navigation_investigation_comparison(self):
        from streamlit.testing.v1 import AppTest
        from discovery.radar import collect
        from test_radar import fixture
        data=collect('2022-01-01','2035-01-01',fixture,now='2036-01-01T00:00:00Z')
        with patch('app_pages.discovery_radar.radar_data',return_value=data), patch('app_pages.discovery_radar.related_data',side_effect=fixture):
            app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'))
            app.query_params['page']='DiscoveryRadar'
            app.run(timeout=30)
            app.date_input[0].set_value(pd.Timestamp('2022-01-01').date())
            app.date_input[1].set_value(pd.Timestamp('2035-01-01').date())
            app.run()
            app.date_input[2].set_value(pd.Timestamp('2022-01-01').date()).run()
            gold=next(s for s in data[1] if s['dataset_id']=='gold' and s['signal_type']=='consecutive_increases')
            # Latest snapshot per episode is used in collect.
            app.button(key=gold['signal_id']).click().run()
            next(m for m in app.multiselect if m.label=='Compare datasets').set_value(['gold','dollar','silver'])
            next(b for b in app.button if b.label=='Begin comparison').click().run()
            self.assertEqual(app.session_state['radar_comparison']['keys'],['gold','dollar','silver'])
            self.assertEqual(app.session_state['radar_comparison']['start'],'2022-01-01')
            app.radio[0].set_value('Most unusual discoveries').run()
            self.assertEqual(app.session_state['radar_comparison']['keys'],['gold','dollar','silver'])
            # Query routing and existing navigation render in the full application.
            app.query_params['page']='Calendar'
            with patch.dict('os.environ',{'OPENAI_API_KEY':'test-only-not-a-live-key'}):
                app.run()
                self.assertEqual(len(app.exception),0)
                app.query_params['page']='DiscoveryRadar'
                app.run()
            self.assertEqual(len(app.exception),0)
