'use client';
import { useMemo } from 'react';
import { Area, Bar, CartesianGrid, ComposedChart, Line, ReferenceArea, ReferenceLine, ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis } from 'recharts';
import type { Comparison, HistoricalContext, WorkspaceSettings } from '../lib/contracts';
import { transformationLabel } from '../lib/contracts';
import { dateLabel, formatNumber, tooltipNumber } from '../lib/presentation';
import { dualAxisSettings, hoverValues, mergeObservations, seriesColor, validateAxes, type ChartRow } from '../lib/workspace';

const tickNumber=(v:number)=>new Intl.NumberFormat('en-US',{notation:Math.abs(v)>=1000?'compact':'standard',maximumFractionDigits:Math.abs(v)<.01?4:2}).format(v);
const tickDate=(v:number)=>new Date(v).toLocaleDateString('en-GB',{month:'short',year:'2-digit',timeZone:'UTC'});
const tickStyle={fill:'#9eB3ce',fontSize:12};

function ValuesTooltip({row,series,hidden,analytical}:{row?:ChartRow;series:Comparison['series'];hidden:string[];analytical:boolean}){
    if(!row)return null;
    return <div className="chart-tooltip workspace-tooltip"><b>{analytical?'Comparison date':'Observation date'} · {dateLabel(row.date)}</b>{hoverValues(row,series,hidden).map(s=><div className="tooltip-series" key={s.id} style={{color:seriesColor(s.id)}}><strong>{s.name}</strong><span>{s.value===null?'Missing observation':tooltipNumber(s.value)} {s.value!==null&&s.units}</span><small>{transformationLabel(s.transformation,series.find(v=>v.id===s.id)?.horizon_observations)}{s.source_date&&s.source_date!==row.date?` · Source reference ${s.source_date}`:''}</small></div>)}<small>Values shown to two decimals · Missing observations stay empty</small></div>;
}

export function ResearchCharts({comparison,settings,start,end,context,onSettings,onTransform}:{comparison:Comparison;settings:WorkspaceSettings;start:string;end:string;context:HistoricalContext|null;onSettings:(s:WorkspaceSettings)=>void;onTransform:(t:'standardized'|'indexed')=>void}){
    const rows=useMemo(()=>mergeObservations(comparison.series),[comparison]);
    const lookup=useMemo(()=>new Map(rows.map(r=>[r.time,r])),[rows]);
    const visible=comparison.series.filter(s=>!settings.hidden.includes(s.id));
    const axesError=validateAxes(visible,settings);
    const analytical=Boolean(comparison.lead_lag?.periods)||comparison.alignment==='period_end';
    const domain:[number,number]=[Date.parse(`${start}T00:00:00Z`),Date.parse(`${end}T00:00:00Z`)];
    const axisFor=(id:string)=>settings.axes==='dual'?(settings.axis_assignment[id]||'left'):'left';

    function chart(series:Comparison['series'],sync=true){
        const dual=settings.mode==='overlay'&&settings.axes==='dual';
        const axisSeries=(axis:string)=>series.find(s=>!dual||axisFor(s.id)===axis);
        const axisLabel=(axis:string)=>{const s=axisSeries(axis);return s?{value:s.units,angle:axis==='left'?-90:90,position:axis==='left'?'insideLeft' as const:'insideRight' as const,fill:seriesColor(s.id),fontSize:11}:undefined;};
        return <ResponsiveContainer width="100%" height="100%"><ComposedChart data={rows} syncId={sync?'macrolens-research':undefined} syncMethod="value" margin={{top:16,right:dual?12:20,bottom:8,left:2}} accessibilityLayer>
            <CartesianGrid stroke="#25364c" vertical={false} strokeDasharray="3 5"/>
            <XAxis dataKey="time" type="number" scale="time" domain={domain} allowDataOverflow tickFormatter={tickDate} tick={tickStyle} minTickGap={34} axisLine={false} tickLine={false} tickMargin={10}/>
            <YAxis yAxisId="left" tickFormatter={tickNumber} tick={{...tickStyle,fill:dual?seriesColor(axisSeries('left')?.id||''):tickStyle.fill}} label={dual?axisLabel('left'):undefined} width={86} domain={settings.chart_type==='bar'?[(v:number)=>Math.min(0,v),(v:number)=>Math.max(0,v)]:['auto','auto']} axisLine={false} tickLine={false}/>
            {dual&&<YAxis yAxisId="right" orientation="right" tickFormatter={tickNumber} tick={{...tickStyle,fill:seriesColor(axisSeries('right')?.id||'')}} label={axisLabel('right')} width={86} domain={settings.chart_type==='bar'?[(v:number)=>Math.min(0,v),(v:number)=>Math.max(0,v)]:['auto','auto']} axisLine={false} tickLine={false}/>}
            {context?.periods.map(p=><ReferenceArea key={p.id} yAxisId="left" x1={Date.parse(`${p.start}T00:00:00Z`)} x2={Date.parse(`${p.end}T00:00:00Z`)} fill="#afbfdd" fillOpacity={.10} strokeOpacity={0} ifOverflow="hidden"/>)}
            {settings.chart_type==='bar'&&<ReferenceLine yAxisId="left" y={0} stroke="#60758f"/>}
            <Tooltip filterNull={false} cursor={{stroke:'#9ab9e0',strokeDasharray:'3 4'}} content={({active,label})=>active?<ValuesTooltip row={lookup.get(Number(label))} series={comparison.series} hidden={settings.hidden} analytical={analytical}/>:null}/>
            {series.map(s=>{const props={dataKey:(r:ChartRow)=>r.values[s.id],name:s.name,yAxisId:dual?axisFor(s.id):'left',stroke:seriesColor(s.id),fill:seriesColor(s.id),isAnimationActive:false};
                return settings.chart_type==='bar'?<Bar {...props} key={s.id} fillOpacity={.75} maxBarSize={16}/>:settings.chart_type==='area'?<Area {...props} key={s.id} type="linear" fillOpacity={.10} strokeWidth={1.8} dot={false} connectNulls={false} baseValue="dataMin"/>:<Line {...props} key={s.id} type="linear" strokeWidth={1.8} dot={rows.length<40?{r:2,strokeWidth:0}:false} activeDot={{r:4}} connectNulls={false}/>;
            })}
        </ComposedChart></ResponsiveContainer>;
    }

    if(settings.mode==='scatter'){
        if(comparison.series.length!==2)return <div className="workspace-empty">Select exactly two datasets for a scatter comparison.</div>;
        const [x,y]=comparison.series,points=comparison.scatter||[],stat=comparison.statistics[0];
        return <section aria-label="Scatter comparison"><div className="scatter-labels"><span style={{color:seriesColor(x.id)}}>X · {x.name}<small>{x.units} · {transformationLabel(x.transformation,x.horizon_observations)}</small></span><span style={{color:seriesColor(y.id)}}>Y · {y.name}<small>{y.units} · {transformationLabel(y.transformation,y.horizon_observations)}</small></span><b>Pearson r {formatNumber(stat?.correlation,3)}<small>{points.length} paired observations</small></b></div>{points.length?<div className="workspace-chart scatter-chart" role="img" aria-label={`Scatter plot of ${x.name} against ${y.name}, ${points.length} paired observations`}><ResponsiveContainer width="100%" height="100%"><ScatterChart margin={{top:18,right:30,bottom:22,left:12}} accessibilityLayer><CartesianGrid stroke="#25364c" strokeDasharray="3 5"/><XAxis dataKey="x" type="number" name={x.name} domain={['auto','auto']} tickFormatter={tickNumber} tick={tickStyle} tickLine={false} label={{value:`X · ${x.units}`,position:'insideBottom',offset:-12,fill:'#93acca',fontSize:12}}/><YAxis dataKey="y" type="number" name={y.name} domain={['auto','auto']} width={74} tickFormatter={tickNumber} tick={tickStyle} tickLine={false}/><Tooltip cursor={{stroke:'#8199b9',strokeDasharray:'3 4'}} content={({active,payload})=>{const p=payload?.[0]?.payload as NonNullable<Comparison['scatter']>[number];return active&&p?<div className="chart-tooltip"><b>{analytical?'Comparison period':'Paired period'} · {dateLabel(p.date)}</b><div style={{color:seriesColor(x.id)}}>{x.name}: {tooltipNumber(p.x)} {x.units}<small>Source reference {p.x_source_date||'Unknown'}</small></div><div style={{color:seriesColor(y.id)}}>{y.name}: {tooltipNumber(p.y)} {y.units}<small>Source reference {p.y_source_date||'Unknown'}</small></div><small>Correlation does not establish causation</small></div>:null;}}/><Scatter data={points} fill="#7daaff" fillOpacity={.75} isAnimationActive={false}/></ScatterChart></ResponsiveContainer></div>:<div className="workspace-empty">No overlapping observations for this range and shift. Try a longer timeframe.</div>}<p className="quiet">Each point is an exact aligned pair, with its source dates in the tooltip. Correlation is descriptive, not causal or predictive evidence.</p></section>;
    }

    return <><div className="workspace-legend" aria-label="Chart series visibility">{comparison.series.map(s=>{const active=!settings.hidden.includes(s.id);return <button key={s.id} aria-pressed={active} disabled={active&&visible.length===1} onClick={()=>onSettings({...settings,hidden:active?[...settings.hidden,s.id]:settings.hidden.filter(id=>id!==s.id)})} title="Show or hide this series; calculations still use all selected datasets" className={!active?'series-hidden':''}><i style={{background:seriesColor(s.id)}}/>{s.name}<small>{s.units}{s.native_frequency?` · ${s.native_frequency}`:''}{s.shift_periods?` · shifted ${s.shift_periods>0?'+':''}${s.shift_periods} ${s.shift_unit}`:''}{settings.mode==='overlay'&&settings.axes==='dual'?` · ${axisFor(s.id)} axis`:''}</small></button>;})}</div>
        {axesError?<div role="alert" className="axis-warning"><b>Choose a comparison scale</b><p>These datasets need different scales. Choose how to compare them.</p><div className="axis-actions">{comparison.series.length===2&&<button onClick={()=>onSettings(dualAxisSettings(settings,comparison.series.map(s=>s.id)))}>Use left/right Y-axes</button>}{comparison.datasets.every(d=>d.allowed_transformations.includes('standardized'))&&<button onClick={()=>onTransform('standardized')}>Standardize both datasets</button>}{comparison.datasets.every(d=>d.allowed_transformations.includes('indexed'))&&<button onClick={()=>onTransform('indexed')}>Index to 100</button>}<button onClick={()=>onSettings({...settings,mode:'separate'})}>Show separate charts</button></div></div>:<>
            {settings.mode==='overlay'&&settings.axes==='dual'&&<p className="axis-warning">Independent scales can exaggerate relationships. Matching slopes do not imply matching changes.</p>}
            {settings.mode==='overlay'?<div className="workspace-chart" role="img" aria-label="Overlay chart">{rows.length?chart(visible):<div className="workspace-empty">No observations in this range.</div>}</div>:<div className={`workspace-panels ${settings.layout==='grid'?'workspace-grid':'workspace-stacked'}`}>{visible.map(s=><section key={s.id} className="workspace-panel"><div className="panel-heading"><b style={{color:seriesColor(s.id)}}>{s.name}</b><span>{s.units} · {transformationLabel(s.transformation,s.horizon_observations)}{s.native_frequency?` · ${s.native_frequency}`:''}</span></div><div className="workspace-chart" role="img" aria-label={`${s.name} chart`}>{s.observations.some(o=>o.value!==null)?chart([s]):<div className="workspace-empty">No observations for this dataset in the selected range.</div>}</div></section>)}</div>}
            <p className="quiet chart-caption">{settings.chart_type==='bar'?'Bars use a zero baseline.':'Axes adapt to the selected values; inspect axis labels when comparing amplitudes.'} {settings.chart_type==='area'?'Area fill begins at the displayed data minimum; it does not encode a total.':''} {settings.mode==='separate'?'Charts share the same date range and synchronized crosshair.':''} Visibility changes charts only; statistics use all selected datasets.</p>
        </>}
    </>;
}
