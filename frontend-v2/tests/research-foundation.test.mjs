import test from 'node:test';
import assert from 'node:assert/strict';
import {IDBFactory,IDBObjectStore} from 'fake-indexeddb';
import {newInvestigation,migrateInvestigation,comparisonParameters,receiptMatches,validateReceipt} from '../lib/investigation.ts';
import {openResearchRepository,ResearchConflict} from '../lib/research-repository.ts';
const now='2026-11-03T12:00:00Z';
const make=(id='one')=>newInvestigation(id,now,'2020-01-01','2025-12-31');
const receipt=(r,value='a')=>({schema_version:1,method_version:'test-1',calculated_at:now,parameters:comparisonParameters(r),parameter_fingerprint:'b'.repeat(64),result_fingerprint:value.repeat(64),datasets:[],effective_ranges:[],statistics:[{correlation:.4,observations:42}],limitations:['Revised data'],exact_replay:{available:false,reason:'No frozen observations'}});
const repository=()=>openResearchRepository(new IDBFactory());
test('legacy migration preserves IDs, unknown dataset references and notes without inventing historical timestamps',()=>{
 for(const version of [2,3]){const old={...make('legacy'),version,datasets:['retired','private'],note:'Keep',created_at:undefined,updated_at:undefined};const before=JSON.stringify(old);const r=migrateInvestigation(old,now);assert.equal(r.version,4);assert.equal(r.created_at,null);assert.equal(r.updated_at,null);assert.equal(r.migrated_at,now);assert.deepEqual(r.datasets,old.datasets);assert.equal(JSON.stringify(old),before);assert.equal(r.original_calculation,null);}
});
test('unsupported and corrupt legacy records stay untouched and import is additive/idempotent',async()=>{
 const db=await repository();try{const raw=JSON.stringify([{...make('valid'),version:3},{version:99},null,{...make('bad'),workspace:{hidden:12}}]);const issues=await db.importLegacy(raw);assert.equal(issues.length,3);assert.equal((await db.list()).length,1);await db.importLegacy(raw);assert.equal((await db.list()).length,1);await db.importLegacy(JSON.stringify([{...make('later'),version:2}]));assert.equal((await db.list()).length,2);assert.match((await db.importLegacy('broken'))[0],/retained/);}finally{db.close();}
});
test('acknowledged draft survives connection close and reopen including structured fields',async()=>{
 const f=new IDBFactory();let db=await openResearchRepository(f);const r={...make(),research_question:'Why?',working_hypothesis:'Policy',conclusion:'Uncertain',supporting_evidence:[{id:'e1',dataset_ids:['cpi'],start:null,end:null,calculation_fingerprint:null,note:'Reference'}]};await db.writeDraft(r,0);db.close();db=await openResearchRepository(f);try{const d=(await db.read(r.id)).draft;assert.deepEqual(d.record,r);assert.equal(d.draft_revision,1);assert.equal(await db.active(),r.id);}finally{db.close();}
});
test('same-ID saves update one record and retain creation time, first receipt and original Discovery',async()=>{
 const db=await repository();try{const r=make();r.discovery={generated_at:now,snapshot_fingerprint:'origin',finding:{type:'correlation',headline:'Original',label:'Evidence',datasets:['cpi'],observation_date:'2025-01-01',evidence:{baseline:{start:r.start,end:r.end}},configuration:{start:r.start,end:r.end}}};r.saved_calculation=receipt(r);await db.writeDraft(r,0);const saved=await db.save(r,1);assert.equal(saved.revision,1);const edited={...saved,note:'Reconsidered',conclusion:'My conclusion',saved_calculation:receipt(saved,'c'),discovery:{...r.discovery,snapshot_fingerprint:'changed'}};await db.writeDraft(edited,0);const second=await db.save(edited,1);assert.equal(second.id,r.id);assert.equal(second.revision,2);assert.equal(second.created_at,now);assert.equal(second.discovery.snapshot_fingerprint,'origin');assert.equal(second.original_calculation.result_fingerprint,'a'.repeat(64));assert.equal(second.saved_calculation.result_fingerprint,'c'.repeat(64));assert.equal((await db.list()).length,1);assert.equal((await db.drafts()).length,0);}finally{db.close();}
});
test('transaction conflicts preserve newer same-ID writes while independent records remain separate',async()=>{
 const db=await repository();try{const a=make(),b=make('two');await Promise.all([db.writeDraft(a,0),db.writeDraft(b,0)]);await assert.rejects(db.writeDraft({...a,note:'stale'},0),ResearchConflict);const saved=await db.save(a,1);await assert.rejects(db.save(a,0),ResearchConflict);assert.equal((await db.read(a.id)).saved.revision,saved.revision);assert.equal((await db.read(b.id)).draft.record.id,'two');}finally{db.close();}
});
test('quota failure aborts whole write, rejects acknowledgement and preserves prior durable draft',async()=>{
 const db=await repository();const original=IDBObjectStore.prototype.put;try{await db.writeDraft(make(),0);IDBObjectStore.prototype.put=function(...args){if(this.name==='meta')throw new DOMException('Quota full','QuotaExceededError');return original.apply(this,args);};await assert.rejects(db.writeDraft({...make(),note:'not committed'},1),/Quota full/);IDBObjectStore.prototype.put=original;assert.equal((await db.read('one')).draft.record.note,'');assert.equal((await db.read('one')).draft.draft_revision,1);}finally{IDBObjectStore.prototype.put=original;db.close();}
});
test('unavailable storage rejects clearly; corrupt canonical records are retained with visible warning',async()=>{
 await assert.rejects(openResearchRepository(null),/unavailable/);const factory=new IDBFactory(),db=await openResearchRepository(factory);const opened=await new Promise(resolve=>{const q=factory.open('macrolens-research');q.onsuccess=()=>resolve(q.result);});await new Promise(resolve=>{const t=opened.transaction('saved','readwrite');t.objectStore('saved').put({version:99},'corrupt');t.oncomplete=resolve;});assert.deepEqual(await db.list(),[]);assert.match(db.warnings()[0],/retained/);const kept=await new Promise(resolve=>{const q=opened.transaction('saved').objectStore('saved').get('corrupt');q.onsuccess=()=>resolve(q.result);});assert.equal(kept.version,99);opened.close();db.close();
});
test('receipt consistency rejects stale settings and full observation arrays',async()=>{
 const r=make(),p=receipt(r);assert.ok(receiptMatches(r,p));assert.equal(receiptMatches({...r,start:'2021-01-01'},p),false);assert.throws(()=>validateReceipt({...p,statistics:[{rolling:[1,2]}]}),/arrays/);const db=await repository();try{await assert.rejects(async()=>db.save({...r,start:'2021-01-01',saved_calculation:p},0),/does not match/);}finally{db.close();}
});
test('malformed saved origins cannot reach evidence renderers',()=>{
 for(const discovery of [{finding:{}},{generated_at:now,snapshot_fingerprint:'x',finding:{type:'correlation',headline:{bad:true}}}])assert.throws(()=>migrateInvestigation({...make(),discovery},now));
 assert.throws(()=>migrateInvestigation({...make(),start:'2025-02-30'},now));
});
