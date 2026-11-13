import {test} from 'node:test';
import assert from 'node:assert/strict';
import {historicalCensus,censusYears} from './boj-historical-census.mjs';

test('older BOJ annual indexes are discovery only, never fabricated census',async()=>{
 const report=await historicalCensus({transport:async()=>new Response('<!doctype html><html></html>',{headers:{'content-type':'text/html'}})});
 assert.equal(report.periods.length,censusYears.length);
 assert.equal(report.production_approval,'NOT_APPROVED');
 for(const p of report.periods){
   assert.equal(p.census_status,'UNRESOLVED');
   assert.deepEqual(p.listed_dates,[]);
   assert.equal(p.reason,'publisher_body_not_yet_parsed');
   assert.match(p.content_sha256,/^[a-f0-9]{64}$/);
 }
});
