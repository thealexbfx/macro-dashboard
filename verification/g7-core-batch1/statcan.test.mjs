import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {parseManifest, verify} from './verify.mjs';
const rows = parseManifest(await readFile(new URL('manifest.csv', import.meta.url), 'utf8'));
const immediate = async () => {};
const row = mapping => rows.find(x => x.mapping_id === mapping);
const ok = object => Response.json([{status: 'SUCCESS', object: {responseStatusCode: 0, ...object}}]);
const metadata = (vectorId, productId, title) =>
  ok({vectorId, productId, SeriesTitleEn: title, frequencyCode: 6, terminated: 0, memberUomCode: 257});
const observations = (vectorId, value = 170) =>
  ok({vectorId, vectorDataPoint: [{refPer: '2026-09-01', value, frequencyCode: 6}]});

test('StatsCan CPI checks metadata then observations with POST and retains independent gates', async () => {
  let calls = 0;
  const r = await verify(row('G7-CA-07'), async (url, options) => {
    calls++;
    assert.equal(options.method, 'POST');
    assert.equal(options.redirect, 'error');
    const body = JSON.parse(options.body);
    assert.equal(body[0].vectorId, 41690973);
    if (url.endsWith('/getSeriesInfoFromVector'))
      return metadata(41690973, 18100004, 'Canada; All-items');
    assert.ok(url.endsWith('/getDataFromVectorsAndLatestNPeriods'));
    assert.equal(body[0].latestN, 5);
    return observations(41690973, 170);
  }, immediate);
  assert.equal(calls, 2);
  assert.equal(r.outcome, 'VERIFIED');
  assert.equal(r.verification_scope, 'RECENT_SAMPLE_ONLY');
  assert.equal(r.publisher_series_id, 'v41690973');
  assert.equal(r.history_status, 'SAMPLE_ONLY');
  assert.equal(r.rights_status, 'PENDING');
  assert.equal(r.production_approval, 'NOT_APPROVED');
  assert.equal(r.api_receipts.length, 2);
});

test('StatsCan unemployment checks metadata but does not infer full history or seasonality', async () => {
  const r = await verify(row('G7-CA-11'), async (url) =>
    url.endsWith('/getSeriesInfoFromVector')
      ? metadata(2062815, 14100287, 'Canada; Total - Gender; 15 years and over; Unemployment rate; Estimate; Seasonally adjusted')
      : observations(2062815, 6.7), immediate);
  assert.equal(r.outcome, 'VERIFIED');
  assert.equal(r.seasonal_adjustment, 'Seasonally adjusted');
  assert.equal(r.last_evidenced, '2026-09-01');
  assert.equal(r.vintage_status, 'NOT_ESTABLISHED');
});

test('StatsCan contradictory series title is MISMATCH and observations are never fetched', async () => {
  let calls = 0;
  const r = await verify(row('G7-CA-11'), async () => {
    calls++;
    return metadata(2062815, 14100287, 'Canada; Employment rate; Seasonally adjusted');
  }, immediate);
  assert.equal(calls, 1);
  assert.equal(r.outcome, 'MISMATCH');
  assert.equal(r.identity_status, 'MISMATCH');
});

test('StatsCan invalid JSON, missing vector and network errors cannot be verified', async () => {
  const malformed = await verify(row('G7-CA-07'), async () => new Response('<html>blocked</html>'), immediate);
  assert.equal(malformed.outcome, 'ACCESS_BLOCKED');
  assert.equal(malformed.identity_status, 'UNRESOLVED');
  const missing = await verify(row('G7-CA-07'), async () => Response.json([{status:'FAILURE', object:{responseStatusCode: 101}}]), immediate);
  assert.equal(missing.outcome, 'UNRESOLVED');
  const blocked = await verify(row('G7-CA-07'), async () => { throw Error('network'); }, immediate);
  assert.equal(blocked.outcome, 'ACCESS_BLOCKED');
  assert.equal(blocked.production_approval, 'NOT_APPROVED');
});

test('StatsCan unresolved observations do not advance an identity-matched candidate', async () => {
  const r = await verify(row('G7-CA-07'), async url =>
    url.endsWith('/getSeriesInfoFromVector')
      ? metadata(41690973, 18100004, 'Canada; All-items')
      : observations(41690973, null), immediate);
  assert.equal(r.outcome, 'UNRESOLVED');
  assert.equal(r.identity_status, 'MATCHED');
  assert.equal(r.history_status, 'NOT_ESTABLISHED');
});
