import test from 'node:test';
import assert from 'node:assert/strict';
import {discoveryInvestigation} from '../lib/discovery.ts';
import {defaultWorkspace,restoreWorkspace,appendInvestigation} from '../lib/workspace.ts';

const finding=()=>({id:'f1',type:'correlation',label:'Relationship changing',headline:'Measured change',datasets:['cpi','unemployment'],observation_date:'2026-09-01',evidence:{recent_correlation:-.5,baseline_correlation:.6,recent:{start:'2024-10-01',end:'2026-09-01'},baseline:{start:'2014-10-01',end:'2024-09-01'}},sources:[{id:'cpi',latest_observation_date:'2026-09-01'}],configuration:{datasets:['cpi','unemployment'],transformations:{cpi:'mom',unemployment:'pp'},start:'2014-10-01',end:'2026-09-01',alignment:'native',rolling_window:24,timeframe:'Custom',workspace:{...defaultWorkspace(),mode:'separate'}},methodology_version:'3.1.0'});
const report={generated_at:'2026-10-25T12:00:00Z',snapshot_fingerprint:'abc'};
test('discovery-to-Investigate retains exact datasets, transformations, dates, mode, windows and lead-lag',()=>{
 const f=finding();const r=discoveryInvestigation(f,report,'save1','question');
 assert.deepEqual(r.datasets,f.datasets);assert.deepEqual(r.transformations,f.configuration.transformations);
 assert.equal(r.start,f.configuration.start);assert.equal(r.end,f.configuration.end);assert.equal(r.rolling_window,24);
 assert.deepEqual(restoreWorkspace(r),f.configuration.workspace);assert.equal(r.note,'question');
 assert.deepEqual(r.discovery.finding.evidence,f.evidence);assert.deepEqual(r.discovery.finding.sources,f.sources);
});
test('saved discovery is an immutable evidence snapshot when subsequent live results revise',()=>{
 const f=finding();const record=discoveryInvestigation(f,report,'s');f.evidence.recent_correlation=.8;f.sources[0].latest_observation_date='2026-10-01';
 assert.equal(record.discovery.finding.evidence.recent_correlation,-.5);assert.equal(record.discovery.finding.sources[0].latest_observation_date,'2026-09-01');
 const reopened=JSON.parse(JSON.stringify(record));assert.deepEqual(restoreWorkspace(reopened),record.workspace);assert.equal(reopened.discovery.generated_at,report.generated_at);
});
test('saving discovery preserves older investigations and collection filtering',()=>{
 let value=JSON.stringify([{id:'old',version:2,datasets:['gold'],note:'keep'}]);const storage={getItem:()=>value,setItem:(_,v)=>value=v};
 const next=appendInvestigation(storage,discoveryInvestigation(finding(),report,'new'));
 assert.equal(next[1].note,'keep');assert.equal(next[0].collection,'Discovery Radar');assert.equal(next.filter(s=>s.collection==='Discovery Radar').length,1);
});
