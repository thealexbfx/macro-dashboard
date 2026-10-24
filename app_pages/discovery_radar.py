"""Discovery Radar uses the site's shared charts and real provider adapters."""
from datetime import date, timedelta
import streamlit as st
from discovery.radar import CATALOG, RELATIONSHIPS, collect, load_series, select_discoveries
from components.charts import plot_chart, plot_comparison_chart

@st.cache_data(ttl=300, show_spinner=False)
def radar_data(start,end):
    return collect(start,end)

@st.cache_data(ttl=1800, show_spinner=False)
def related_data(key,start,end):
    return load_series(key,start,end)

def render_discovery_radar():
    st.markdown('## Discovery Radar')
    st.caption('Ranked observations for independent research · priority is not predictive confidence')
    st.info('Market bars dated today are excluded. Economic dates identify reference periods, not release dates; release timestamps and revision vintages are unavailable. Weekday calendars conservatively show holiday gaps.')
    with st.expander('Scan coverage and date range'):
        start=st.date_input('History begins',date.today()-timedelta(days=1095),key='radar_start')
        end=st.date_input('History ends (exclusive)',date.today(),key='radar_end')
        if st.button('Refresh provider data'):
            radar_data.clear(); related_data.clear()
            from data.bls import get_bls_series
            from data.fred import get_fred_series
            get_bls_series.clear(); get_fred_series.clear()
            st.caption('Memory caches cleared. Fresh BLS disk snapshots remain reusable for one day.')
    if start>=end:
        st.warning('Choose an end date after the start date.'); return
    with st.spinner('Scanning provider history…'):
        frames,signals,status=radar_data(str(start),str(end))
    for key,state in status.items():
        if 'error' in state: st.warning(f"{CATALOG[key][0]} unavailable: {state['error']}")
        elif state['stale']: st.warning(f"{CATALOG[key][0]} may be stale. Latest observation: {state['latest']}")
    with st.expander('Data-source status and definitions'):
        from config import BLS_API_KEY, FRED_API_KEY
        st.json({'BLS_registration_configured':bool(BLS_API_KEY),'FRED_key_configured':bool(FRED_API_KEY),'radar_cache_seconds':300,'BLS_disk_cache_days':1,'BLS_attempt_limit':3})
        st.caption('CPI: NSA CPI-U index transformed to YoY percent. Unemployment: seasonally adjusted U-3 percent. Changes in both displayed rates are percentage points. FRED fallback, cached data and failure reasons are identified below.')
        st.json(status)
    a,b=st.columns(2)
    categories=a.multiselect('Category',['Markets','Economy'],default=['Markets','Economy'])
    options=sorted({s['signal_type'] for s in signals})
    types=b.multiselect('Signal type',options,default=options)
    order=st.radio('Discovery ranking',['Latest discoveries','Most unusual discoveries'],horizontal=True)
    since=st.date_input('Discoveries since',max(start,end-timedelta(days=90)),min_value=start,max_value=end)
    chosen=select_discoveries(signals,categories,types,since,end,order=order)
    st.caption('Up to five distinct datasets. Latest sorts by observation date, then priority; Most unusual sorts by the family-specific historical percentile. Continuing trends are grouped.')
    if not chosen: st.info('No discoveries match this window. Widen the date range or check provider availability.')
    for s in chosen:
        with st.container(border=True):
            name=CATALOG[s['dataset_id']][0]
            st.markdown(f"**{name}** · {s['signal_type'].replace('_',' ').title()}")
            change=s['actual_measured_change']
            st.write(f"{s['observation_date']} · {change['value']:+.3f} {change['unit']} · Research priority {s['research_priority']['score']:.0f}/100")
            percentile=s['statistical_unusualness']['absolute_change_percentile']
            st.caption(f"Absolute-change historical percentile: {percentile:.1%}" if percentile is not None else 'Historical unusualness unavailable: insufficient baseline')
            st.caption(f"Consecutive movements: {s['trend_context']['consecutive_movements']} · Latest provider observation: {s['freshness']['latest_observation']} · Source: {s['data_source']['source']}")
            if st.button('Investigate',key=s['signal_id']): st.session_state['radar_investigation']=s
    s=st.session_state.get('radar_investigation')
    if not s: return
    key=s['dataset_id']
    st.divider()
    st.markdown(f"### Investigate · {CATALOG[key][0]}")
    st.write(f"Flagged by {s['signal_type'].replace('_',' ')} using prior observations only. Observation: {s['observation_date']}.")
    if key in frames:
        chart=plot_chart(frames[key],CATALOG[key][0],'Line')
        chart.add_vline(x=s['observation_date'],line_dash='dot',line_color='#c27818')
        st.plotly_chart(chart,use_container_width=True)
    with st.expander('Calculation evidence and methodology'):
        st.json(s)
    st.markdown('#### Related datasets')
    suggestions=RELATIONSHIPS.get(key,[])
    for related,rationale in suggestions:
        st.caption(f'{CATALOG[related][0]} — {rationale}')
    allowed=[key]+[k for k,_ in suggestions]
    selection=st.multiselect('Compare datasets',allowed,default=[key],format_func=lambda k:CATALOG[k][0],key='radar_compare_'+key)
    if st.button('Begin comparison'):
        st.session_state['radar_comparison']={'keys':selection,'start':str(start),'end':str(end)}
    comparison=st.session_state.get('radar_comparison')
    if comparison:
        st.markdown('#### Chart comparison')
        st.caption(f"{comparison['start']} to {comparison['end']} (exclusive). Native units and frequencies; no filling, resampling, or contemporaneous-release assumption.")
        series={}
        for k in comparison['keys']:
            try:
                f,source=related_data(k,comparison['start'],comparison['end'])
                series[CATALOG[k][0]]=f
                st.caption(f"{CATALOG[k][0]} · {source} · latest {f.date.max().date()}")
            except Exception as exc: st.warning(f'{CATALOG[k][0]} unavailable: {exc}')
        if series: st.plotly_chart(plot_comparison_chart(series),use_container_width=True)
