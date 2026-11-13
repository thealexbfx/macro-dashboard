import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {parseManifest,verify} from './verify.mjs';
const rows=parseManifest(await readFile(new URL('manifest.csv',import.meta.url),'utf8'));
const row=id=>rows.find(r=>r.mapping_id===id);
const immediate=async()=>{};
const ons=(cdid,description)=>Response.json({cdid,description,unit:'%',months:[
  {date:'2026 SEP',value:'4.6'},{date:'2026 OCT',value:'4.7'}]});
test('ONS unemployment is a rolling 3-month rate, not single-month labour data',async()=>{
  const r=await verify(row('G7-GB-11'),async(url,options)=>{
    assert.equal(options.method,'GET');
    assert.match(url,/\/timeseries\/mgsx\/lms\/data$/);
    return ons('MGSX','Unemployment rate (aged 16 and over, seasonally adjusted): %');
  },immediate);
  assert.equal(r.outcome,'VERIFIED');
  assert.equal(r.publisher_series_id,'MGSX');
  assert.match(r.frequency,/Rolling 3-month/);
  assert.equal(r.production_approval,'NOT_APPROVED');
  assert.equal(r.rights_status,'PENDING');
});
test('ONS CPI publisher title, route and recent observations establish sample only',async()=>{
  const r=await verify(row('G7-GB-07'),async()=>ons('D7BT','CPI INDEX 00: ALL ITEMS 2015=100'),immediate);
  assert.equal(r.outcome,'VERIFIED');
  assert.equal(r.last_evidenced,'2026-10');
  assert.equal(r.verification_scope,'RECENT_SAMPLE_ONLY');
  assert.equal(r.vintage_status,'NOT_ESTABLISHED');
});
test('ONS ID conflicts, HTML and missing samples are never VERIFIED',async()=>{
  const wrong=await verify(row('G7-GB-07'),async()=>ons('D7G7','CPI INDEX 00: ALL ITEMS 2015=100'),immediate);
  assert.equal(wrong.outcome,'MISMATCH');
  const html=await verify(row('G7-GB-07'),async()=>new Response('<html>Error</html>'),immediate);
  assert.equal(html.outcome,'UNRESOLVED');
  const empty=await verify(row('G7-GB-07'),async()=>Response.json({cdid:'D7BT',description:'CPI INDEX 00: ALL ITEMS',months:[]}),immediate);
  assert.equal(empty.outcome,'UNRESOLVED');
});
test('Bank of England official Bank Rate validates returned column and recent date',async()=>{
  const r=await verify(row('G7-GB-22'),async(url,options)=>{
    assert.equal(options.method,'GET');
    assert.match(url,/SeriesCodes=IUDBEDR/);
    return new Response('DATE,IUDBEDR\r\n05 Nov 2026,4.00\r\n09 Nov 2026,4.00\r\n');
  },immediate);
  assert.equal(r.outcome,'VERIFIED');
  assert.equal(r.publisher_series_id,'IUDBEDR');
  assert.equal(r.last_evidenced,'2026-11-09');
  assert.equal(r.observations.length,2);
  assert.equal(r.rights_status,'PENDING');
});
test('BoE missing column and upstream access failures keep gates locked',async()=>{
  const r=await verify(row('G7-GB-22'),async()=>new Response('DATE,WRONG\n05 Nov 2026,4.00'),immediate);
  assert.equal(r.outcome,'UNRESOLVED');
  const blocked=await verify(row('G7-GB-22'),async()=>{throw Error('network');},immediate);
  assert.equal(blocked.outcome,'ACCESS_BLOCKED');
  assert.equal(blocked.production_approval,'NOT_APPROVED');
});

test('ONS publisher nested description metadata is accepted only with exact CDID',async()=>{
  const nested={description:{cdid:'D7BT',datasetId:'MM23',description:'CPI INDEX 00: ALL ITEMS 2015=100',unit:'Index'},
    months:[{date:'2026 OCT',value:'140.3'}]};
  const passed=await verify(row('G7-GB-07'),async()=>Response.json(nested),immediate);
  assert.equal(passed.outcome,'VERIFIED');
  assert.equal(passed.identity_status,'PUBLISHER_ID_AND_LABEL_MATCHED');
  assert.equal(passed.metadata.dataset,'MM23');
  const noId=await verify(row('G7-GB-07'),async()=>Response.json({
    description:{description:nested.description.description},months:nested.months}),immediate);
  assert.equal(noId.outcome,'UNRESOLVED');
  const conflict=await verify(row('G7-GB-07'),async()=>Response.json({
    ...nested,description:{...nested.description,cdid:'D7BZ'}}),immediate);
  assert.equal(conflict.outcome,'MISMATCH');
  assert.equal(conflict.production_approval,'NOT_APPROVED');
});
