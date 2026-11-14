import {test} from 'node:test';import assert from 'node:assert/strict';import {readFile} from 'node:fs/promises';const d=JSON.parse(await readFile(new URL('./boj-2006-2008-rate-regime-anchors.json',import.meta.url)));test('BOJ 2006–2008 rate anchors preserve instrument, provenance and unresolved zero semantics',()=>{assert.equal(d.production_approval,'NOT_APPROVED');assert.equal(d.full_history_verified,false);assert.deepEqual(d.anchors.map(a=>a.date),['2006-03-09','2006-07-14','2007-02-21','2008-10-31','2008-12-19']);assert.deepEqual(d.anchors.map(a=>a.target_percent),[null,0.25,0.5,0.3,0.1]);for(const a of d.anchors){assert.equal(a.instrument,'UNCOLLATERALIZED_OVERNIGHT_CALL_RATE');assert.match(a.source_url,/^https:\/\/www\.boj\.or\.jp\//);assert.ok(a.status);}});

test('original decision evidence supports immediate numeric changes only', () => {
  for (const anchor of d.anchors) {
    assert.equal(anchor.source_type, 'ORIGINAL_POLICY_DECISION');
    assert.equal(anchor.status, 'ORIGINAL_DOCUMENT_MANUALLY_REVIEWED');
    const numeric = anchor.target_percent !== null;
    assert.equal(anchor.effective_date, numeric ? anchor.date : null);
    assert.equal(anchor.effective_date_status,
      numeric ? 'IMMEDIATE_PER_DECISION' : 'NOT_STATED_IN_REVIEWED_GUIDELINE');
    assert.match(anchor.source_url, /\/mopo\/mpmdeci\/mpr_20\d{2}\//);
  }
});
