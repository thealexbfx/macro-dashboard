import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
const data=JSON.parse(await readFile(new URL('./boj-2008-policy-target-candidates.json',import.meta.url)));
test('2008 original-source overnight target events remain development-only',()=>{
 assert.equal(data.production_approval,'NOT_APPROVED');
 assert.equal(data.commercial_rights,'PENDING');
 assert.equal(data.full_history_verified,false);
 assert.deepEqual(data.events.map(e=>[e.date,e.value_percent,e.change_basis_points]),
 [['2008-10-31',0.3,-20],['2008-12-19',0.1,-20]]);
 for(const e of data.events){
  assert.equal(e.instrument,'UNCOLLATERALIZED_OVERNIGHT_CALL_RATE_TARGET');
  assert.match(e.url,/^https:\/\/www\.boj\.or\.jp\/en\/mopo\/mpmdeci\/mpr_2008\/k\d+\.pdf$/);
  assert.equal(e.status,'ORIGINAL_DOCUMENT_MANUALLY_REVIEWED');
 }
});
