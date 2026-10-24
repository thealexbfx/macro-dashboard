import unittest
from unittest.mock import patch
import pandas as pd
import numpy as np
from discovery.radar import collect, select_discoveries, load_series, RELATIONSHIPS, CATALOG
from components.charts import plot_comparison_chart

def fixture(key,start,end):
    freq='ME' if key in ('unemployment','inflation') else 'D' if key=='bitcoin' else 'B'
    dates=pd.date_range('2022-01-01',periods=100,freq=freq)
    return pd.DataFrame({'date':dates,'value':100+np.cumsum([.1,-.1]*48+[1,2,3,4])}),'test fixture'

class RadarTests(unittest.TestCase):
    def test_failure_isolation_and_distinct_rank(self):
        def loader(key,start,end):
            if key=='unemployment': raise RuntimeError('outage')
            return fixture(key,start,end)
        frames,signals,status=collect('2022-01-01','2035-01-01',loader,now='2036-01-01T00:00:00Z')
        self.assertIn('error',status['unemployment'])
        result=select_discoveries(signals,['Markets','Economy'],{s['signal_type'] for s in signals},'2022-01-01','2035-01-01')
        self.assertLessEqual(len(result),5)
        self.assertEqual(len(result),len({s['dataset_id'] for s in result}))
        self.assertTrue(all(s['freshness']['stale'] for s in result))
        self.assertEqual(select_discoveries(signals,[],[],'2022-01-01','2035-01-01'),[])

    def test_relationships_and_native_chart(self):
        for key,pairs in RELATIONSHIPS.items():
            self.assertIn(key,CATALOG)
            for other,rationale in pairs:
                self.assertIn(other,CATALOG); self.assertGreater(len(rationale),20)
        frame,_=fixture('gold',None,None)
        chart=plot_comparison_chart({'Gold':frame,'Other':frame.iloc[::20]})
        self.assertEqual(len(chart.data[1].x),5)
        self.assertFalse(chart.data[0].connectgaps)

    def test_cpi_month_matching(self):
        f=pd.DataFrame({'date':pd.date_range('2019-01-31',periods=25,freq='ME'),'value':[100]*12+[110]*13})
        with patch('data.bls.get_bls_series',return_value=f):
            result,_=load_series('inflation','2020-01-01','2021-02-01')
        self.assertAlmostEqual(result.value.iloc[1],10)

    def test_ui_investigate_compare(self):
        from streamlit.testing.v1 import AppTest
        # Fixtures are test-only. Production has no fixture/demo fallback.
        with patch('app_pages.discovery_radar.radar_data',return_value=collect('2022-01-01','2035-01-01',fixture,now='2036-01-01T00:00:00Z')), patch('app_pages.discovery_radar.related_data',side_effect=fixture):
            app=AppTest.from_string('from app_pages.discovery_radar import render_discovery_radar\nrender_discovery_radar()').run()
            app.date_input[0].set_value(pd.Timestamp('2022-01-01').date())
            app.date_input[1].set_value(pd.Timestamp('2035-01-01').date())
            app.run()
            app.date_input[2].set_value(pd.Timestamp('2022-01-01').date()).run()
            investigate=next(b for b in app.button if b.label=='Investigate')
            investigate.click().run()
            self.assertIn('radar_investigation',app.session_state)
            next(b for b in app.button if b.label=='Begin comparison').click().run()
            self.assertIn('radar_comparison',app.session_state)
            self.assertEqual(len(app.exception),0)
