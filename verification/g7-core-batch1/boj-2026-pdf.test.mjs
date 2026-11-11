import {test} from 'node:test';
import assert from 'node:assert/strict';
import {PDF_EVENTS,verifyBojPdfDecision,probeBoj2026Pdfs} from './boj-2026-pdf.mjs';
const textFor=(e,rate=e.expected_percent,effective=e.effective_date)=> {
  const words=d=>new Date(d+'T00:00:00Z').toLocaleDateString('en-US',{
    month:'long',day:'numeric',year:'numeric',timeZone:'UTC'});
  return [words(e.decision_date),'Bank of Japan',
    'Change in the Guideline for Money Market Operations',
    'The Bank will encourage the uncollateralized overnight call rate to remain at around '+rate+' percent.',
    '1 The new guideline for money market operations will be effective from '+words(effective)+'.'].join('\n');
};
const immediate=async()=>{};
test('two original 2026 BOJ PDFs prove target plus independent effective date',async()=>{
  const r=await probeBoj2026Pdfs(async(url,options)=>{
    assert.equal(options.method,'GET');
    assert.equal(options.redirect,'error');
    assert.match(url,/^https:\/\/www\.boj\.or\.jp\/en\/mopo\/mpmdeci\/mpr_2026\/k260(616|918)a\.pdf$/);
    return new Response(Buffer.from('%PDF-1.7 mock'),{headers:{'content-type':'application/pdf'}});
  },immediate,(_pdf)=>{
    const e=PDF_EVENTS[seen++];
    return textFor(e);
  });
  assert.equal(r.selected_events_verified,2);
  assert.deepEqual(r.events.map(e=>e.decision_date),['2026-06-16','2026-09-18']);
  assert.deepEqual(r.events.map(e=>e.effective_date),['2026-06-17','2026-09-24']);
  assert.deepEqual(r.events.map(e=>e.announced_target_percent),[1,1.25]);
  assert.equal(r.mapping_status,'UNCONFIGURED');
  assert.equal(r.full_history_verified,false);
  assert.equal(r.production_approval,'NOT_APPROVED');
});
let seen=0;
test('incorrect target and effective date never silently pass',()=>{
  const e=PDF_EVENTS[0];
  assert.equal(verifyBojPdfDecision(textFor(e,1.25),e).error_category,'announced_rate_conflicts_with_source');
  assert.equal(verifyBojPdfDecision(textFor(e,1,'2026-06-18'),e).error_category,'effective_date_conflicts_with_source');
  assert.equal(verifyBojPdfDecision(textFor(e).replace('Bank of Japan','Unknown'),e).outcome,'UNRESOLVED');
});
test('PDF transport and body failures are unresolved, not economic mismatches',async()=>{
  const bad=await probeBoj2026Pdfs(async()=>new Response('<html>Oops</html>',{headers:{'content-type':'text/html'}}),immediate);
  assert.equal(bad.selected_events_verified,0);
  assert.equal(bad.events[0].error_category,'unexpected_content_type');
  const corrupt=await probeBoj2026Pdfs(async()=>new Response('hello',{headers:{'content-type':'application/pdf'}}),immediate);
  assert.equal(corrupt.events[0].error_category,'missing_pdf_magic');
  const inaccessible=await probeBoj2026Pdfs(async()=>{throw Error('offline');},immediate);
  assert.equal(inaccessible.events[0].error_category,'network_or_timeout');
  assert.equal(inaccessible.production_approval,'NOT_APPROVED');
});
test('missing effective-date footnote cannot be fabricated from announcement date',()=>{
  const e=PDF_EVENTS[1];
  const source=textFor(e).replace(/1 The new guideline.*$/m,'');
  assert.equal(verifyBojPdfDecision(source,e).error_category,'effective_date_not_proven');
});
