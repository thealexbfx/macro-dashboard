import {test} from 'node:test';
import assert from 'node:assert/strict';
import {bojMetadataShape,probeBojMetadata} from './boj-discovery.mjs';
const immediately=async()=>{};
test('BOJ metadata discovery only retains schema, not publisher series or values',async()=>{
  const secret='SENSITIVE_SERIES_VALUE_DO_NOT_EXPORT';
  const payload={status:'success',metadata:[{code:secret,title:secret,observations:secret}],token:secret};
  const r=await probeBojMetadata(async(url,opts)=>{
    assert.equal(url,'https://www.stat-search.boj.or.jp/api/v1/getMetadata?format=json&lang=en&db=FM01');
    assert.equal(opts.method,'GET');
    assert.equal(opts.redirect,'error');
    return Response.json(payload);
  },immediately);
  assert.equal(r.http_status,200);
  assert.equal(r.operational_result,'RETRIEVED_METADATA_RESPONSE_NOT_SERIES_VERIFIED');
  assert.equal(r.series_code,null);
  assert.equal(r.identity_status,'UNRESOLVED');
  assert.equal(r.production_approval,'NOT_APPROVED');
  assert.equal(r.rights_status,'PENDING');
  assert.equal(r.verification_scope,'NONE');
  assert.ok(!JSON.stringify(r).includes(secret));
  assert.equal(r.shape.first_level_types.metadata,'array');
});
test('BOJ malformed data, 404 and network outage do not become verified',async()=>{
  const bad=await probeBojMetadata(async()=>new Response('<html>error</html>'),immediately);
  assert.equal(bad.error_category,'invalid_json');
  assert.equal(bad.series_code,null);
  const notfound=await probeBojMetadata(async()=>new Response('',{status:404}),immediately);
  assert.equal(notfound.error_category,'http_404');
  const outage=await probeBojMetadata(async()=>{throw Error('offline');},immediately);
  assert.equal(outage.error_category,'network_or_timeout');
  assert.equal(outage.attempt,3);
});
test('BOJ bounded metadata diagnostics never record leaf data or dynamic keys',()=>{
  const secret='value-secret';
  const shape=bojMetadataShape([{seriesCode:secret,'sneaky data':secret}]);
  assert.deepEqual(shape.first_entry_keys,['seriesCode']);
  assert.ok(!JSON.stringify(shape).includes(secret));
});
