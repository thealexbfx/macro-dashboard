'use client';
import {useCallback,useEffect,useRef,useState} from 'react';
import type {CalculationReceipt,Investigation,InvestigationV4} from './contracts';
import {migrateInvestigation,newInvestigation} from './investigation';
import {openResearchRepository,type Draft,type ResearchRepository} from './research-repository';
import {timeframeStart} from './presentation';

// Stable server AND first-client state. Actual date/UUID/storage are read only after mount.
const initial=()=>newInvestigation('initializing','2000-01-01T00:00:00Z','1995-01-01','2000-01-01');
export function useResearchFoundation(){
    const [record,setState]=useState<InvestigationV4>(initial),[ready,setReady]=useState(false),[restored,setRestored]=useState(false),[saved,setSaved]=useState<InvestigationV4[]>([]),[drafts,setDrafts]=useState<Draft[]>([]),[status,setStatus]=useState('Opening local research…'),[error,setError]=useState(''),[warning,setWarning]=useState('');
    const repo=useRef<ResearchRepository|null>(null),current=useRef(record),change=useRef(0),ack=useRef(-1),draftVersions=useRef(new Map<string,number>()),queue=useRef<Promise<unknown>>(Promise.resolve());
    const setRecord=useCallback((update:InvestigationV4|((p:InvestigationV4)=>InvestigationV4))=>{
        const next=typeof update==='function'?update(current.current):update;
        current.current={...next,updated_at:new Date().toISOString()};change.current++;setState(current.current);setStatus('Draft changes not yet saved');
    },[]);
    const enqueue=useCallback(<T,>(action:()=>Promise<T>):Promise<T>=>{const p=queue.current.catch(()=>{}).then(action);queue.current=p;return p;},[]);
    const refresh=useCallback(async()=>{if(repo.current){setSaved(await repo.current.list());setDrafts(await repo.current.drafts());const warnings=repo.current.warnings();if(warnings.length)setWarning(warnings[0]);}},[]);
    const persist=useCallback(async(snapshot:InvestigationV4,sequence:number)=>{
        if(!repo.current)throw new Error('Local storage is unavailable; keep this tab open or export your draft.');
        setStatus('Saving draft on this browser…');
        const d=await repo.current.writeDraft(snapshot,draftVersions.current.get(snapshot.id)||0);draftVersions.current.set(snapshot.id,d.draft_revision);
        if(sequence===change.current&&snapshot.id===current.current.id){ack.current=sequence;setStatus('Draft saved on this browser');setError('');}
        await refresh();
    },[refresh]);
    const flush=useCallback(async()=>{
        const snapshot=structuredClone(current.current),sequence=change.current;
        if(ack.current===sequence)return queue.current;
        return enqueue(async()=>{if(ack.current!==sequence)await persist(snapshot,sequence);});
    },[enqueue,persist]);
    const fail=useCallback((e:unknown)=>{setError(e instanceof Error?e.message:'Local storage failed. Your draft remains in this tab.');setStatus('Draft is not saved');},[]);
    useEffect(()=>{
        let cancelled=false;let opened:ResearchRepository|null=null;
        (async()=>{
            let fallback:InvestigationV4|undefined;
            const now=new Date().toISOString(),end=new Date(Date.now()-86400000).toISOString().slice(0,10);
            fallback=newInvestigation(crypto.randomUUID(),now,timeframeStart('5Y',end),end);
            try{
                opened=await openResearchRepository();if(cancelled){opened.close();return;}repo.current=opened;
                let legacy:string|null=null;try{legacy=localStorage.getItem('ml-research');}catch{setWarning('Older browser research could not be read; it was not overwritten.');}
                const issues=await opened.importLegacy(legacy);if(issues.length)setWarning(issues[0]);
                const id=await opened.active();if(id){try{const state=await opened.read(id);if(state.draft){fallback=state.draft.record;draftVersions.current.set(id,state.draft.draft_revision);ack.current=0;setRestored(true);}else if(state.saved){fallback=state.saved;ack.current=0;setRestored(true);}}catch{setWarning('The active record could not be opened. Original stored data was retained.');}}
                if(cancelled)return;
                current.current=fallback;setState(fallback);await refresh();setStatus(ack.current===0?'Research restored from this browser':'New local draft');
            }catch(e){if(cancelled)return;current.current=fallback;setState(fallback);fail(e);}
            if(!cancelled)setReady(true);
        })();
        return()=>{cancelled=true;opened?.close();repo.current=null;};
    },[fail,refresh]);
    useEffect(()=>{
        if(!ready||!repo.current||ack.current===change.current)return;
        const snapshot=structuredClone(record),sequence=change.current;
        const timer=setTimeout(()=>{enqueue(async()=>{if(sequence===change.current&&ack.current!==sequence)await persist(snapshot,sequence);}).catch(fail);},350);
        return()=>clearTimeout(timer);
    },[record,ready,enqueue,persist,fail]);
    useEffect(()=>{if(!ready)return;const warn=(event:BeforeUnloadEvent)=>{if(ack.current!==change.current){event.preventDefault();event.returnValue='';}};window.addEventListener('beforeunload',warn);return()=>window.removeEventListener('beforeunload',warn);},[ready]);
    const open=useCallback(async(value:Investigation)=>{
        await flush();
        let next=migrateInvestigation(value,new Date().toISOString(),value.version!==4);
        if(!repo.current)throw new Error('Local storage is unavailable. Export the current draft before starting another.');
        const existing=await repo.current.read(next.id);next=existing.draft?.record||existing.saved||next;
        draftVersions.current.set(next.id,existing.draft?.draft_revision||0);
        current.current=next;const sequence=++change.current;ack.current=-1;setState(next);await enqueue(()=>persist(next,sequence));
    },[flush,enqueue,persist]);
    const save=useCallback(async(receipt:CalculationReceipt|null)=>{
        const snapshot={...structuredClone(current.current),saved_calculation:receipt},sequence=change.current;
        await flush();if(!repo.current)throw new Error('Local storage is unavailable');
        return enqueue(async()=>{
            if(sequence!==change.current||snapshot.id!==current.current.id)throw new Error('New edits arrived while saving. Your draft is retained; save again when ready.');
            const next=await repo.current!.save(snapshot,draftVersions.current.get(snapshot.id)||0);
            draftVersions.current.set(next.id,0);
            if(current.current.id===next.id){current.current=sequence===change.current?next:{...current.current,revision:next.revision,original_calculation:next.original_calculation,saved_calculation:next.saved_calculation};setState(current.current);ack.current=sequence;}
            setStatus(sequence===change.current?'Investigation saved on this browser':'Saved version; newer draft changes are pending');setError('');await refresh();return next;
        });
    },[flush,enqueue,refresh]);
    function exportDraft(){const url=URL.createObjectURL(new Blob([JSON.stringify(current.current,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download='macrolens-investigation.json';a.click();URL.revokeObjectURL(url);}
    return {record,setRecord,ready,restored,saved,drafts,status,error:[warning,error].filter(Boolean).join(' '),flush,open,save,fail,exportDraft};
}
