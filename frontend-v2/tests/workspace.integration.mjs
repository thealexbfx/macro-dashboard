// Real providers through the isolated API. These are not fixture/statistical proofs.
import test from 'node:test';
import assert from 'node:assert/strict';
import {validateAxes,defaultWorkspace} from '../lib/workspace.ts';
const origin=process.env.MACROLENS_V2_API_URL||'http://127.0.0.1:8016';
async function compare(extra={}){
 const r=await fetch(`${origin}/api/v2/compare`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({datasets:['cpi_nsa','core_cpi_nsa'],start:'2020-01-01',end:'2025-12-31',transformations:{cpi_nsa:'yoy',core_cpi_nsa:'yoy'},alignment:'native',rolling_window:12,...extra}),signal:AbortSignal.timeout(45000)});
 assert.equal(r.status,200,await r.clone().text());return r.json();
}
test('real annual CPI/core CPI are compatible overlay and exact scatter inputs',{timeout:60000},async()=>{
 const data=await compare();assert.equal(validateAxes(data.series,{...defaultWorkspace(),mode:'overlay'}),null);
 assert.equal(data.scatter.length,data.statistics[0].observations);
 for(const p of data.scatter){assert.equal(p.x,data.series[0].observations.find(o=>o.date===p.date).value);assert.equal(p.y,data.series[1].observations.find(o=>o.date===p.date).value);}
});
test('real indexed and standardized market comparisons preserve common units',{timeout:60000},async()=>{
 for(const mode of ['indexed','standardized']){const d=await compare({datasets:['gold','dxy'],transformations:{gold:mode,dxy:mode}});assert.equal(validateAxes(d.series,{...defaultWorkspace(),mode:'overlay'}),null);assert(d.scatter.length>1000);if(mode==='indexed')assert(d.series.every(s=>s.observations.find(o=>o.value!==null).value===100));}
});
test('real monthly lead-lag keeps original references and recalculates paired samples',{timeout:60000},async()=>{
 const base=await compare({datasets:['cpi_nsa','unemployment'],transformations:{cpi_nsa:'yoy'}});
 const shifted=await compare({datasets:['cpi_nsa','unemployment'],transformations:{cpi_nsa:'yoy'},lead_lag:{dataset_id:'cpi_nsa',periods:6,unit:'months'}});
 assert(shifted.scatter.length<base.scatter.length);
 assert.equal(shifted.scatter.length,shifted.statistics[0].observations);
 for(const o of shifted.series[0].observations){const original=shifted.series[0].source_dates[o.date];if(original)assert.equal(o.value,base.series[0].observations.find(p=>p.date===original).value);}
 assert(shifted.statistics[0].rolling.length>0);
});
test('real mixed-frequency common-quarter sampling retains source references',{timeout:60000},async()=>{
 const r=await compare({datasets:['cpi_nsa','real_gdp_growth'],transformations:{cpi_nsa:'yoy'},alignment:'period_end',lead_lag:{dataset_id:'cpi_nsa',periods:1,unit:'quarters'}});
 assert.equal(r.statistics[0].frequency,'quarterly');assert(r.series[0].source_dates['2020-06-30']);
 assert(r.scatter.every(p=>p.date>='2020-01-01'&&p.date<='2025-12-31'));
});
test('real FRED USREC shading matches the recorded March-April 2020 recession',{timeout:60000},async()=>{
 const response=await fetch(`${origin}/api/v2/context/recessions?start=2019-01-01&end=2021-12-31`,{signal:AbortSignal.timeout(45000)});assert.equal(response.status,200);const d=await response.json();
 assert.equal(d.source_id,'USREC');assert.equal(d.source_url,'https://fred.stlouisfed.org/series/USREC');
 assert.deepEqual(d.periods.map(p=>[p.start,p.end]),[['2020-03-01','2020-04-30']]);assert(d.retrieved_at);assert(d.latest_reference>='2026-09-01');
});
