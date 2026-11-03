import test from 'node:test';
import assert from 'node:assert/strict';
import {sparklineObservations,tooltipNumber,defaultRollingWindow,correlationInterpretation} from '../lib/presentation.ts';
import {dualAxisSettings,defaultWorkspace,validateAxes,mergeObservations} from '../lib/workspace.ts';
import {readFileSync} from 'node:fs';

test('compact sparklines connect valid sessions without changing source dates or null analytical cells',()=>{
 const observations=[{date:'2026-10-16',value:4.123456},{date:'2026-10-17',value:null},{date:'2026-10-18',value:null},{date:'2026-10-19',value:4.2},{date:'2026-10-20',value:null},{date:'2026-10-21',value:4.3}];
 const d={status:'ok',latest_observation_date:'2026-10-21',observations};const before=JSON.stringify(d);
 assert.deepEqual(sparklineObservations(d),[observations[0],observations[3],observations[5]]);
 assert.equal(JSON.stringify(d),before);
 const rows=mergeObservations([{id:'us10y',observations}]);assert.equal(rows.length,6);assert.equal(rows[1].values.us10y,null);
 assert.deepEqual(sparklineObservations({...d,status:'unavailable'}),[]);
 assert.deepEqual(sparklineObservations({...d,observations:[{date:'2026-10-21',value:null}]}),[]);
});
test('all observation tooltip values use exactly two decimals without changing precision',()=>{
 for(const [v,text] of [[1,'1.00'],[-.126,'-0.13'],[1234.56789,'1,234.57'],[0,'0.00'],[null,'Unavailable'],[undefined,'Unavailable'],[NaN,'Unavailable']])assert.equal(tooltipNumber(v),text);
 const source=1.123456789;tooltipNumber(source);assert.equal(source,1.123456789);
});
test('dual-axis action immediately assigns CPI left and unemployment right and retains research settings',()=>{
 const before={...defaultWorkspace(),recession:true,lead_lag:{dataset_id:'cpi',periods:6,unit:'months'}};
 const w=dualAxisSettings(before,['cpi','unemployment']);
 assert.equal(w.mode,'overlay');assert.equal(w.axes,'dual');assert.deepEqual(w.axis_assignment,{cpi:'left',unemployment:'right'});assert.deepEqual(w.lead_lag,before.lead_lag);assert.equal(w.recession,true);
 const series=[{id:'cpi',units:'Index 1982=100',transformation:'level'},{id:'unemployment',units:'Percent',transformation:'level'}];
 assert(validateAxes(series,{...w,axes:'shared'}));assert.equal(validateAxes(series,w),null);
});
test('frequency defaults and fixed descriptive correlation interpretation',()=>{
 assert.equal(defaultRollingWindow('daily'),60);assert.equal(defaultRollingWindow('monthly'),12);assert.equal(defaultRollingWindow('quarterly'),12);
 assert.match(correlationInterpretation(.8),/strong.*together/);assert.match(correlationInterpretation(-.5),/moderate.*opposite/);assert.match(correlationInterpretation(.05),/Little/);assert.match(correlationInterpretation(null),/Not enough/);
});
test('renderers preserve gap handling, bounded rolling scale, dated labels and consistent tooltip formatter',()=>{
 const charts=readFileSync(new URL('../components/research-charts.tsx',import.meta.url),'utf8');
 const workspace=readFileSync(new URL('../components/investigation-workspace.tsx',import.meta.url),'utf8');
 assert.match(charts,/connectNulls=\{false\}/);assert.match(charts,/Use left\/right Y-axes/);assert.match(charts,/tooltipNumber\(p.x\)/);assert.match(charts,/tooltipNumber\(s.value\)/);
 assert.match(workspace,/domain=\{\[-1,1\]\}/);assert.match(workspace,/ticks=\{\[-1,0,1\]\}/);assert.match(workspace,/minTickGap=\{42\}/);assert.match(workspace,/tooltipNumber\(v\)/);
});
