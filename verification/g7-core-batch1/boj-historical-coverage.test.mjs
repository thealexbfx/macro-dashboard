import {test} from 'node:test';
import assert from 'node:assert/strict';
import {crosswalk} from './boj-historical-coverage.mjs';
test('unselected publisher dates are explicit, never fabricated observations',()=>{
 const result=crosswalk({periods:[{year:2008,census_status:'PUBLISHER_INDEX_DATES_EXTRACTED',
 listed_dates:['2008-10-31','2008-12-19']}]},[['2008-10-31','source.pdf']]);
 assert.deepEqual(result.periods[0].not_in_selected_manifest_dates,['2008-12-19']);
 assert.equal(result.periods[0].coverage_status,'SELECTED_MANIFEST_INCOMPLETE');
 assert.equal(result.production_approval,'NOT_APPROVED');
 assert.equal(result.full_meeting_census_verified,false);
});
test('unresolved publisher index cannot be declared covered',()=>{
 const r=crosswalk({periods:[{year:2006,census_status:'UNRESOLVED',listed_dates:[]}]},[]);
 assert.equal(r.periods[0].coverage_status,'UNRESOLVED');
});
