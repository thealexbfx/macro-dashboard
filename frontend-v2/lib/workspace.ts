import type { ChartMode, ChartType, Comparison, Dataset, Investigation, WorkspaceSettings } from './contracts';

const palette: Record<string,string> = {
    cpi:'#6399ff',core_cpi:'#b09aff',cpi_nsa:'#f1bd71',core_cpi_nsa:'#ee91cb',
    unemployment:'#4ed4b5',payrolls:'#65ceef',pce:'#e5d185',core_pce:'#abcc79',
    fed_funds:'#eaa28c',real_gdp_growth:'#ce9de8',us10y:'#8fb9eb',
    initial_claims:'#e8b35b',job_openings:'#8ac9ae',participation:'#90a9f8',hourly_earnings:'#df9ebd',breakeven_5y:'#b7cb7f',retail_sales:'#7cceca',real_consumption:'#b6a7e7',consumer_sentiment:'#e7bd8c',housing_starts:'#8ab5d4',building_permits:'#d3bc7d',mortgage_30y:'#b6d0e9',industrial_production:'#c6a1c5',yield_curve:'#a4bf93',high_yield_spread:'#e5a39b',investment_grade_spread:'#9dbdd5',
    sp500:'#ef93a4',gold:'#dbbf54',wti:'#9cbd78',dxy:'#9ba8f5',
};
export const seriesColor = (id:string) => palette[id] || '#c8d7e9';
export const defaultWorkspace = ():WorkspaceSettings => ({mode:'separate',chart_type:'line',layout:'stacked',axes:'shared',axis_assignment:{},recession:false,lead_lag:{dataset_id:'',periods:0,unit:'months'},hidden:[]});
export function readInvestigations(storage:Pick<Storage,'getItem'>):Investigation[]{
    const records:unknown=JSON.parse(storage.getItem('ml-research')||'[]');
    if(!Array.isArray(records))throw new Error('Existing research could not be read; it was not overwritten');
    return records;
}
export function appendInvestigation(storage:Pick<Storage,'getItem'|'setItem'>,record:Investigation):Investigation[]{
    // Read again at save time so another open tab's newly saved records survive.
    const next=[record,...readInvestigations(storage)];
    storage.setItem('ml-research',JSON.stringify(next));
    return next;
}
export function availableTypes(mode:ChartMode):ChartType[]{return mode==='scatter'?['scatter']:['line','area','bar'];}
export function changeMode(settings:WorkspaceSettings,mode:ChartMode):WorkspaceSettings {
    return {...settings,mode,chart_type:mode==='scatter'?'scatter':settings.chart_type==='scatter'?'line':settings.chart_type};
}
export function restoreWorkspace(investigation:Investigation):WorkspaceSettings {
    const w=investigation.workspace, defaults=defaultWorkspace();
    if(!w)return defaults;
    const mode:ChartMode=['overlay','separate','scatter'].includes(w.mode)?w.mode:'separate';
    const shift=w.lead_lag;
    return {...defaults,...w,mode,chart_type:availableTypes(mode).includes(w.chart_type)?w.chart_type:availableTypes(mode)[0],
        layout:w.layout==='grid'?'grid':'stacked',axes:w.axes==='dual'?'dual':'shared',
        axis_assignment:w.axis_assignment||{},hidden:investigation.datasets.every(id=>(w.hidden||[]).includes(id))?[]:(w.hidden||[]).filter(id=>investigation.datasets.includes(id)),
        lead_lag:shift&&investigation.datasets.includes(shift.dataset_id)&&Number.isInteger(shift.periods)&&Math.abs(shift.periods)<=12?shift:defaults.lead_lag};
}
export function commonFrequency(datasets:Dataset[]):string {
    return ['event','irregular','annual','quarterly','monthly','weekly','daily'].find(f=>datasets.some(d=>d.frequency===f))||'monthly';
}
export function shiftUnit(frequency:string):WorkspaceSettings['lead_lag']['unit']{
    return frequency==='weekly'?'weeks':frequency==='daily'?'calendar_days':frequency==='quarterly'?'quarters':'months';
}
export function shiftDescription(lead:WorkspaceSettings['lead_lag'],datasets:Dataset[]):string {
    if(!lead.periods)return 'No lead-lag shift';
    const name=datasets.find(d=>d.id===lead.dataset_id)?.name||lead.dataset_id;
    return `${name} ${lead.periods>0?'leads':'lags'} the other series by ${Math.abs(lead.periods)} ${lead.unit.replace('_',' ')}. Labels shifted ${lead.periods>0?'+':''}${lead.periods}; original source dates retained.`;
}
// Conservative: equal text alone is insufficient for unrelated index bases.
export function unitKey(series:Comparison['series'][number]):string{
    if(series.transformation==='indexed'||series.transformation==='standardized')return series.transformation;
    if(series.transformation==='level' && series.units==='index points')return `${series.units}:${series.id}`;
    if(series.transformation==='percent'||series.transformation==='pp')return `${series.units}:${series.native_frequency||'unspecified'}`;
    return series.units;
}
export function validateAxes(series:Comparison['series'],settings:WorkspaceSettings):string|null {
    if(settings.mode!=='overlay')return null;
    const groups=new Map<string,Set<string>>();
    for(const s of series){const axis=settings.axes==='dual'?(settings.axis_assignment[s.id]||'left'):'left';
        const group=groups.get(axis)||new Set<string>();group.add(unitKey(s));groups.set(axis,group);}
    if([...groups.values()].some(g=>g.size>1))return 'These series have different units or index bases. Choose indexed values, z-scores, separate charts, or explicitly assign compatible groups to left/right axes.';
    return null;
}
export interface ChartRow {time:number;date:string;values:Record<string,number|null>;sources:Record<string,string|null>;labels?:Record<string,string>}
export function mergeObservations(series:Comparison['series']):ChartRow[]{
    const rows=new Map<string,ChartRow>();
    for(const s of series)for(const o of s.observations){
        const key=o.event_id||s.native_frequency==='event'||s.native_frequency==='irregular'?`${s.id}:${o.key||o.date}`:o.date;
        const row=rows.get(key)||{time:Date.parse(o.date.includes('T')?o.date:`${o.date}T00:00:00Z`),date:o.date,values:{},sources:{},labels:{}};
        row.labels={...row.labels,[s.id]:o.native_label?`${o.native_label} · ${o.period_start} to ${o.period_end}${o.event_id?` · ${o.event_id}`:''}`:''};
        row.values[s.id]=o.value;row.sources[s.id]=s.source_dates?(s.source_dates[o.date]??null):o.date;rows.set(key,row);
    }
    return [...rows.values()].sort((a,b)=>a.time-b.time).map(row=>({...row,values:Object.fromEntries(series.map(s=>[s.id,row.values[s.id]??null]))}));
}
export function hoverValues(row:ChartRow,series:Comparison['series'],hidden:string[]){
    return series.filter(s=>!hidden.includes(s.id)).map(s=>({id:s.id,name:s.name,value:row.values[s.id]??null,units:s.units,transformation:s.transformation,native_label:row.labels?.[s.id],source_date:row.sources[s.id]??null}));
}

export function dualAxisSettings(settings:WorkspaceSettings,ids:string[]):WorkspaceSettings {
    return {...changeMode(settings,'overlay'),axes:'dual',axis_assignment:Object.fromEntries(ids.map((id,i)=>[id,i===0?'left':'right']))};
}
