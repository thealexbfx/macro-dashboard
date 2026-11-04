import type {Comparison, EvidenceReference, InvestigationV4} from './contracts';
import {migrateInvestigation,receiptMatches} from './investigation.ts';
export type EvidenceKind='supporting_evidence'|'contradictory_evidence';

/** Capture only a successfully calculated, matching comparison. Never save its raw arrays. */
export function attachCalculation(record:InvestigationV4,comparison:Comparison|null,kind:EvidenceKind,id:string,at:string):InvestigationV4 {
    const receipt=comparison?.provenance;
    if(!receipt||!receiptMatches(record,receipt))throw new Error('Calculate the current settings successfully before attaching evidence.');
    if(comparison.datasets.map(d=>d.id).join()!==record.datasets.join())throw new Error('Calculation dataset references do not match.');
    if([...record.supporting_evidence,...record.contradictory_evidence].some(e=>e.capture?.receipt.result_fingerprint===receipt.result_fingerprint&&e.capture.receipt.parameter_fingerprint===receipt.parameter_fingerprint))throw new Error('This calculation is already attached. You can change its classification or annotation below.');
    const evidence:EvidenceReference={id,dataset_ids:[...record.datasets],start:record.start,end:record.end,calculation_fingerprint:receipt.result_fingerprint,note:'',capture:{attached_at:at,dataset_labels:Object.fromEntries(comparison.datasets.map(d=>[d.id,d.name])),timeframe:record.timeframe,workspace:structuredClone(record.workspace),receipt:structuredClone(receipt)}};
    return migrateInvestigation({...record,[kind]:[...record[kind],evidence]},at);
}

export function changeEvidence(record:InvestigationV4,id:string,annotation:string,kind:EvidenceKind):InvestigationV4 {
    const item=[...record.supporting_evidence,...record.contradictory_evidence].find(e=>e.id===id);
    if(!item)throw new Error('Evidence reference not found');
    return {...record,supporting_evidence:record.supporting_evidence.filter(e=>e.id!==id),contradictory_evidence:record.contradictory_evidence.filter(e=>e.id!==id),[kind]:record[kind].some(e=>e.id===id)?record[kind].map(e=>e.id===id?{...e,note:annotation}:e):[...record[kind],{...item,note:annotation}]};
}

/** Recalculate with captured settings, retaining the current question, writing and evidence. */
export function applyEvidenceSettings(record:InvestigationV4,id:string):InvestigationV4 {
    const e=[...record.supporting_evidence,...record.contradictory_evidence].find(e=>e.id===id);
    if(!e?.capture)throw new Error('This older reference has no captured settings');
    const p=e.capture.receipt.parameters;
    return migrateInvestigation({...record,datasets:e.dataset_ids,start:e.start,end:e.end,transformations:p.transformations,horizons:p.horizons,observation_basis:p.observation_basis,alignment:p.alignment,rolling_window:p.rolling_window,window_explicit:true,workspace:e.capture.workspace,timeframe:e.capture.timeframe},new Date().toISOString());
}
