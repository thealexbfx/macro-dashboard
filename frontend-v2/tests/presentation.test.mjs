import test from 'node:test';
import assert from 'node:assert/strict';
import {timeframeStart,TIMEFRAMES,marketMovement,formatDatasetValue,formatNumber,freshness,recentObservations,referenceLabel} from '../lib/presentation.ts';
const dataset=(patch={})=>({id:'gold',name:'Gold — continuous futures',representation:'price',units:'USD / troy oz',frequency:'daily',status:'ok',latest_value:4007.89990234375,latest_observation_date:'2026-10-23',previous_observation_date:'2026-10-22',observations:[{date:'2026-10-22',value:4060.39990234375},{date:'2026-10-23',value:4007.89990234375}],...patch});
test('every timeframe selects the expected source window anchored to the selected endpoint',()=>{
const expected={'1M':'2026-09-23','3M':'2026-07-23',YTD:'2026-01-01','1Y':'2025-10-23','3Y':'2023-10-23','5Y':'2021-10-23','10Y':'2016-10-23',MAX:'1990-01-01'};
for(const range of TIMEFRAMES)assert.equal(timeframeStart(range,'2026-10-23'),expected[range]);
});
test('month ends and leap years clamp to valid dates rather than overflow',()=>{
assert.equal(timeframeStart('1M','2024-03-31'),'2024-02-29');assert.equal(timeframeStart('1M','2025-03-31'),'2025-02-28');assert.equal(timeframeStart('1Y','2024-02-29'),'2023-02-28');assert.equal(timeframeStart('3M','2026-05-31'),'2026-02-28');
});
test('YTD follows the endpoint year including January; MAX respects the service floor',()=>{
assert.equal(timeframeStart('YTD','2026-01-01'),'2026-01-01');assert.equal(timeframeStart('YTD','2025-12-31'),'2025-01-01');assert.equal(timeframeStart('10Y','1995-01-01'),'1990-01-01');
});
test('market display rounds values without changing underlying observations',()=>{
const d=dataset();const before=JSON.stringify(d);assert.equal(formatDatasetValue(d),'$4,007.90');assert.equal(formatNumber(marketMovement(d).value),'-1.29');assert.equal(JSON.stringify(d),before);
});
test('Treasury changes use basis points, not percentage returns',()=>{
const d=dataset({id:'us10y',representation:'rate',units:'Percent',latest_value:4.96,observations:[{date:'2026-10-22',value:5.13},{date:'2026-10-23',value:4.96}]});assert.equal(formatDatasetValue(d),'4.96%');assert.equal(formatNumber(marketMovement(d).value),'-17.00');assert.equal(marketMovement(d).unit,'bp');
});
test('WTI uses the actual positive prior close for percentage display',()=>{
const d=dataset({id:'wti',representation:'signed_flow',latest_value:103.27,units:'USD / barrel',observations:[{date:'2026-10-22',value:99.47},{date:'2026-10-23',value:103.27}]});assert.equal(formatNumber(marketMovement(d).value),'3.82');assert.equal(marketMovement(d).unit,'%');
});
test('nonpositive futures bases never produce misleading percent returns',()=>{
const d=dataset({representation:'signed_flow',observations:[{date:'2026-10-22',value:-10},{date:'2026-10-23',value:5}]});assert.equal(marketMovement(d).value,15);assert.equal(marketMovement(d).unit,'USD / troy oz');
});
test('stale and missing data stay visibly distinct from delayed observations',()=>{
assert.equal(freshness(dataset()),'Delayed data');assert.equal(freshness(dataset({status:'stale'})),'Stale data');assert.equal(freshness(dataset({status:'unavailable'})),'Unavailable');assert.equal(formatDatasetValue(dataset({status:'unavailable'})),'Unavailable');assert.equal(marketMovement(dataset({status:'unavailable'})).value,null);assert.equal(marketMovement(dataset({observations:[]})).value,null);
});
test('sparklines use only the recent supplied observations, preserve nulls and exclude future labels',()=>{
const observations=Array.from({length:30},(_,i)=>({date:`2026-09-${String(i+1).padStart(2,'0')}`,value:i===20?null:i}));const d=dataset({latest_observation_date:'2026-09-29',observations});const recent=recentObservations(d);assert.equal(recent.length,22);assert.equal(recent.at(-1).date,'2026-09-29');assert(recent.some(o=>o.value===null));assert.deepEqual(recent,d.observations.slice(7,29));
});
test('economic formatting respects rates, payroll levels and quarterly reference periods',()=>{
assert.equal(formatDatasetValue(dataset({id:'unemployment',units:'Percent',latest_value:4.2})),'4.2%');assert.equal(formatDatasetValue(dataset({id:'payrolls',units:'Thousands of persons',latest_value:159044})),'159,044');assert.equal(referenceLabel(dataset({frequency:'quarterly',latest_observation_date:'2026-04-01'})),'Q2 2026');assert.equal(referenceLabel(dataset({frequency:'quarterly',latest_observation_date:'2026-03-31'})),'Q1 2026');assert.equal(referenceLabel(dataset({frequency:'monthly',latest_observation_date:'2026-09-01'})),'Sept 2026');
});
