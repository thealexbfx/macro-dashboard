// Explicit opt-in command: npm run test:integration. These tests contact real providers
// through a running isolated V2 backend; no fixtures or synthetic fallbacks are used.
import test from 'node:test';
import assert from 'node:assert/strict';
import {TIMEFRAMES,timeframeStart,marketMovement,formatDatasetValue} from '../lib/presentation.ts';
const origin=process.env.MACROLENS_V2_API_URL||'http://127.0.0.1:8016';
const end=new Date(Date.now()-86400000).toISOString().slice(0,10);
const sizes=[];
async function compare(start,end){const response=await fetch(`${origin}/api/v2/compare`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({datasets:['gold','dxy'],start,end,transformations:{},alignment:'native',rolling_window:12}),signal:AbortSignal.timeout(45000)});assert.equal(response.status,200,await response.clone().text());return response.json()}
for(const timeframe of TIMEFRAMES){test(`real observations and statistics respect ${timeframe}`,{timeout:60000},async()=>{const start=timeframeStart(timeframe,end);const result=await compare(start,end);for(const s of result.series){assert(s.observations.length>0);assert(s.observations.every(o=>o.date>=start&&o.date<=end));}assert(result.statistics[0].observations>2);assert(Number.isFinite(result.statistics[0].correlation));sizes.push(result.series[0].observations.length);});}
test('all eight preset windows produce different real sample sizes',()=>assert.equal(new Set(sizes).size,8));
test('custom historical dates bound charts and statistics',{timeout:60000},async()=>{const result=await compare('2024-01-01','2024-12-31');for(const s of result.series)assert(s.observations.every(o=>o.date>='2024-01-01'&&o.date<='2024-12-31'));assert(result.statistics[0].start>='2024-01-01');assert(result.statistics[0].end<='2024-12-31');});
test('market widget changes reconcile with backend source differences',{timeout:60000},async()=>{const response=await fetch(`${origin}/api/v2/datasets`,{signal:AbortSignal.timeout(45000)});assert.equal(response.status,200);const data=await response.json();for(const id of ['sp500','gold','us10y','dxy','wti']){const d=data.find(d=>d.id===id);assert.notEqual(d.status,'unavailable',`${id} provider unavailable`);const move=marketMovement(d);assert(Number.isFinite(move.value));const previous=d.observations.find(o=>o.date===d.previous_observation_date).value;const expected=d.change_units==='percentage points'?d.change*100:d.change_units==='percent'?d.change:100*d.change/previous;assert(Math.abs(expected-move.value)<1e-8,`${id} display change does not match backend source values`);assert.match(formatDatasetValue(d),/\d[,.]\d{2}%?$/);}});

test('real economic headlines reconcile with dated releases and Investigate', {timeout:60000}, async()=>{
 const data=await (await fetch(`${origin}/api/v2/datasets`)).json();
 for(const [id,expected,decimals] of [['payrolls',29000,0],['cpi_nsa',3.7,1],['core_cpi_nsa',2.6,1],['real_gdp_growth',2.2,1]]){
  const d=data.find(d=>d.id===id); assert(d,`Missing ${id}`);
  assert.equal(Number(d.headline.value.toFixed(decimals)),expected);
  assert.equal(d.verification.headline_reconciliation.difference_at_release_precision,0);
  const result=await (await fetch(`${origin}/api/v2/compare`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({datasets:[id],start:'2025-01-01',end,transformations:{[id]:d.headline.transformation},alignment:'native',rolling_window:12})})).json();
  const last=result.series[0].observations.find(o=>o.date===d.headline.reference_period);
  assert.equal(last.value,d.headline.value,`${id}: Today / Investigate mismatch`);
 }
});
test('real market prices retain independent-verification limits',async()=>{
 const data=await (await fetch(`${origin}/api/v2/datasets`)).json();
 for(const id of ['gold','wti','sp500','dxy']){const d=data.find(d=>d.id===id);assert.equal(d.verification.raw_status,'Unverified');assert(d.provider_metadata);}
});
