import {test} from 'node:test';
import assert from 'node:assert/strict';
import {probeSource,auditGapSources} from './boj-historical-gap-sources.mjs';

test('source probe rejects unsafe URLs and redirects', async () => {
  assert.equal((await probeSource('https://example.com/x')).reason,'unapproved_url');
  assert.equal((await probeSource('http://www.boj.or.jp/x')).reason,'unapproved_url');
  const result=await probeSource('https://www.boj.or.jp/a',async (url,opts)=>{
    assert.equal(opts.redirect,'error'); assert.equal(opts.method,'GET');
    return new Response(null,{status:302});
  });
  assert.equal(result.reason,'http_error');
});
test('retrieved source receipt is never an economic verification', async () => {
  const result=await probeSource('https://www.boj.or.jp/x',async()=>new Response(
    '<!doctype html><html><body>Policy rate 1%</body></html>',
    {headers:{'content-type':'text/html'}}));
  assert.equal(result.status,'SOURCE_RETRIEVED_NOT_ECONOMICALLY_VERIFIED');
  assert.match(result.content_sha256,/^[a-f0-9]{64}$/);
  assert.equal('economic_target' in result,false);
});
test('malformed publisher payloads stay unresolved',async()=>{
  const result=await probeSource('https://www.boj.or.jp/x',async()=>new Response('not pdf',
    {headers:{'content-type':'application/pdf'}}));
  assert.equal(result.reason,'malformed_pdf');
});
test('candidate source audit preserves production safeguards',async()=>{
  const report=await auditGapSources(async()=>new Response('<html>ok</html>',
    {headers:{'content-type':'text/html'}}));
  assert.equal(report.candidate_count,6);
  assert.equal(report.mapping_status,'UNCONFIGURED');
  assert.equal(report.production_approval,'NOT_APPROVED');
  assert.equal(report.source_count, new Set([
    'https://www.boj.or.jp/en/research/brp/ron_2007/ron0707c.htm',
    'https://www.boj.or.jp/en/mopo/mpmsche_minu/minu_2007/g070221.pdf',
    'https://www.boj.or.jp/en/mopo/mpmdeci/state_2008/index.htm',
    'https://www.boj.or.jp/en/mopo/mpmsche_minu/minu_2018/g180731.htm',
    'https://www.boj.or.jp/en/mopo/mpmdeci/state_2021/k210319a.pdf',
  ]).size);
});
