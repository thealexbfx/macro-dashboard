import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {parseManifest, verify} from './verify.mjs';
const rows=parseManifest(await readFile(new URL('manifest.csv',import.meta.url),'utf8'));
const mapping=id=>rows.find(r=>r.mapping_id===id);
const immediate=async()=>{};
const blsResponse=(id,period='M09')=>Response.json({status:'REQUEST_SUCCEEDED',message:[],
  Results:{series:[{seriesID:id,data:[{year:'2026',period,value:'330.8'}]}]}});
test('BLS CPI uses official POST and only validates returned series id and recent observations',async()=>{
  const r=await verify(mapping('G7-US-07'),async(url,opts)=>{
    assert.equal(url,'https://api.bls.gov/publicAPI/v1/timeseries/data/');
    assert.equal(opts.method,'POST');
    assert.deepEqual(JSON.parse(opts.body),{seriesid:['CUUR0000SA0']});
    return blsResponse('CUUR0000SA0');
  },immediate);
  assert.equal(r.outcome,'VERIFIED');
  assert.equal(r.identity_status,'PUBLISHER_ID_MATCHED');
  assert.equal(r.verification_scope,'RECENT_SAMPLE_ONLY');
  assert.equal(r.history_status,'SAMPLE_ONLY');
  assert.equal(r.rights_status,'PENDING');
  assert.equal(r.production_approval,'NOT_APPROVED');
});
test('BLS returned incorrect identifier is mismatch; invalid payload is unresolved',async()=>{
  const wrong=await verify(mapping('G7-US-11'),async()=>blsResponse('LNS14000006'),immediate);
  assert.equal(wrong.outcome,'MISMATCH');
  const invalid=await verify(mapping('G7-US-07'),async()=>new Response('<html>blocked</html>'),immediate);
  assert.equal(invalid.outcome,'UNRESOLVED');
  assert.equal(invalid.identity_status,'UNRESOLVED');
});
const ecbCsv='KEY,FREQ,REF_AREA,PROVIDER_FM_ID,TIME_PERIOD,OBS_VALUE\nFM.B.U2.EUR.4F.KR.DFR.LEV,B,U2,DFR,2026-11-06,2.25\n';
test('three national policy mappings share one canonical ECB source but remain separate mapping records',async()=>{
  const keys=new Set();
  for(const country of ['DE','FR','IT']){
    const r=await verify(mapping('G7-'+country+'-22'),async(url,opts)=>{
      assert.match(url,/^https:\/\/data-api\.ecb\.europa\.eu\/service\/data\/FM\//);
      assert.equal(opts.method,'GET');
      return new Response(ecbCsv,{status:200,headers:{'content-type':'text/csv'}});
    },immediate);
    assert.equal(r.outcome,'VERIFIED');
    assert.equal(r.verification_scope,'RECENT_SAMPLE_ONLY');
    assert.equal(r.production_approval,'NOT_APPROVED');
    assert.equal(r.rights_status,'PENDING');
    keys.add(r.canonical_series_key);
  }
  assert.equal(keys.size,1);
});
test('ECB unmatched dimensions are mismatch, missing schema is unresolved',async()=>{
  const wrong=ecbCsv.replace('DFR,2026','MLFR,2026');
  const bad=await verify(mapping('G7-DE-22'),async()=>new Response(wrong),immediate);
  assert.equal(bad.outcome,'MISMATCH');
  const malformed=await verify(mapping('G7-DE-22'),async()=>new Response('time,value\n2026-11-06,2.25\n'),immediate);
  assert.equal(malformed.outcome,'UNRESOLVED');
});
test('publisher transport failures never imply invalid economic series',async()=>{
  for(const id of ['G7-US-07','G7-DE-22']){
    const r=await verify(mapping(id),async()=>{throw Error('network');},immediate);
    assert.equal(r.outcome,'ACCESS_BLOCKED');
    assert.equal(r.identity_status,'UNRESOLVED');
  }
});
