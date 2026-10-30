// Separate real-provider checks; no fixture discoveries are installed in the app.
import test from 'node:test';
import assert from 'node:assert/strict';
const origin=process.env.MACROLENS_V2_API_URL||'http://127.0.0.1:8032';
async function radar(){const r=await fetch(`${origin}/api/v2/discovery`,{signal:AbortSignal.timeout(90000)});assert.equal(r.status,200,await r.clone().text());return r.json();}
function corr(rows){const n=rows.length,mx=rows.reduce((s,p)=>s+p.x,0)/n,my=rows.reduce((s,p)=>s+p.y,0)/n;let xx=0,yy=0,xy=0;for(const p of rows){xx+=(p.x-mx)**2;yy+=(p.y-my)**2;xy+=(p.x-mx)*(p.y-my);}return xy/Math.sqrt(xx*yy);}
const close=(a,b)=>assert(Math.abs(a-b)<1e-9,`${a} != ${b}`);
test('real Discovery report uses only canonical curated changes and stable cached evidence',{timeout:120000},async()=>{
 const a=await radar(),b=await radar();if(a.snapshot_fingerprint===b.snapshot_fingerprint)assert.equal(a.generated_at,b.generated_at);else assert(Date.parse(b.generated_at)>=Date.parse(a.generated_at));
 assert.equal(a.universe.curated_pairs,13);assert.equal(a.universe.exploratory_pairs,0);assert(a.findings.length<=8);
 for(const f of a.findings){assert(f.sources.every(s=>s.source&&s.url.startsWith('https://')));assert(!Object.values(f.configuration.transformations).includes('level'));assert.equal(f.methodology_version,'3.2.2');assert(f.ranking.score<=100);}
});
test('real findings reconcile with the same Investigate transformations and exact source observations',{timeout:120000},async()=>{
 const report=await radar();for(const f of report.findings){
 const c=f.configuration;const r=await fetch(`${origin}/api/v2/compare`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({datasets:c.datasets,transformations:c.transformations,start:c.start,end:c.end,alignment:c.alignment,rolling_window:c.rolling_window,horizons:c.horizons,observation_basis:c.observation_basis}),signal:AbortSignal.timeout(45000)});assert.equal(r.status,200);const compared=await r.json();
 if(f.type==='unusual'){const value=compared.series[0].observations.find(o=>o.date===f.observation_date).value;close(value,f.evidence.movement);assert(f.evidence.absolute_movement_percentile>=.975);assert(Math.abs(f.evidence.standardized_magnitude)>=2);if(c.datasets[0]==='us10y')close(f.evidence.display_movement,value*100);}
 else{for(const window of ['recent','baseline']){const w=f.evidence[window];const pairs=compared.scatter.filter(o=>o.date>=w.start&&o.date<=w.end);assert.equal(pairs.length,w.observations);close(corr(pairs),f.evidence[`${window}_correlation`]);}}
 }
});
test('real stale or excluded sources do not appear as fresh discoveries',{timeout:120000},async()=>{
 const report=await radar();for(const e of report.excluded)assert(!report.findings.some(f=>f.datasets.includes(e.id)));
 const unique=new Set(report.findings.map(f=>[...f.datasets].sort().join(',')));assert.equal(unique.size,report.findings.length);
 assert(report.limitations.some(v=>v.includes('Multiple')||v.includes('Several predefined')));
});
