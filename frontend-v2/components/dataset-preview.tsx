'use client';
import {chartTheme} from '../lib/chart-theme';
import {CartesianGrid,ComposedChart,Line,ResponsiveContainer,Scatter,Tooltip,XAxis,YAxis} from 'recharts';
import type {Dataset,Observation} from '../lib/contracts';
import {dateLabel,tooltipNumber} from '../lib/presentation';
import {seriesColor} from '../lib/workspace';
export function DatasetPreview({dataset:d}:{dataset:Dataset}){
 const points=d.observations.map(o=>({...o,time:Date.parse(o.date)}));
 if(!points.some(o=>o.value!==null))return <p className="quiet">No observations available for this preview.</p>;
 return <figure className="ml-dataset-preview"><figcaption>{d.units} · Recent observations</figcaption><div role="img" aria-label={`Preview of ${d.name}`}><ResponsiveContainer width="100%" height="100%"><ComposedChart data={points} accessibilityLayer margin={{top:12,right:12,bottom:8,left:0}}><CartesianGrid vertical={false} stroke={chartTheme.grid} strokeDasharray="2 5"/><XAxis dataKey="time" type="number" domain={['dataMin','dataMax']} tickFormatter={v=>dateLabel(new Date(v).toISOString().slice(0,10))} minTickGap={70} tick={{fill:chartTheme.text,fontSize:10}} tickLine={false} axisLine={false}/><YAxis hide domain={['auto','auto']}/><Tooltip content={({active,payload})=>{const o=payload?.[0]?.payload as Observation|undefined;return active&&o?<div className="chart-tooltip"><b>{o.native_label||dateLabel(o.date)}</b><p>{o.value===null?'Missing':tooltipNumber(o.value)} {d.units}</p><small>{o.date}{o.event_id?` · ${o.event_id}`:''}</small></div>:null;}}/>{['event','irregular'].includes(d.frequency)?<Scatter dataKey="value" fill={seriesColor(d.id)} isAnimationActive={false}/>:<Line dataKey="value" stroke={seriesColor(d.id)} strokeWidth={1.8} dot={points.length<3} connectNulls={false} isAnimationActive={false}/>}</ComposedChart></ResponsiveContainer></div><p>Source observations only. No values filled in.</p></figure>;
}
