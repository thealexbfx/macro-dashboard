import {test} from 'node:test';
import assert from 'node:assert/strict';
import {bojMetadataShape,probeBojMetadata,selectBojRateCandidates} from './boj-discovery.mjs';
const immediate=async()=>{};
const candidate={SERIES_CODE:'MAINAVG',
  NAME_OF_TIME_SERIES:'Call Rates (Uncollateralized Overnight)/Average',
  UNIT:'% per annum',FREQUENCY:'DAILY',CATEGORY:'Financial Markets',
  NOTES:'DO_NOT_COPY_THIS_ARBITRARY_TEXT'};
const payload={STATUS:200,DB:'FM01',RESULTSET:[
  candidate,{SERIES_CODE:'OTHER',NAME_OF_TIME_SERIES:'Other financial statistic'},
  {SERIES_CODE:'NOT_VALID;INJECTION',NAME_OF_TIME_SERIES:'Call Rate'}]};

test('BOJ real metadata envelope exposes bounded candidate catalogue, not verified mapping',async()=>{
  const r=await probeBojMetadata(async(url,options)=>{
    assert.equal(url,'https://www.stat-search.boj.or.jp/api/v1/getMetadata?format=json&lang=en&db=FM01');
    assert.equal(options.method,'GET');
    assert.equal(options.redirect,'error');
    return Response.json(payload);
  },immediate);
  assert.equal(r.http_status,200);
  assert.equal(r.error_category,null);
  assert.equal(r.publisher_status,200);
  assert.equal(r.operational_result,'METADATA_CATALOGUE_DISCOVERY_ONLY');
  assert.equal(r.shape.resultset_type,'array');
  assert.equal(r.shape.resultset_count,3);
  assert.equal(r.shape.resultset_first_entry_type,'object');
  assert.ok(r.shape.resultset_first_entry_keys.includes('SERIES_CODE'));
  assert.equal(r.candidates.length,1);
  assert.equal(r.candidates[0].series_code,'MAINAVG');
  assert.equal(r.candidates[0].policy_target_equivalence,'NOT_ESTABLISHED');
  assert.equal(r.series_code,null);
  assert.equal(r.identity_status,'UNRESOLVED');
  assert.equal(r.production_approval,'NOT_APPROVED');
  assert.equal(r.rights_status,'PENDING');
  assert.equal(r.verification_scope,'NONE');
  assert.ok(!JSON.stringify(r).includes('DO_NOT_COPY_THIS_ARBITRARY_TEXT'));
});

test('BOJ HTTP 200 with failure STATUS or wrong DB is NOT usable metadata',async()=>{
  const failure=await probeBojMetadata(async()=>Response.json({STATUS:400,DB:'FM01',RESULTSET:[]}),immediate);
  assert.equal(failure.http_status,200);
  assert.equal(failure.error_category,'unexpected_boj_envelope');
  assert.equal(failure.operational_result,'UNRESOLVED_METADATA_RESPONSE');
  assert.deepEqual(failure.candidates,[]);
  const wrong=await probeBojMetadata(async()=>Response.json({STATUS:200,DB:'FX01',RESULTSET:[candidate]}),immediate);
  assert.equal(wrong.error_category,'unexpected_boj_envelope');
  assert.deepEqual(wrong.candidates,[]);
});

test('BOJ malformed data, 404 and network outage do not become verified',async()=>{
  const bad=await probeBojMetadata(async()=>new Response('<html>error</html>'),immediate);
  assert.equal(bad.error_category,'invalid_json');
  const missing=await probeBojMetadata(async()=>new Response('',{status:404}),immediate);
  assert.equal(missing.error_category,'http_404');
  const offline=await probeBojMetadata(async()=>{throw Error('offline');},immediate);
  assert.equal(offline.error_category,'network_or_timeout');
  assert.equal(offline.attempt,3);
});

test('BOJ discovery refuses dynamic fields, labels with unbounded length and stray values',()=>{
  const contaminated={STATUS:200,DB:'FM01',RESULTSET:[
    {...candidate,NOTES:'DO_NOT_EXPORT'},
    {...candidate,SERIES_CODE:'INJECT;BAD'},
    {...candidate,SERIES_CODE:'VALIDCODE',NAME_OF_TIME_SERIES:'overnight '.repeat(40)}]};
  const chosen=selectBojRateCandidates(contaminated);
  assert.equal(chosen.length,1);
  assert.deepEqual(Object.keys(chosen[0]).sort(),[
    'candidate_only','category','frequency','name','policy_target_equivalence','series_code','unit'].sort());
  assert.ok(!JSON.stringify(chosen).includes('DO_NOT_EXPORT'));
});

test('BOJ response schema diagnostic retains field names/types, never leaf values',()=>{
  const secret='NO_VALUE_IN_SHAPE';
  const schema=bojMetadataShape({STATUS:200,DB:'FM01',RESULTSET:[
    {SERIES_CODE:secret,NAME_OF_TIME_SERIES:secret,NOTES:secret}]});
  assert.ok(schema.resultset_first_entry_keys.includes('SERIES_CODE'));
  assert.equal(schema.resultset_count,1);
  assert.equal(JSON.stringify(schema).includes(secret),false);
});
