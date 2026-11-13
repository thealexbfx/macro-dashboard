import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';

const inventory = JSON.parse(await readFile(new URL('./boj-historical-gap-candidates.json', import.meta.url)));
test('BOJ historical gap candidates cannot masquerade as verified observations', () => {
  assert.equal(inventory.scope, 'DISCOVERY_ONLY');
  assert.equal(inventory.historical_completeness, 'PARTIAL');
  assert.equal(inventory.mapping_status, 'UNCONFIGURED');
  assert.equal(inventory.commercial_rights, 'PENDING');
  assert.equal(inventory.production_approval, 'NOT_APPROVED');
  const dates = new Set();
  for (const candidate of inventory.candidates) {
    assert.match(candidate.decision_date, /^\d{4}-\d{2}-\d{2}$/);
    assert.equal(dates.has(candidate.decision_date), false);
    dates.add(candidate.decision_date);
    assert.equal(candidate.verification_status, 'SOURCE_DISCOVERY_PENDING');
    assert.match(candidate.corroborating_official_url, /^https:\/\/www\.boj\.or\.jp\//);
    assert.ok(candidate.source_url === null || candidate.source_url.startsWith('https://www.boj.or.jp/'));
    assert.ok(candidate.note.length > 20);
    assert.notEqual(candidate.verification_status, 'DOCUMENT_VERIFIED');
  }
  assert.ok(dates.has('2006-07-14'));
  assert.ok(dates.has('2007-02-21'));
  assert.ok(dates.has('2008-10-31'));
  assert.ok(dates.has('2008-12-19'));
  assert.ok(dates.has('2018-07-31'));
  assert.ok(dates.has('2021-03-19'));
});
