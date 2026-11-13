import {test} from 'node:test';
import assert from 'node:assert/strict';
import {historicalCensus,censusYears,classifyStatementTitle} from './boj-historical-census.mjs';

const table=year=>'<!doctype html><html><h1>Statements on Monetary Policy '+year+'</h1>'+
 '<table><tr><th>Date</th><th>Title</th></tr>'+
 '<tr><td>Dec. 19, '+year+'</td><td><a href="decision.pdf">Policy decision</a></td></tr>'+
 '<tr><td>Dec. 19, '+year+'</td><td><a href="reference.pdf">Additional document</a></td></tr>'+
 '</table></html>';
test('historical annual index extracts distinct dates without asserting full meeting coverage',async()=>{
 const report=await historicalCensus({transport:async url=>{
   const year=Number(url.match(/state_(\d{4})/)[1]);
   return new Response(table(year),{headers:{'content-type':'text/html'}});
 }});
 assert.equal(report.periods.length,censusYears.length);
 assert.equal(report.production_approval,'NOT_APPROVED');
 assert.equal(report.meeting_census_verified,false);
 for(const p of report.periods){
   assert.equal(p.census_status,'PUBLISHER_INDEX_DATES_EXTRACTED');
   assert.deepEqual(p.listed_dates,[p.year+'-12-19']);
   assert.equal(p.listed_date_count,1);
   assert.match(p.content_sha256,/^[a-f0-9]{64}$/);
 }
});
test('malformed index does not become a verified census',async()=>{
 const report=await historicalCensus({transport:async()=>new Response('<html>no table</html>',
 {headers:{'content-type':'text/html'}})});
 assert.ok(report.periods.every(p=>p.census_status==='UNRESOLVED'&&p.reason==='archive_table_unproven'));
});

test('title classifications do not certify policy rates',()=>{
 assert.equal(classifyStatementTitle('Policy unchanged, Announced at 12:34 pm'),
 'TITLE_SAYS_UNCHANGED_NOT_DOCUMENT_VERIFIED');
 assert.equal(classifyStatementTitle('On Monetary Policy Decisions'),
 'REQUIRES_ORIGINAL_DOCUMENT_REVIEW');
});
