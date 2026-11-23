import {test} from 'node:test';import assert from 'node:assert/strict';import {reconcileReviewQueue} from './boj-2006-2008-anchor-reconciliation.mjs';
test('source URL mismatch cannot verify policy values',()=>{
 const q={statement_dates:[{decision_date:'2008-10-31',documents:[{source_url:'https://www.boj.or.jp/a.pdf'}]}]};
 const a={anchors:[{date:'2008-10-31',target_percent:0.3,source_url:'https://www.boj.or.jp/b.pdf',status:'ORIGINAL_DOCUMENT_MANUALLY_REVIEWED'}]};
 const r=reconcileReviewQueue(q,a);
 assert.deepEqual(r.unmatched_anchors,['2008-10-31']);
 assert.equal(r.statement_dates[0].policy_value_verified,false);
 assert.equal(r.statement_dates[0].verification_status,'ANCHOR_SOURCE_LINK_UNMATCHED');
});
test('even source URL match does not certify unreviewed document content',()=>{
 const url='https://www.boj.or.jp/a.pdf';
 const r=reconcileReviewQueue({statement_dates:[{decision_date:'2008-10-31',documents:[{source_url:url}]}]},{anchors:[{date:'2008-10-31',target_percent:0.3,source_url:url,status:'ORIGINAL_DOCUMENT_MANUALLY_REVIEWED'}]});
 assert.equal(r.anchors_with_publisher_index_links,1);
 assert.equal(r.statement_dates[0].policy_value_verified,false);
 assert.equal(r.production_approval,'NOT_APPROVED');
});
