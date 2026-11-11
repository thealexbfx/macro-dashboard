import {test} from 'node:test';
import assert from 'node:assert/strict';
import {onsShapeDiagnostic} from './uk.mjs';
import {parseManifest, verify} from './verify.mjs';
import {readFile} from 'node:fs/promises';

const rows=parseManifest(await readFile(new URL('manifest.csv',import.meta.url),'utf8'));
const candidate=rows.find(r=>r.mapping_id==='G7-GB-07');
const immediate=async()=>{};

test('ONS diagnostic captures keys and types without values or full payload',()=>{
  const sensitive='A_PRIVATE_TOKEN_SHOULD_NEVER_APPEAR_IN_ARTIFACT';
  const payload={description:{cdid:null,description:null,unit:sensitive,
    anotherField:{secret:sensitive}},months:[{date:'2026 OCT',value:sensitive}],
    secretField:sensitive};
  const d=onsShapeDiagnostic(payload);
  assert.equal(d.schema_only,true);
  assert.equal(d.nested_cdid_type,'null');
  assert.ok(d.root_keys.includes('description'));
  assert.ok(d.description_keys.includes('unit'));
  assert.ok(d.first_month_keys.includes('date'));
  assert.equal(d.months_count,1);
  assert.ok(!JSON.stringify(d).includes(sensitive));
});

test('ONS missing metadata stays unresolved and returns safe shape diagnostic',async()=>{
  const payload={description:{title:'unverified title',cdid:null},
    months:[{date:'2026 OCT',value:'999.99'}]};
  const result=await verify(candidate,async()=>Response.json(payload),immediate);
  assert.equal(result.outcome,'UNRESOLVED');
  assert.equal(result.identity_status,'UNRESOLVED');
  assert.equal(result.production_approval,'NOT_APPROVED');
  assert.equal(result.rights_status,'PENDING');
  assert.equal(result.error_category,'missing_series_metadata');
  assert.equal(result.ons_response_shape.schema_only,true);
  assert.ok(!JSON.stringify(result.ons_response_shape).includes('999.99'));
  assert.ok(!JSON.stringify(result.ons_response_shape).includes('unverified title'));
});

test('ONS verified mocks are not burdened with diagnostic payload',async()=>{
  const result=await verify(candidate,async()=>Response.json({
    description:{cdid:'D7BT',description:'CPI INDEX 00: ALL ITEMS 2015=100'},
    months:[{date:'2026 OCT',value:'140.3'}]}),immediate);
  assert.equal(result.outcome,'VERIFIED');
  assert.equal(result.ons_response_shape,undefined);
});

test('ONS live publisher schema uses nested description.title, not description.description',async()=>{
  const sample={description:{cdid:'D7BT',datasetId:'MM23',title:'CPI INDEX 00: ALL ITEMS 2015=100',unit:'Index'},
    months:[{date:'2026 OCT',year:'2026',month:'OCT',value:'140.3'}]};
  const r=await verify(candidate,async()=>Response.json(sample),immediate);
  assert.equal(r.outcome,'VERIFIED');
  assert.equal(r.identity_status,'PUBLISHER_ID_AND_LABEL_MATCHED');
  assert.equal(r.metadata.cdid,'D7BT');
  assert.equal(r.metadata.dataset,'MM23');
  assert.equal(r.verification_scope,'RECENT_SAMPLE_ONLY');
  assert.equal(r.rights_status,'PENDING');
  assert.equal(r.production_approval,'NOT_APPROVED');
});
test('ONS real-schema missing CDID stays unresolved despite matching title and observations',async()=>{
  const r=await verify(candidate,async()=>Response.json({
    description:{title:'CPI INDEX 00: ALL ITEMS 2015=100'},
    months:[{date:'2026 OCT',value:'140.3'}]}),immediate);
  assert.equal(r.outcome,'UNRESOLVED');
  assert.equal(r.identity_status,'UNRESOLVED');
  assert.equal(r.ons_response_shape.nested_title_type,'string');
  assert.equal(r.production_approval,'NOT_APPROVED');
});

test('ONS schema-only title diagnostic distinguishes nested title from legacy description without exposing either value',()=>{
  const secret='DO_NOT_EXPORT_PUBLISHER_TITLE_VALUE';
  const current=onsShapeDiagnostic({description:{cdid:null,title:secret},months:[]});
  assert.equal(current.nested_title_type,'string');
  assert.equal(current.nested_cdid_type,'null');
  assert.equal(current.description_keys.includes('title'),true);
  assert.equal(JSON.stringify(current).includes(secret),false);
  const older=onsShapeDiagnostic({description:{description:secret},months:[]});
  assert.equal(older.nested_title_type,'undefined');
  assert.equal(JSON.stringify(older).includes(secret),false);
});
