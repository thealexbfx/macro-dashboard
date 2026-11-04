import type {InvestigationV4} from './contracts';
import {migrateInvestigation, preserveOriginal,receiptMatches} from './investigation.ts';

export class ResearchConflict extends Error {constructor(){super('This research changed in another tab. Reload the saved copy or export your draft before continuing.');}}
export interface Draft {record:InvestigationV4; draft_revision:number; base_revision:number}
export interface ResearchRepository {
    list():Promise<InvestigationV4[]>; drafts():Promise<Draft[]>;
    read(id:string):Promise<{saved?:InvestigationV4;draft?:Draft}>;
    active():Promise<string|undefined>;
    importLegacy(raw:string|null):Promise<string[]>;
    writeDraft(record:InvestigationV4,expectedDraft:number):Promise<Draft>;
    save(record:InvestigationV4,expectedDraft:number):Promise<InvestigationV4>;
    warnings():string[];close():void;
}
const request=<T>(r:IDBRequest<T>)=>new Promise<T>((resolve,reject)=>{r.onsuccess=()=>resolve(r.result);r.onerror=()=>reject(r.error||new Error('Browser storage request failed'));});
export async function openResearchRepository(factory:IDBFactory=globalThis.indexedDB,name='macrolens-research'):Promise<ResearchRepository>{
    if(!factory)throw new Error('Browser-local research storage is unavailable. Your draft remains in memory.');
    const opening=factory.open(name,1);
    opening.onupgradeneeded=()=>{for(const store of ['saved','drafts','meta'])opening.result.createObjectStore(store);};
    const db=await new Promise<IDBDatabase>((resolve,reject)=>{opening.onsuccess=()=>resolve(opening.result);opening.onerror=()=>reject(opening.error||new Error('Browser storage could not open'));opening.onblocked=()=>reject(new Error('Close older MacroLens tabs to open local research storage'));});
    db.onversionchange=()=>db.close();
    function run<T>(stores:string[],mode:IDBTransactionMode,action:(tx:IDBTransaction)=>Promise<T>):Promise<T>{
        return new Promise((resolve,reject)=>{
            let value:T,reason:unknown;const tx=db.transaction(stores,mode);
            tx.oncomplete=()=>resolve(value);tx.onabort=()=>reject(reason||tx.error||new Error('Browser storage write was aborted'));
            tx.onerror=()=>{reason=tx.error||reason;};
            action(tx).then(v=>{value=v;}).catch(e=>{reason=e;try{tx.abort();}catch{reject(e);}});
        });
    }
    const issues=new Set<string>();
    const validated=(r:unknown)=>migrateInvestigation(r,new Date().toISOString());
    const validDraft=(d:Draft):Draft=>{if(!d||!Number.isInteger(d.draft_revision)||d.draft_revision<1||!Number.isInteger(d.base_revision)||d.base_revision<0||d.base_revision!==d.record?.revision)throw new Error('Invalid stored draft');return {...d,record:validated(d.record)};};
    return {
        warnings:()=>[...issues],close:()=>db.close(),
        list:()=>run(['saved'],'readonly',async tx=>{
            const records=await request<unknown[]>(tx.objectStore('saved').getAll());const result:InvestigationV4[]=[];
            for(const r of records){try{result.push(validated(r));}catch{issues.add('A corrupt or unsupported stored investigation was retained but could not be displayed.');}}
            return result;
        }),
        drafts:()=>run(['drafts'],'readonly',async tx=>{
            const records=await request<Draft[]>(tx.objectStore('drafts').getAll());const result:Draft[]=[];
            for(const d of records){try{result.push(validDraft(d));}catch{issues.add('A corrupt stored draft was retained but could not be displayed.');}}return result;
        }),
        active:()=>run(['meta'],'readonly',tx=>request<string|undefined>(tx.objectStore('meta').get('active'))),
        read:id=>run(['saved','drafts'],'readonly',async tx=>{
            const saved=await request<unknown>(tx.objectStore('saved').get(id));const draft=await request<Draft|undefined>(tx.objectStore('drafts').get(id));
            return {saved:saved?validated(saved):undefined,draft:draft?validDraft(draft):undefined};
        }),
        importLegacy:async raw=>{
            if(!raw)return [];const issues:string[]=[];let values:unknown;
            try{if(raw.length>5242880)throw new Error();values=JSON.parse(raw);if(!Array.isArray(values)||values.length>1000)throw new Error();}
            catch{return ['Older research could not be read. Its original browser copy was retained.'];}
            const valid:InvestigationV4[]=[];const seen=new Set<string>();
            for(const v of values as unknown[]){try{const r=validated(v);if(seen.has(r.id))throw new Error();seen.add(r.id);valid.push(r);}catch{issues.push('An unsupported or corrupt older record was retained in the original browser copy.');}}
            await run(['saved','drafts'],'readwrite',async tx=>{
                for(const r of valid){const saved=await request(tx.objectStore('saved').get(r.id));const draft=await request(tx.objectStore('drafts').get(r.id));if(!saved&&!draft)await request(tx.objectStore('saved').add(r,r.id));}
            });return issues;
        },
        writeDraft:(incoming,expectedDraft)=>{
            const r=validated(incoming);
            return run(['saved','drafts','meta'],'readwrite',async tx=>{
                const saved=await request<InvestigationV4|undefined>(tx.objectStore('saved').get(r.id));
                const prior=await request<Draft|undefined>(tx.objectStore('drafts').get(r.id));
                if(saved)validated(saved);
                if(prior)validDraft(prior);
                if((saved?.revision??0)!==r.revision||(prior?.draft_revision??0)!==expectedDraft)throw new ResearchConflict();
                const draft={record:preserveOriginal(r,prior?.record||saved),draft_revision:expectedDraft+1,base_revision:r.revision};
                await request(tx.objectStore('drafts').put(draft,r.id));await request(tx.objectStore('meta').put(r.id,'active'));return draft;
            });
        },
        save:(incoming,expectedDraft)=>{
            const r=validated(incoming);
            if(r.saved_calculation&&!receiptMatches(r,r.saved_calculation))throw new Error('Saved calculation does not match investigation parameters');
            return run(['saved','drafts','meta'],'readwrite',async tx=>{
                const saved=await request<InvestigationV4|undefined>(tx.objectStore('saved').get(r.id));const draft=await request<Draft|undefined>(tx.objectStore('drafts').get(r.id));
                if(saved)validated(saved);
                if(draft)validDraft(draft);
                if((saved?.revision??0)!==r.revision||(draft?.draft_revision??0)!==expectedDraft)throw new ResearchConflict();
                const record=preserveOriginal(r,saved||draft?.record);
                record.original_calculation=record.original_calculation||structuredClone(record.saved_calculation);
                record.revision=r.revision+1;record.updated_at=new Date().toISOString();
                await request(tx.objectStore('saved').put(record,r.id));await request(tx.objectStore('drafts').delete(r.id));await request(tx.objectStore('meta').put(r.id,'active'));return record;
            });
        },
    };
}
