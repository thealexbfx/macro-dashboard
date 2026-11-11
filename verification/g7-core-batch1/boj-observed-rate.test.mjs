import {test} from 'node:test';
import assert from 'node:assert/strict';
import {extractObservedBoj,probeObservedBoj} from './boj-observed-rate.mjs';
const immediate=async()=>{};
const example={STATUS:200,PARAMETER:{DB:'FM01'},NEXTPOSITION:null,RESULTSET:[{
  SERIES_CODE:'STRDCLUCON',NAME_OF_TIME_SERIES:'Uncollateralized Overnight Call Rate',
  UNIT:'%',FREQUENCY:'DAILY',VALUES:{SURVEY_DATES:[20261104,20261105,20261106,20261109],
    VALUES:[0.49,null,0.50,0.51]}}]};
test('BOJ observed rate checks exact publisher code and samples but never verifies policy target',async()=>{
  const r=await probeObservedBoj(async(url,opts)=>{
    assert.match(url,/^https:\/\/www\.stat-search\.boj\.or\.jp\/api\/v1\/getDataCode\?format=json&lang=en&db=FM01&startDate=\d{6}&endDate=\d{6}&code=STRDCLUCON$/);
    assert.equal(opts.method,'GET');
    assert.equal(opts.redirect,'error');
    return Response.json(example);
  },immediate);
  assert.equal(r.outcome,'RECENT_OBSERVED_RATE_SAMPLE');
  assert.equal(r.series_id,'STRDCLUCON');
  assert.equal(r.last_observations.length,3);
  assert.equal(r.last_observations[2].date,'20261109');
  assert.equal(r.policy_target_equivalence,'NOT_ESTABLISHED');
  assert.equal(r.target_mapping,null);
  assert.equal(r.rights_status,'PENDING');
  assert.equal(r.production_approval,'NOT_APPROVED');
});
test('BOJ wrong series, inconsistent units, non-200 body, pagination fail closed',()=>{
  const wrong=structuredClone(example);wrong.RESULTSET[0].SERIES_CODE='STRDCLUCONH';
  assert.equal(extractObservedBoj(wrong).error_category,'unexpected_series_identity');
  const units=structuredClone(example);units.RESULTSET[0].UNIT='JPY';
  assert.equal(extractObservedBoj(units).error_category,'unexpected_rate_unit');
  const paging=structuredClone(example);paging.NEXTPOSITION=10;
  assert.equal(extractObservedBoj(paging).error_category,'pagination_not_exhausted');
  const failed=structuredClone(example);failed.STATUS=400;
  assert.equal(extractObservedBoj(failed).outcome,'UNRESOLVED');
});
test('BOJ date/observation count and malicious values cannot be verified',()=>{
  const weird=structuredClone(example);weird.RESULTSET[0].VALUES.SURVEY_DATES=['not-a-date'];
  assert.equal(extractObservedBoj(weird).outcome,'UNRESOLVED');
  const inconsistent=structuredClone(example);inconsistent.RESULTSET[0].VALUES.VALUES=[1];
  assert.equal(extractObservedBoj(inconsistent).outcome,'UNRESOLVED');
  const injected=structuredClone(example);injected.RESULTSET[0].VALUES.VALUES[0]='1e309';
  assert.equal(extractObservedBoj(injected).outcome,'UNRESOLVED');
});
test('BOJ network and unexpected HTML do not verify observed series',async()=>{
  const unavailable=await probeObservedBoj(async()=>{throw Error('offline');},immediate);
  assert.equal(unavailable.outcome,'UNRESOLVED');
  assert.equal(unavailable.error_category,'network_or_timeout');
  const html=await probeObservedBoj(async()=>new Response('<html>blocked</html>'),immediate);
  assert.equal(html.error_category,'invalid_json');
  assert.equal(html.production_approval,'NOT_APPROVED');
});
