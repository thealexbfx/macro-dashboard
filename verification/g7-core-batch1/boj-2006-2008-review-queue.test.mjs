import {test} from 'node:test';
import assert from 'node:assert/strict';
import {buildDecisionReviewQueue} from './boj-2006-2008-review-queue.mjs';
test('one original BOJ decision document per indexed date, no inferred rates',()=>{
 const census={periods:[{year:2006,dates_without_statement_links:[],statement_links:[
 {date:'2006-07-14',url:'https://www.boj.or.jp/a.pdf',title:'Announcement of the Monetary Policy Meeting Decisions (Change in the Guideline)',title_classification:'REQUIRES_ORIGINAL_DOCUMENT_REVIEW'},
 {date:'2006-07-14',url:'https://www.boj.or.jp/b.pdf',title:'On Monetary Policy Decisions',title_classification:'REQUIRES_ORIGINAL_DOCUMENT_REVIEW'},
 {date:'2006-03-09',url:'https://www.boj.or.jp/c.htm',title:'Announcement of the Monetary Policy Meeting Decisions (unchanged)',title_classification:'TITLE_SAYS_UNCHANGED_NOT_DOCUMENT_VERIFIED'}]}]};
 const report=buildDecisionReviewQueue(census);
 assert.equal(report.statement_dates.length,2);
 assert.equal(report.production_approval,'NOT_APPROVED');
 assert.equal(report.complete_economic_series,false);
 for(const d of report.statement_dates){
  assert.equal(d.original_document_verified,false);
  assert.equal(d.target_value_percent,null);
  assert.equal(d.verification_status,'ORIGINAL_DOCUMENT_REVIEW_REQUIRED');
 }
});
