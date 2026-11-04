import test from 'node:test';
import assert from 'node:assert/strict';
import {IDBFactory} from 'fake-indexeddb';
import {newInvestigation,comparisonParameters,migrateInvestigation} from '../lib/investigation.ts';
import {attachCalculation,changeEvidence} from '../lib/research-evidence.ts';
import {openResearchRepository,ResearchConflict} from '../lib/research-repository.ts';
import {discoveryInvestigation,suggestionInvestigation} from '../lib/discovery.ts';
const now='2026-11-04T02:00:00Z';
const record=()=>newInvestigation('research',now,'2020-01-01','2024-12-31');
function comparison(r,revision='a'){
 return {datasets:r.datasets.map(id=>({id,name:`Label ${id}`})),raw_observations:{do_not_copy:[1,2]},provenance:{schema_version:1,method_version:'method-1',calculated_at:now,parameters:comparisonParameters(r),parameter_fingerprint:'b'.repeat(64),result_fingerprint:revision.repeat(64),datasets:r.datasets.map(id=>({dataset_id:id,definition_identifier:'c'.repeat(64),input_fingerprint:'d'.repeat(64),units:'Percent',frequency:'monthly',generation_references:['fixture-generation']})),effective_ranges:[],statistics:[{correlation:.45,observations:24}],limitations:['Latest revised observations'],exact_replay:{available:false,reason:'No frozen vintage'}}};
}
test('attaching captures exact independent configuration, labels, date and compact provenance',()=>{
 const r=record(),c=comparison(r);const attached=attachCalculation(r,c,'supporting_evidence','e1',now);const e=attached.supporting_evidence[0];assert.equal(e.capture.receipt.result_fingerprint,c.provenance.result_fingerprint);assert.equal(e.capture.dataset_labels.cpi,'Label cpi');assert.equal(e.capture.attached_at,now);assert.deepEqual(e.capture.workspace,r.workspace);assert.deepEqual(e.capture.receipt.parameters,comparisonParameters(r));assert.ok(!JSON.stringify(e).includes('do_not_copy'));c.provenance.statistics[0].correlation=.9;r.workspace.mode='overlay';assert.equal(e.capture.receipt.statistics[0].correlation,.45);assert.equal(e.capture.workspace.mode,'separate');
});
test('missing, stale, mismatched or duplicate calculations cannot create evidence',()=>{
 const r=record(),c=comparison(r);assert.throws(()=>attachCalculation(r,null,'supporting_evidence','e',now),/Calculate/);assert.throws(()=>attachCalculation({...r,start:'2021-01-01'},c,'supporting_evidence','e',now),/Calculate/);assert.throws(()=>attachCalculation(r,{...c,datasets:[]},'supporting_evidence','e',now),/references/);const next=attachCalculation(r,c,'supporting_evidence','e',now);assert.throws(()=>attachCalculation(next,c,'contradictory_evidence','e2',now),/already attached/);
});
test('annotations and classification changes retain evidence identity and frozen capture',()=>{
 const r=attachCalculation(record(),comparison(record()),'supporting_evidence','e',now);const changed=changeEvidence(r,'e','An alternative interpretation','contradictory_evidence');assert.equal(changed.supporting_evidence.length,0);assert.equal(changed.contradictory_evidence[0].id,'e');assert.deepEqual(changed.contradictory_evidence[0].capture,r.supporting_evidence[0].capture);assert.equal(changed.contradictory_evidence[0].note,'An alternative interpretation');
});
test('same-ID edits preserve first evidence captures and history even if current charts are unavailable',async()=>{
 const db=await openResearchRepository(new IDBFactory());try{
 let r=attachCalculation(record(),comparison(record()),'supporting_evidence','e',now);r.saved_calculation=comparison(r).provenance;r.conclusion='Provisional';await db.writeDraft(r,0);r=await db.save(r,1);const original=structuredClone(r.supporting_evidence[0]);
 let edited={...r,research_question:'Updated question',end:'2023-12-31',conclusion:'Reconsidered',supporting_evidence:r.supporting_evidence.map(e=>({...e,note:'My annotation',capture:{...e.capture,attached_at:'2026-11-05T00:00:00Z'}}))};await db.writeDraft(edited,0);const saved=await db.save(edited,1);assert.equal(saved.revision,2);assert.equal((await db.list()).length,1);assert.equal(saved.conclusion,'Reconsidered');assert.deepEqual(saved.saved_calculation,r.saved_calculation);assert.deepEqual(saved.supporting_evidence[0].capture,original.capture);assert.equal(saved.supporting_evidence[0].note,'My annotation');await assert.rejects(db.save(r,0),ResearchConflict);
 }finally{db.close();}
});
test('corrupt evidence captures fail closed and PR1 references without receipts still migrate',()=>{
 const old={...record(),supporting_evidence:[{id:'old',dataset_ids:['retired'],start:null,end:null,calculation_fingerprint:null,note:'Legacy note'}]};assert.equal(migrateInvestigation(old,now).supporting_evidence[0].capture,undefined);
 const r=attachCalculation(record(),comparison(record()),'supporting_evidence','e',now);for(const mutate of [e=>e.capture.receipt.result_fingerprint='f'.repeat(64),e=>e.capture.dataset_labels.cpi={},e=>e.capture.receipt.datasets=[],e=>e.capture.attached_at='never']){const copy=structuredClone(r);mutate(copy.supporting_evidence[0]);assert.throws(()=>migrateInvestigation(copy,now));}
});
test('Discovery and followup questions retain original evidence and settings independently',()=>{
 const r=record(),finding={headline:'Observed pattern',configuration:{datasets:r.datasets,start:r.start,end:r.end,workspace:r.workspace},suggestions:[{label:'Why might this relationship change?'}]},report={generated_at:now,snapshot_fingerprint:'origin'};const d=discoveryInvestigation(finding,report,'d');assert.equal(d.research_question,finding.suggestions[0].label);const suggestion={label:'What happens in another period?',origin:'Followup',context:'Compare',configuration:{...finding.configuration,start:'2021-01-01'}};const followup=suggestionInvestigation(finding,suggestion,report,'f');assert.equal(followup.research_question,suggestion.label);assert.equal(followup.start,'2021-01-01');assert.equal(followup.discovery.finding.configuration.start,'2020-01-01');finding.headline='Revised';assert.equal(d.discovery.finding.headline,'Observed pattern');
});
test('repository upgrade preserves v1 saves and fences clients that would strip new capture fields',async()=>{
 const factory=new IDBFactory();const old=await new Promise(resolve=>{const q=factory.open('macrolens-research',1);q.onupgradeneeded=()=>{for(const n of ['saved','drafts','meta'])q.result.createObjectStore(n);};q.onsuccess=()=>resolve(q.result);});await new Promise(resolve=>{const t=old.transaction('saved','readwrite');t.objectStore('saved').put(record(),'research');t.oncomplete=resolve;});old.onversionchange=()=>old.close();const db=await openResearchRepository(factory);assert.equal((await db.list())[0].id,'research');await assert.rejects(new Promise((resolve,reject)=>{const q=factory.open('macrolens-research',1);q.onsuccess=()=>{q.result.close();resolve();};q.onerror=()=>reject(q.error);}),{name:'VersionError'});db.close();
});
test('new attachments committed in a draft cannot be rewritten by a later explicit save',async()=>{
 const db=await openResearchRepository(new IDBFactory());try{let r=await db.save(record(),0);r=attachCalculation(r,comparison(r),'supporting_evidence','new-draft-evidence',now);await db.writeDraft(r,0);const tampered=structuredClone(r);tampered.supporting_evidence[0].capture.attached_at='2026-11-05T00:00:00Z';const saved=await db.save(tampered,1);assert.equal(saved.supporting_evidence[0].capture.attached_at,now);}finally{db.close();}
});
