import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {parseManifest,verify} from './verify.mjs';
import {parseTreasuryAtom} from './treasury.mjs';
const rows=parseManifest(await readFile(new URL('manifest.csv',import.meta.url),'utf8'));
const row=rows.find(x=>x.mapping_id==='G7-US-23');
const immediate=async()=>{};
const xml=(v='4.88')=>`<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:d="http://schemas.microsoft.com/ado/2007/08/dataservices" xmlns:m="http://schemas.microsoft.com/ado/2007/08/dataservices/metadata">
<entry><content><m:properties><d:NEW_DATE m:type="Edm.DateTime">2026-11-09T00:00:00</d:NEW_DATE><d:BC_10YEAR m:type="Edm.Double">${v}</d:BC_10YEAR></m:properties></content></entry>
</feed>`;
test('Treasury official XML feed validates 10-year field and sampled date',async()=>{
  const r=await verify(row,async(url,options)=>{
    assert.match(url,/^https:\/\/home\.treasury\.gov\/resource-center\/data-chart-center\/interest-rates\/pages\/xml\?data=daily_treasury_yield_curve&field_tdr_date_value_month=\d{6}$/);
    assert.equal(options.method,'GET');
    assert.equal(options.redirect,'error');
    return new Response(xml());
  },immediate);
  assert.equal(r.outcome,'VERIFIED');
  assert.equal(r.identity_status,'PUBLISHER_FEED_FIELD_MATCHED');
  assert.equal(r.last_evidenced,'2026-11-09');
  assert.equal(r.observations[0].value,'4.88');
  assert.equal(r.verification_scope,'RECENT_SAMPLE_ONLY');
  assert.equal(r.history_status,'SAMPLE_ONLY');
  assert.equal(r.rights_status,'PENDING');
  assert.equal(r.production_approval,'NOT_APPROVED');
});
test('Malformed XML, alternate tenor and HTML never verify',async()=>{
  assert.equal(parseTreasuryAtom('<!DOCTYPE x><feed/>'),null);
  assert.equal(parseTreasuryAtom(xml(),'BC_30YEAR'),null);
  assert.deepEqual(parseTreasuryAtom(xml('not-a-number')),[]);
  const other=await verify(row,async()=>new Response(xml().replaceAll('BC_10YEAR','BC_20YEAR')),immediate);
  assert.equal(other.outcome,'UNRESOLVED');
  const html=await verify(row,async()=>new Response('<html>proxy error</html>'),immediate);
  assert.equal(html.outcome,'UNRESOLVED');
});
test('Treasury transport failure is not an economic-series mismatch',async()=>{
  const r=await verify(row,async()=>{throw new Error('network blocked');},immediate);
  assert.equal(r.outcome,'ACCESS_BLOCKED');
  assert.equal(r.identity_status,'UNRESOLVED');
  assert.equal(r.production_approval,'NOT_APPROVED');
});
