import test from 'node:test';
import assert from 'node:assert/strict';
const origin=process.env.MACROLENS_V2_API_URL||'http://127.0.0.1:8032';
async function get(path){const r=await fetch(origin+'/api/v2/'+path,{signal:AbortSignal.timeout(90000)});assert.equal(r.status,200);return r.json();}
const close=(a,b)=>assert(Math.abs(a-b)<1e-9,`${a} != ${b}`);
test('expanded live catalogue retrieves all audited free series with dated units and real weekly observations',{timeout:120000},async()=>{
 const all=await get('datasets');assert.equal(all.length,30);const added=['initial_claims','job_openings','participation','hourly_earnings','breakeven_5y','retail_sales','real_consumption','consumer_sentiment','housing_starts','building_permits','mortgage_30y','industrial_production','yield_curve','high_yield_spread','investment_grade_spread'];
 for(const id of added){const d=all.find(d=>d.id===id);assert.notEqual(d.status,'unavailable',id);assert(d.observations.some(o=>o.value!==null),id);assert(d.units&&d.definition&&d.latest_observation_date&&d.retrieved_at);assert.equal(d.provider,'fred');assert.equal(d.publication_date,null);}
});
test('all real daily scan horizons reproduce source endpoints and never label unknown movements as anomalies',{timeout:120000},async()=>{
 const r=await get('discovery');assert(r.horizon_results.length>60);
 for(const key of ['us10y','sp500','gold','dxy']){
 const results=r.horizon_results.filter(x=>x.dataset===key);assert.deepEqual(results.map(x=>x.horizon),[1,5,21,63,252]);
 for(const result of results){const response=await fetch(origin+'/api/v2/compare',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({datasets:[key],transformations:{[key]:key==='us10y'?'pp':'percent'},horizons:{[key]:result.horizon},observation_basis:'trading_sessions',start:'2020-01-01',end:result.date})});assert.equal(response.status,200);const c=await response.json();const last=c.series[0].observations.at(-1);if(result.change!==null)close(last.value,result.change);else assert.equal(last.value,null);}
 }
});
test('real discovery memory survives repeated manual checks without duplicate identities or version increments',{timeout:120000},async()=>{
 const a=await get('discovery');const r=await fetch(origin+'/api/v2/discovery/refresh',{method:'POST'});assert.equal(r.status,200);const b=await r.json();
 const one=[...a.findings,...a.following],two=[...b.findings,...b.following];
 assert.deepEqual(one.map(f=>[f.id,f.evidence_version,f.lifecycle.last_meaningful_update]),two.map(f=>[f.id,f.evidence_version,f.lifecycle.last_meaningful_update]));assert.equal(a.generated_at,b.generated_at);assert(b.manual_refresh.note.includes('No AI'));
});
test('real historical snapshots stay fixed and current comparisons have identical definitions and horizons',{timeout:120000},async()=>{
 const a=await get('discovery'),b=await get('discovery');assert(a.historical.length>=1);
 for(const h of a.historical){const again=b.historical.find(x=>x.id===h.id);assert.deepEqual(h.snapshot,again.snapshot);assert(h.notes.includes('not a backtest'));assert(h.snapshot.pattern.observations.every(o=>o.date<=h.snapshot.finding.observation_date));if(h.current_pattern){assert.equal(h.current_pattern.required,h.snapshot.pattern.required);assert.equal(h.current_pattern.units,h.snapshot.pattern.units);}assert.equal(typeof h.similarity.matches,'boolean');}
});
