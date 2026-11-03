import test from 'node:test';
import assert from 'node:assert/strict';
import {storedSourceDetails,formatDatasetValue,referenceLabel} from '../lib/presentation.ts';
test('approved synthetic commodity uses existing Explorer/Investigate display with provenance',()=>{
 const d={id:'fixture_copper',name:'Synthetic copper',frequency:'monthly',status:'ok',
  units:'USD / metric tonne',latest_value:1234.567,latest_observation_date:'2025-12-01',
  stored_provenance:{benchmark:'Synthetic benchmark',attribution:['Synthetic supplier'],
  license_url:'https://example.invalid/license',source_unit:'($/mt)',
  stored_start:'1960-01',stored_end:'2025-12',reference_convention:'Economic month',
  ai_allowed:false}};
 assert.equal(formatDatasetValue(d),'$1,234.57');
 assert.match(referenceLabel(d),/Dec 2025/);
 assert(storedSourceDetails(d).some(([k,v])=>k==='Attribution'&&v==='Synthetic supplier'));
 assert(storedSourceDetails(d).some(([k,v])=>k==='AI use'&&v==='Not enabled'));
});
test('legacy datasets do not acquire commodity provenance or private pilot fixtures',()=>{
 assert.deepEqual(storedSourceDetails({id:'cpi'}),[]);
});

