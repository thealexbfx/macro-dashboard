import {test} from 'node:test';
import assert from 'node:assert/strict';
import {probeBojPolicyHistory,verifiedBojEvent} from './boj-policy-history.mjs';
const immediate=async()=>{};
const statement=(date,rate)=>'<html><body><h1>Change in the Guideline for Money Market Operations</h1>'+
  '<p>'+date+'</p><p>Bank of Japan</p><p>'+
  'The Bank will encourage the uncollateralized overnight call rate to remain at around '+
  rate+' percent.</p></body></html>';
test('two original BOJ decision dates can be supported while effective date stays unresolved',async()=>{
  const r=await probeBojPolicyHistory(async url=>{
    if(url.endsWith('k250124a.htm'))return new Response(statement('January 24, 2025','0.5'),
      {headers:{'content-type':'text/html'}});
    if(url.endsWith('k251219a.htm'))return new Response(statement('December 19, 2025','0.75'),
      {headers:{'content-type':'text/html'}});
    throw Error('Unexpected URL');
  },immediate);
  assert.equal(r.confirmed_events,2);
  assert.equal(r.all_selected_events_confirmed,true);
  assert.deepEqual(r.events.map(e=>e.announced_target_percent),[0.5,0.75]);
  assert.deepEqual(r.events.map(e=>e.decision_date),['2025-01-24','2025-12-19']);
  assert.deepEqual(r.events.map(e=>e.effective_date),[null,null]);
  assert.equal(r.full_history_verified,false);
  assert.equal(r.mapping_status,'UNCONFIGURED');
  assert.equal(r.production_approval,'NOT_APPROVED');
});
test('rate conflicts and missing date or publisher fail independently',()=>{
  const e={decision_date:'2025-01-24',expected_percent:0.5};
  assert.equal(verifiedBojEvent(statement('January 24, 2025','0.75'),e).outcome,'MISMATCH');
  assert.equal(verifiedBojEvent(statement('February 1, 2025','0.5'),e).error_category,'decision_date_not_proven');
  assert.equal(verifiedBojEvent(statement('January 24, 2025','0.5').replace('Bank of Japan','Unknown'),e).error_category,'publisher_identity_missing');
});
test('a wrong page type or blocked original URL does not fabricate a historical event',async()=>{
  const r=await probeBojPolicyHistory(async url=>url.endsWith('k250124a.htm')
    ?new Response('PDF', {headers:{'content-type':'application/pdf'}})
    :new Response('',{status:403}),immediate);
  assert.deepEqual(r.events.map(e=>e.outcome),['UNRESOLVED','UNRESOLVED']);
  assert.equal(r.confirmed_events,0);
  assert.equal(r.events[0].error_category,'wrong_content_type');
  assert.equal(r.events[1].error_category,'http_403');
});
test('unreachable history still permits independent failure receipts without approval',async()=>{
  const r=await probeBojPolicyHistory(async()=>{throw Error('offline');},immediate);
  assert.equal(r.events.length,2);
  assert.equal(r.events[0].error_category,'network_or_timeout');
  assert.equal(r.full_history_verified,false);
  assert.equal(r.production_approval,'NOT_APPROVED');
});
