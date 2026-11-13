import {test} from 'node:test';
import assert from 'node:assert/strict';
import {parseBojPolicyGuideline,probeBojPolicyGuideline} from './boj-policy-guideline.mjs';
const immediate=async()=>{};
const doc=v=>'<html><body><section><h2>Guideline</h2><p>'+
  'The Bank will encourage the uncollateralized overnight call rate to remain at around '+v+
  ' percent.</p><p>Basic loan rate 1.5 percent; inflation target 2 percent</p></section></body></html>';
test('matches only the BOJ announced target statement, not observed rates or adjacent figures',()=>{
  const r=parseBojPolicyGuideline(doc('1.25'));
  assert.equal(r.outcome,'PUBLISHER_GUIDELINE_SNAPSHOT');
  assert.equal(r.level,1.25);
  assert.equal(r.unit,'percent');
  assert.equal(r.frequency,'EVENT_DECISION_NOT_DAILY_OBSERVATION');
  assert.equal(r.error_category,null);
});
test('publisher guideline snapshot remains separate from G7-JP-22 mapped series',async()=>{
  const r=await probeBojPolicyGuideline(async(url,opts)=>{
    assert.equal(url,'https://www.boj.or.jp/en/index.htm');
    assert.equal(opts.method,'GET');
    assert.equal(opts.redirect,'error');
    return new Response(doc('1.25'),{headers:{'content-type':'text/html; charset=utf-8'}});
  },immediate);
  assert.equal(r.outcome,'PUBLISHER_GUIDELINE_SNAPSHOT');
  assert.equal(r.target_mapping,'G7-JP-22');
  assert.equal(r.mapping_status,'UNCONFIGURED');
  assert.equal(r.historical_target_series_verified,false);
  assert.equal(r.release_effective_date_verified,false);
  assert.equal(r.release_vintages_verified,false);
  assert.equal(r.rate_observations_verified,false);
  assert.equal(r.rights_status,'PENDING');
  assert.equal(r.production_approval,'NOT_APPROVED');
});
test('missing, ambiguous and out-of-range targets fail closed',()=>{
  assert.equal(parseBojPolicyGuideline('<html><body>the uncollateralized overnight rate was 0.51%</body></html>').outcome,'UNRESOLVED');
  const conflict=doc('1.25').replace('</body>','<p>The Bank will encourage the uncollateralized overnight call rate to remain at around 2.00 percent.</p></body>');
  assert.equal(parseBojPolicyGuideline(conflict).error_category,'ambiguous_or_missing_guideline');
  assert.equal(parseBojPolicyGuideline(doc('30')).outcome,'UNRESOLVED');
});
test('body, content type and HTTP failures cannot count as target evidence',async()=>{
  const bad=await probeBojPolicyGuideline(async()=>Response.json({message:doc('1.25')}),immediate);
  assert.equal(bad.error_category,'unexpected_content_type');
  const block=await probeBojPolicyGuideline(async()=>new Response('',{status:403}),immediate);
  assert.equal(block.error_category,'http_403');
  const outage=await probeBojPolicyGuideline(async()=>{throw Error('offline');},immediate);
  assert.equal(outage.error_category,'network_or_timeout');
  for(const r of [bad,block,outage])assert.equal(r.production_approval,'NOT_APPROVED');
});
test('script-injected target is ignored',()=>{
  const malicious='<html><body><script>'+doc('2.5')+'</script><p>No current guideline</p></body></html>';
  assert.equal(parseBojPolicyGuideline(malicious).outcome,'UNRESOLVED');
});
