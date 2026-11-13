import {test} from 'node:test';
import assert from 'node:assert/strict';
import {buildDecisionReviewQueue} from './boj-2006-2008-review-queue.mjs';
test('retains every original document for a date without inferring a policy value',()=>{
 const census={periods:[{year:2006,census_status:'PUBLISHER_INDEX_DATES_EXTRACTED',
 listed_dates:['2006-07-14','2006-03-09'],statement_links:[
 {date:'2006-07-14',url:'https://www.boj.or.jp/a.pdf',title:'Monetary policy decision',title_classification:'REQUIRES_ORIGINAL_DOCUMENT_REVIEW'},
 {date:'2006-07-14',url:'https://www.boj.or.jp/b.pdf',title:'Additional measures',title_classification:'UNCLASSIFIED'},
 {date:'2006-03-09',url:'https://www.boj.or.jp/c.htm',title:'Policy unchanged',title_classification:'TITLE_SAYS_UNCHANGED_NOT_DOCUMENT_VERIFIED'}]}]};
 const report=buildDecisionReviewQueue(census);
 assert.equal(report.statement_dates.length,2);
 assert.deepEqual(report.missing_years,[2007,2008]);
 assert.equal(report.statement_dates[1].documents.length,2);
 assert.equal(report.production_approval,'NOT_APPROVED');
 assert.equal(report.complete_economic_series,false);
 for(const d of report.statement_dates){
  assert.equal(d.policy_value_verified,false);
  assert.equal(d.target_value_percent,null);
  assert.ok(d.documents.every(doc=>doc.original_document_verified===false));
 }
});
test('missing source links remain explicit without dropping publisher dates',()=>{
 const report=buildDecisionReviewQueue({periods:[{year:2008,census_status:'PUBLISHER_INDEX_DATES_EXTRACTED',listed_dates:['2008-10-31'],statement_links:[]}]});
 assert.deepEqual(report.missing_document_links,['2008-10-31']);
 assert.equal(report.statement_dates[0].date_verification_status,'MISSING_DOCUMENT_LINKS');
});
