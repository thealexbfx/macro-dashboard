import {test} from 'node:test';
import assert from 'node:assert/strict';
import {checkBojPolicyPdf,probeBojPolicyPdfs} from './boj-policy-pdf.mjs';
const immediate=async()=>{};
const pdf=Buffer.from('%PDF-1.7\nfake mocked bytes');
const text=(date,rate,effective)=>[
  date,'Bank of Japan','Change in the Guideline for Money Market Operations',
  'The Bank will encourage the uncollateralized overnight call rate to remain at around '+rate+' percent.',
  'The new guideline for money market operations will be effective from '+effective+'.',
  'The basic loan rate was different from the target.'
].join('\n');
const june={decision_date:'2026-06-16',effective_date:'2026-06-17',rate:1};
test('2026 original BOJ PDF sample verifies rate, decision and effective dates separately',async()=>{
  const r=await probeBojPolicyPdfs(async(url,opts)=>{
    assert.equal(opts.method,'GET');assert.equal(opts.redirect,'error');
    assert.match(url,/^https:\/\/www\.boj\.or\.jp\/en\/mopo\/mpmdeci\/mpr_2026\/k260(616|918)a\.pdf$/);
    return new Response(pdf,{headers:{'content-type':'application/pdf'}});
  },immediate,(_pdf)=>text(
    _pdf.length&&'June 16, 2026','1.0','June 17, 2026'));
  assert.equal(r.events[0].outcome,'PUBLISHER_PDF_POLICY_DECISION_SAMPLE');
  assert.equal(r.events[0].decision_date,'2026-06-16');
  assert.equal(r.events[0].effective_date,'2026-06-17');
  assert.equal(r.events[1].outcome,'UNRESOLVED');
  assert.equal(r.confirmed_events,1);
  assert.equal(r.mapping_status,'UNCONFIGURED');
  assert.equal(r.full_history_verified,false);
  assert.equal(r.production_approval,'NOT_APPROVED');
});
test('both 2026 events have distinct original dates and target levels',()=>{
  const september={decision_date:'2026-09-18',effective_date:'2026-09-24',rate:1.25};
  const result=checkBojPolicyPdf(text('September 18, 2026','1.25','September 24, 2026'),september);
  assert.equal(result.outcome,'PUBLISHER_PDF_POLICY_DECISION_SAMPLE');
  assert.equal(result.target_percent,1.25);
  assert.equal(result.effective_date,'2026-09-24');
});
test('mismatched values and missing effective date must never become verified',()=>{
  assert.equal(checkBojPolicyPdf(text('June 16, 2026','1.25','June 17, 2026'),june).outcome,'MISMATCH');
  assert.equal(checkBojPolicyPdf(text('June 16, 2026','1.0','June 18, 2026'),june).error_category,'effective_date_not_proven');
  assert.equal(checkBojPolicyPdf(text('June 17, 2026','1.0','June 17, 2026'),june).error_category,'decision_date_not_proven');
});
test('no PDF, inaccessible document or failed extraction remains unresolved',async()=>{
  const wrong=await probeBojPolicyPdfs(async()=>new Response('<html>No</html>',{headers:{'content-type':'text/html'}}),immediate);
  assert.equal(wrong.confirmed_events,0);
  assert.equal(wrong.events[0].error_category,'wrong_content_type');
  const blocked=await probeBojPolicyPdfs(async()=>new Response('',{status:403}),immediate);
  assert.equal(blocked.events[1].error_category,'http_403');
  const missing=await probeBojPolicyPdfs(async()=>new Response(pdf,{headers:{'content-type':'application/pdf'}}),immediate,()=>{throw Error('missing binary');});
  assert.equal(missing.events[0].error_category,'pdf_extraction_failed_or_missing');
});
