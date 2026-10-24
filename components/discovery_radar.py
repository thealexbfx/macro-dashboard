"""Compact Today discovery surface; uses the existing chart-first workflow."""
from datetime import date, datetime, timezone, timedelta
import streamlit as st
from comparison_registry import COMPARISON_REGISTRY
from discovery.radar import scan, ranked, RELATED


@st.cache_data(ttl=900, show_spinner=False)
def current_discoveries(as_of):
    from components.chart_workspace import load_series
    return scan(load_series, COMPARISON_REGISTRY, as_of)


def render_discovery_radar():
    st.subheader('Discovery Radar')
    st.caption('Unusual changes and sustained trends. Observations, not explanations or predictions.')
    mode=st.radio('Discoveries', ['Latest','Most unusual'], horizontal=True, key='discovery_order')
    with st.spinner('Checking historical context…'):
        today=datetime.now(timezone.utc).date()
        signals,status=current_discoveries(today)
    chosen=ranked(signals,mode,today-timedelta(days=90))
    if not chosen:
        st.info('No discoveries in the last 90 days. See source status for unavailable or insufficient data.')
    for s in chosen:
        with st.container(border=True):
            st.markdown(f"**{s['name'].split(' · ')[-1]}** · {s['signal_type'].replace('_',' ')}")
            movement=s['actual_measured_change']
            st.write(f"{s['observation_date']} · {movement['value']:+.3f} {movement['unit']}")
            percentile=s['statistical_unusualness']['absolute_change_percentile']
            st.caption(f"Historical absolute-change percentile: {percentile:.1%}" if percentile is not None else 'Insufficient prior history for unusualness')
            st.caption(f"Consecutive moves: {s['trend_context']['consecutive_movements']} · Latest source observation: {s['freshness']['latest']} · {s['freshness']['source']}" + (' · possibly stale' if s['freshness']['stale'] else ''))
            with st.expander('Why flagged / methodology'):
                st.json(s)
            if st.button('Investigate', key='discovery_'+s['signal_id']):
                queue=[name for name,_ in RELATED.get(s['dataset_id'],[]) if name in COMPARISON_REGISTRY]
                st.session_state['discovery_context']={**s, 'queue':queue}
                st.query_params.clear()
                st.query_params.update(page='Investigate',left=s['name'],right=queue[0] if queue else 'Rates & Bonds · US 10Y',
                                       discovery=s['signal_id'],observation=s['observation_date'],start=s['start'],end=s['end'])
                st.rerun()
    with st.expander('Source status and limitations'):
        st.json(status)
        st.caption('Today’s UTC-dated bars are excluded. Weekday holidays create conservative gaps. Release dates and revision vintages are unavailable. Gold is GC=F futures, not spot/ETF. CPI is explicitly seasonally adjusted YoY. Priority is research triage, not predictive confidence.')
        st.caption('Real-yield and breakeven suggestions are not registered in this chart workspace; nominal US 10Y is not a substitute for either.')
