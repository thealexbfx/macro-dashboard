import type { ChartMode, ChartType, Comparison, Dataset, Investigation, WorkspaceSettings } from './contracts';

const palette: Record<string,string> = {
    cpi:'#6399ff',core_cpi:'#b09aff',cpi_nsa:'#f1bd71',core_cpi_nsa:'#ee91cb',
    unemployment:'#4ed4b5',payrolls:'#65ceef',pce:'#e5d185',core_pce:'#abcc79',
    fed_funds:'#eaa28c',real_gdp_growth:'#ce9de8',us10y:'#8fb9eb',
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
    return ['quarterly','monthly','daily'].find(f=>datasets.some(d=>d.frequency===f))||'monthly';
}
export function shiftUnit(frequency:string):WorkspaceSettings['lead_lag']['unit']{
    return frequency==='daily'?'calendar_days':frequency==='quarterly'?'quarters':'months';
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
export interface ChartRow {time:number;date:string;values:Record<string,number|null>;sources:Record<string,string|null>}
export function mergeObservations(series:Comparison['series']):ChartRow[]{
    const rows=new Map<string,ChartRow>();
    for(const s of series)for(const o of s.observations){
        const row=rows.get(o.date)||{time:Date.parse(`${o.date}T00:00:00Z`),date:o.date,values:{},sources:{}};
        row.values[s.id]=o.value;row.sources[s.id]=s.source_dates?(s.source_dates[o.date]??null):o.date;rows.set(o.date,row);
    }
    return [...rows.values()].sort((a,b)=>a.time-b.time).map(row=>({...row,values:Object.fromEntries(series.map(s=>[s.id,row.values[s.id]??null]))}));
}
export function hoverValues(row:ChartRow,series:Comparison['series'],hidden:string[]){
    return series.filter(s=>!hidden.includes(s.id)).map(s=>({id:s.id,name:s.name,value:row.values[s.id]??null,units:s.units,transformation:s.transformation,source_date:row.sources[s.id]??null}));
}

export function dualAxisSettings(settings:WorkspaceSettings,ids:string[]):WorkspaceSettings {
    return {...changeMode(settings,'overlay'),axes:'dual',axis_assignment:Object.fromEntries(ids.map((id,i)=>[id,i===0?'left':'right']))};
}
