import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {mergeObservations,hoverValues,restoreWorkspace,readInvestigations} from '../lib/workspace.ts';
import {dateLabel,referenceLabel} from '../lib/presentation.ts';

const s=(id,frequency,observations)=>({id,name:id,native_frequency:frequency,transformation:'level',units:'units',observations});
test('native simultaneous events keep separate identities and exact UTC instants',()=>{
 const events=[{date:'2024-01-01T14:30:00+00:00',key:'a',event_id:'a',value:0,native_label:'Release A',period_start:'2024-01-01',period_end:'2024-01-01'},{date:'2024-01-01T14:30:00+00:00',key:'b',event_id:'b',value:-2,native_label:'Release B',period_start:'2024-01-01',period_end:'2024-01-01'}];
 const rows=mergeObservations([s('events','event',events)]);
 assert.equal(rows.length,2);assert.equal(rows[0].time,Date.parse(events[0].date));assert.equal(rows[1].values.events,-2);assert.match(hoverValues(rows[1],[s('events','event',events)],[])[0].native_label,/Release B/);
});
test('all native frequencies retain source dates, labels, missing and negative observations',()=>{
 for(const frequency of ['daily','weekly','monthly','quarterly','annual','irregular']){
  const series=[s('x',frequency,[{date:'2023-04-01',value:-3,native_label:'FY2024 Q1'},{date:'2023-10-01',value:null},{date:'2024-01-01',value:0}])];
  const rows=mergeObservations(series);assert.equal(rows.length,3);assert.deepEqual(rows.map(r=>r.values.x),[-3,null,0]);
 }
});
test('native fiscal and event labels never acquire Gregorian quarter or invalid dates',()=>{
 assert.equal(referenceLabel({latest_native_label:'FY2024 Q1',frequency:'quarterly',latest_observation_date:'2023-04-01'}),'FY2024 Q1');
 assert.notEqual(dateLabel('2024-01-01T14:30:00+00:00'),'Date unavailable');
});
test('retired and private saved IDs survive reading and workspace restoration',()=>{
 const saved={version:3,datasets:['retired_id','wb_copper_monthly'],note:'preserve',workspace:{mode:'separate',chart_type:'line',hidden:[]}};
 const original=JSON.stringify([saved]);const records=readInvestigations({getItem:()=>original});restoreWorkspace(records[0]);assert.equal(JSON.stringify(records),original);
});
test('Explorer requests metadata pages and visible previews with bounded concurrency',()=>{
 const code=readFileSync(new URL('../components/catalog-explorer.tsx',import.meta.url),'utf8');
 assert.match(code,/catalog\/search/);assert.match(code,/limit:12/);assert.match(code,/length:3/);assert.match(code,/preview=true&limit=24/);assert.doesNotMatch(code,/request<Dataset\[\]>\('datasets'/);
});
test('native renderers preserve exact event tooltip payload and discrete event points',()=>{
 const code=readFileSync(new URL('../components/research-charts.tsx',import.meta.url),'utf8');assert.match(code,/payload\?\.\[0\]\?\.payload/);assert.match(code,/<Scatter/);assert.match(code,/connectNulls=\{false\}/);
});
