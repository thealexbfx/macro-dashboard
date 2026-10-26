import test from 'node:test';
import assert from 'node:assert/strict';
import {discoveryInvestigation,suggestionInvestigation} from '../lib/discovery.ts';
import {appendInvestigation,readInvestigations,defaultWorkspace} from '../lib/workspace.ts';
const f={id:'stable',headline:'Yield fell',configuration:{datasets:['us10y'],transformations:{us10y:'pp'},horizons:{us10y:5},observation_basis:'trading_sessions',start:'2026-01-01',end:'2026-10-23',timeframe:'Custom',alignment:'native',rolling_window:60,workspace:{...defaultWorkspace(),mode:'separate'}},evidence:{movement:-.17},evidence_version:2,lifecycle:{status:'Updated'}};
const report={generated_at:'2026-10-25T12:00:00Z',snapshot_fingerprint:'verified'};
test('Phase 3.2 horizon and trading basis survive saving and reopening without changing previous saves',()=>{
 let data=JSON.stringify([{id:'legacy',version:2,note:'keep'}]);const storage={getItem:()=>data,setItem:(_,v)=>data=v};
 const record=discoveryInvestigation(f,report,'new');record.historical_context={snapshot:{pattern:{observations:[{date:'2008-01-01',value:1.23456789}]}},similarity:{matches:false}};
 appendInvestigation(storage,record);const reopened=readInvestigations(storage);
 assert.deepEqual(reopened[0].horizons,{us10y:5});assert.equal(reopened[0].observation_basis,'trading_sessions');assert.equal(reopened[0].historical_context.snapshot.pattern.observations[0].value,1.23456789);assert.equal(reopened[1].note,'keep');
});
test('one-click followup opens validated configuration while retaining original discovery evidence',()=>{
 const suggestion={label:'How did equities move?',origin:'Research question',context:'Verified same-horizon movements',configuration:{...f.configuration,datasets:['us10y','sp500'],horizons:{us10y:5,sp500:5},transformations:{us10y:'pp',sp500:'percent'}}};
 const record=suggestionInvestigation(f,suggestion,report,'followup');assert.equal(record.datasets.length,2);assert.deepEqual(record.discovery.finding.evidence,{movement:-.17});assert.equal(record.horizons.sp500,5);
 suggestion.configuration.horizons.sp500=21;assert.equal(record.horizons.sp500,5);
});
import {transformationLabel} from '../lib/contracts.ts';
test('multi-month and payroll horizons never retain misleading one-month display labels',()=>{
 assert.equal(transformationLabel('mom',3),'Multi-period percentage change');assert.equal(transformationLabel('jobs',12),'Multi-period net employment change');assert.equal(transformationLabel('mom',1),'Month-over-month %');assert.equal(transformationLabel('yoy',1),'Year-over-year %');
});
