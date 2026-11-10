import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {parseManifest, verify} from './verify.mjs';

const rows = parseManifest(await readFile(new URL('manifest.csv', import.meta.url), 'utf8'));
const candidate = rows.find(row => row.mapping_id === 'G7-CA-22');
const immediate = async () => {};
const check = transport => verify(candidate, transport, immediate);
const label = 'Target for the overnight rate';
const sample = (observations, seriesDetail = {V39079: {label}}) =>
  Response.json({seriesDetail, observations});

test('manifest preserves 35 mappings and three euro-area countries share one ECB series', async () => {
  assert.equal(rows.length, 35);
  const keys = new Set();
  for (const country of ['DE', 'FR', 'IT']) {
    const row = rows.find(row => row.mapping_id === 'G7-' + country + '-22');
    const result = await verify(row, async () => { throw new Error('simulated offline'); }, immediate);
    keys.add(result.canonical_series_key);
    assert.equal(result.canonical_series_key, 'ECB:B.U2.EUR.4F.KR.DFR.LEV');
    assert.equal(result.outcome, 'ACCESS_BLOCKED');
    assert.equal(result.identity_status, 'UNRESOLVED');
    assert.equal(result.production_approval, 'NOT_APPROVED');
    assert.equal(result.rights_status, 'PENDING');
  }
  assert.equal(keys.size, 1);
});

test('matched publisher and old samples establish neither discontinuation nor history, vintages or rights', async () => {
  const result = await check(async (url, options) => {
    assert.match(url, /^https:\/\/www\.bankofcanada\.ca\/valet\/observations\/V39079/);
    assert.equal(options.method, 'GET');
    assert.equal(options.redirect, 'error');
    return sample([{d: '2000-01-04', V39079: {v: '4.5'}}]);
  });
  assert.equal(result.outcome, 'VERIFIED');
  assert.equal(result.first_evidenced, '2000-01-04');
  assert.equal(result.last_evidenced, '2000-01-04');
  assert.equal(result.verification_scope, 'RECENT_SAMPLE_ONLY');
  assert.equal(result.production_approval, 'NOT_APPROVED');
  assert.equal(result.history_status, 'SAMPLE_ONLY');
  assert.equal(result.vintage_status, 'NOT_ESTABLISHED');
  assert.equal(result.rights_status, 'PENDING');
});

test('a conflicting publisher label is a mismatch', async () => {
  const result = await check(async () => sample([], {V39079: {label: 'Wrong series'}}));
  assert.equal(result.outcome, 'MISMATCH');
  assert.equal(result.error_category, 'invalid_metadata');
});

test('no usable observations leaves the candidate unresolved', async () => {
  const result = await check(async () => sample([{d: '2020-01-02', V39079: {v: ''}}]));
  assert.equal(result.outcome, 'UNRESOLVED');
  assert.equal(result.first_evidenced, null);
  assert.equal(result.vintage_status, 'NOT_ESTABLISHED');
});

test('network failures leave identity unresolved', async () => {
  const result = await check(async () => { throw new Error('DNS unavailable'); });
  assert.equal(result.outcome, 'ACCESS_BLOCKED');
  assert.equal(result.identity_status, 'UNRESOLVED');
  assert.equal(result.attempt, 3);
});

test('429 and 5xx retry, then preserve the terminal HTTP receipt', async () => {
  let attempts = 0;
  const result = await check(async () => new Response(null, {status: [429, 503, 502][attempts++]}));
  assert.equal(attempts, 3);
  assert.equal(result.http_status, 502);
  assert.equal(result.outcome, 'ACCESS_BLOCKED');
});

test('oversize response never produces a verified observation', async () => {
  const result = await check(async () => new Response('x'.repeat(65537)));
  assert.equal(result.error_category, 'response_too_large');
  assert.deepEqual(result.observations, []);
});

test('invalid JSON and malformed payloads leave identity unresolved', async () => {
  for (const [response, error] of [
    [new Response('<html>upstream error</html>'), 'invalid_json'],
    [Response.json(null), 'malformed_payload'],
    [sample([], {V39079: {}}), 'malformed_payload'],
    [sample({}), 'malformed_payload'],
  ]) {
    const result = await check(async () => response);
    assert.equal(result.outcome, 'UNRESOLVED');
    assert.equal(result.identity_status, 'UNRESOLVED');
    assert.equal(result.access_status, 'RETRIEVED');
    assert.equal(result.http_status, 200);
    assert.equal(result.error_category, error);
    assert.equal(result.production_approval, 'NOT_APPROVED');
  }
});

const yieldCandidate = rows.find(row => row.mapping_id === 'G7-CA-23');
test('Canada 10-year yield uses the publisher Valet series identifier rather than legacy V39055', async () => {
  const series = 'BD.CDN.10YR.DQ.YLD';
  const result = await verify(yieldCandidate, async (url, options) => {
    assert.equal(url, 'https://www.bankofcanada.ca/valet/observations/' + series + '/json?recent=5');
    assert.equal(options.method, 'GET');
    return Response.json({seriesDetail: {[series]: {label: 'Benchmark bond yield, 10-year', description: 'The yield on the Government of Canada 10-year benchmark bond.'}}, observations: [{d: '2026-11-06', [series]: {v: '3.65'}}]});
  }, immediate);
  assert.equal(result.outcome, 'VERIFIED');
  assert.equal(result.verification_scope, 'RECENT_SAMPLE_ONLY');
  assert.equal(result.history_status, 'SAMPLE_ONLY');
  assert.equal(result.rights_status, 'PENDING');
  assert.equal(result.production_approval, 'NOT_APPROVED');
});
