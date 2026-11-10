import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {parseManifest, verify} from './verify.mjs';
import {getSeriesSpec, validateManifestRegistry} from './series-registry.mjs';
const csv = await readFile(new URL('manifest.csv', import.meta.url), 'utf8');
const rows = parseManifest(csv);
const immediate = async () => {};

test('one shared registry configures nine mappings and leaves 26 explicit exceptions', () => {
  assert.deepEqual(validateManifestRegistry(rows), {
    manifest_count: 35, configured_count: 9, unconfigured_count: 26,
  });
  assert.equal(getSeriesSpec('G7-CA-23').seriesId, 'BD.CDN.10YR.DQ.YLD');
  assert.equal(getSeriesSpec('G7-CA-07').adapter, 'statcan-wds');
  assert.equal(getSeriesSpec('G7-CA-01'), null);
});

test('all 35 pilot mappings produce an audit result without querying unconfigured sources', async () => {
  let networkCalls = 0;
  const outputs = await Promise.all(rows.map(row =>
    verify(row, async () => { networkCalls++; throw Error('network intentionally unavailable'); }, immediate)));
  assert.equal(outputs.length, 35);
  assert.equal(networkCalls, 27); // Three bounded attempts for each of nine registered mappings.
  assert.equal(outputs.filter(r => r.outcome === 'ACCESS_BLOCKED').length, 9);
  assert.equal(outputs.filter(r => r.outcome === 'UNRESOLVED').length, 26);
  assert.ok(outputs.every(r => r.production_approval === 'NOT_APPROVED'));
  assert.ok(outputs.every(r => r.rights_status === 'PENDING'));
});

test('optional 245-row manifest retains 35 pilot IDs and rejects missing IDs', () => {
  const header = csv.split(/\r?\n/)[0];
  const keys = header.split(',');
  const index = Object.fromEntries(keys.map((key,i)=>[key,i]));
  const countries = ['US','GB','DE','FR','IT','CA','JP'];
  const additional = [];
  for (const country of countries) {
    for (let n=1;n<=35;n++) {
      const id='G7-'+country+'-'+String(n).padStart(2,'0');
      if (rows.some(r=>r.mapping_id===id)) continue;
      const values = Array(keys.length).fill('');
      values[index.mapping_id] = id;
      values[index.operational_outcome] = 'NOT_TESTED';
      additional.push(values.map(v=>JSON.stringify(v)).join(','));
    }
  }
  assert.equal(additional.length, 210);
  const extended = header+'\n'+csv.trim().split(/\r?\n/).slice(1).join('\n')+'\n'+additional.join('\n');
  assert.equal(parseManifest(extended).length,245);
  assert.throws(()=>parseManifest(csv.replace('G7-CA-22','G7-CA-99')), /Unexpected/);
  assert.throws(()=>parseManifest(csv.replace('G7-CA-22','G7-CA-23')), /Unexpected/);
});

test('unconfigured country mappings cannot become approved by adding manifest rows', async () => {
  const row = rows.find(r=>r.mapping_id==='G7-US-01');
  const r = await verify(row, () => assert.fail('No adapter configured'), immediate);
  assert.equal(r.outcome,'UNRESOLVED');
  assert.equal(r.identity_status,'UNRESOLVED');
  assert.equal(r.access_status,'NOT_TESTED');
});
