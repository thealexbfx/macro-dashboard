"""Registry/Today/workspace regression contracts; fixtures never reach production."""
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import Mock
import numpy as np
import pandas as pd
import pytest
from comparison_registry import COMPARISON_REGISTRY
from discovery import Dataset, Config, analyze
from discovery.radar import scan, ranked, DEFINITIONS


def test_roundoff_does_not_turn_identical_returns_into_anomalies():
    dates=pd.date_range('2024-01-01',periods=100,freq='D')
    frame=pd.DataFrame({'date':dates,'value':100*np.cumprod(np.full(100,1.003))})
    dataset=Dataset('fixture','D','USD','fixture','Asset','crypto','TEST','USD',adjustment='close')
    metrics,signals=analyze(frame,dataset,market=True)
    assert metrics.percentile.iloc[-1]==pytest.approx(.5)
    assert not any(s['family']=='single_series_anomaly' for s in signals)


def history(name,start,end):
    if name.startswith('United States'):
        dates=pd.date_range(start,end,freq='ME')
        values=3+np.arange(len(dates))*.01
    else:
        dates=pd.date_range(start,end,freq='D' if 'Bitcoin' in name else 'B')
        returns=np.where(np.arange(len(dates))%2,.003,-.003)
        if name=='Commodities · Gold': returns[-1]=-.025
        values=100*np.cumprod(1+returns)
    return pd.DataFrame({'date':dates,'value':values})


def test_registry_adapter_uses_sa_cpi_and_isolates_failures():
    def loader(name,start,end):
        if name=='United States · Unemployment Rate': raise RuntimeError('secret URL must not render')
        return history(name,start,end)
    signals,status=scan(loader,COMPARISON_REGISTRY)
    assert status['unemployment_sa']['unavailable']
    assert 'secret' not in str(status)
    cpi=next(s for s in signals if s['dataset_id']=='us_cpi_sa_yoy')
    assert cpi['data_source']['ticker']=='CPIAUCSL'
    assert cpi['actual_measured_change']['unit']=='percentage_points'
    assert 'seasonally' in DEFINITIONS['us_cpi_sa_yoy'].lower()
    assert any(s['dataset_id']=='gold' and s['signal_type']=='unusual_decrease' for s in signals)


def test_current_bar_excluded_missing_and_ranking():
    today=date.today()
    def loader(name,start,end):
        f=history(name,start,today)
        return f
    signals,status=scan(loader,COMPARISON_REGISTRY,today)
    assert all(s['observation_date']<str(today) for s in signals)
    for mode in ('Latest','Most unusual'):
        chosen=ranked(signals,mode,today-timedelta(days=90))
        assert len({s['dataset_id'] for s in chosen})==len(chosen)
    with pytest.raises(ValueError): ranked(signals,'invalid')


def test_episode_identity_reversals_magnitude_and_gap():
    values=[10]+[.1,-.1]*40+[1,1,1,1,-2,-2,-2]
    frame=pd.DataFrame({'date':pd.date_range('2010-01-31',periods=len(values),freq='ME'),'value':np.cumsum(values)})
    d=Dataset('rate','M','percent','fixture')
    _,signals=analyze(frame,d)
    trends=[s for s in signals if s['signal_type']=='consecutive_increases']
    assert trends[-1]['signal_id']==trends[-2]['signal_id']
    assert len(trends[-1]['trend_context']['observation_history'])==4
    assert trends[-1]['research_priority']['method']=='trend'
    assert any(s['signal_type']=='direction_reversal' for s in signals)
    _,quiet=analyze(frame,d,Config(reversal_minimum=10))
    assert not any(s['signal_type']=='direction_reversal' for s in quiet)
    frame.loc[len(frame)-3,'value']=np.nan
    metrics,_=analyze(frame,d)
    assert pd.isna(metrics.change.iloc[-2])


def test_full_today_gold_queue_save_and_restore(monkeypatch,tmp_path):
    from streamlit.testing.v1 import AppTest
    import components.chart_workspace as charts
    import components.discovery_radar as radar
    from macro_engine.research.notebook import save_investigation,load_investigations
    from datetime import datetime, timezone
    # The renderer uses UTC, whereas date.today() follows the host's local zone.
    # Freeze both sides so this workflow test also works across UTC midnight.
    as_of = date(2026, 10, 23)
    class FixedClock:
        @staticmethod
        def now(tz=None):
            return datetime(2026, 10, 23, 12, tzinfo=timezone.utc)
    monkeypatch.setattr(radar, 'datetime', FixedClock)
    monkeypatch.setattr(charts,'load_series',history)
    monkeypatch.setattr(charts,'load_investigations',lambda:load_investigations(tmp_path))
    monkeypatch.setattr(charts,'save_investigation',lambda payload,investigation_id=None:save_investigation(payload,tmp_path,investigation_id))
    radar.current_discoveries.clear()
    app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py')).run(timeout=30)
    signals,_=radar.current_discoveries(as_of)
    gold=next(s for s in ranked(signals,'Latest',as_of-timedelta(days=90)) if s['dataset_id']=='gold')
    app.button(key='discovery_'+gold['signal_id']).click().run(timeout=30)
    assert app.query_params['page']=='Investigate'
    assert app.query_params['left']=='Commodities · Gold'
    assert app.query_params['observation']==gold['observation_date']
    assert app.selectbox[0].value=='Commodities · Gold'
    assert app.selectbox[1].value=='FX · DXY'
    next(m for m in app.multiselect if m.label=='Related comparison queue').set_value(['FX · DXY','Commodities · Silver']).run()
    assert app.selectbox[1].value=='FX · DXY'
    next(b for b in app.button if b.label=='Save this comparison').click().run()
    next(r for r in app.radio if r.label=='Queued comparison').set_value('Commodities · Silver').run()
    assert app.selectbox[1].value=='Commodities · Silver'
    next(b for b in app.button if b.label=='Save this comparison').click().run()
    records=load_investigations(tmp_path)
    assert len(records)==2
    assert {r['right'] for r in records}=={'FX · DXY','Commodities · Silver'}
    assert all(r['start']==gold['start'] and r['end']==gold['end'] for r in records)
    assert all(r['schema_version']==1 and r['evidence']['source_csv'] for r in records)
    assert all(r['discovery']['observation_date']==gold['observation_date'] for r in records)
    app.query_params['page']='MyResearch'
    app.run()
    assert app.selectbox and not app.exception
    # Restore the unmodified existing saved-record route and evidence rendering.
    app.query_params.update(page='Investigate',record=records[0]['id'])
    app.run()
    assert not app.exception
    assert app.get('plotly_chart')
    radar.current_discoveries.clear()


def test_invalid_handoff_does_not_replace_workspace(monkeypatch):
    from streamlit.testing.v1 import AppTest
    import components.chart_workspace as charts
    monkeypatch.setattr(charts,'load_series',history)
    monkeypatch.setattr(charts,'load_investigations',lambda:[])
    app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'))
    app.query_params.update(page='Investigate',discovery='bad',start='not-a-date')
    app.run()
    assert not app.exception
    assert any('invalid' in w.value for w in app.warning)
    assert len(app.selectbox)==3
