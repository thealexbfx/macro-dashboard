import type {CalculationReceipt, EvidenceReference, Investigation, InvestigationV4, Transformation} from './contracts';
import {defaultWorkspace, restoreWorkspace} from './workspace.ts';

export class InvalidInvestigation extends Error {}
export const object = (v:unknown):v is Record<string,unknown> => !!v&&typeof v==='object'&&!Array.isArray(v);
const modes = ['level','percent','yoy','mom','pp','indexed','standardized','jobs'];
const text = (v:unknown, max=20000):string => {if(typeof v!=='string'||v.length>max)throw new InvalidInvestigation('Invalid text field');return v;};
const ids = (v:unknown):string[] => {if(!Array.isArray(v)||v.length>4||v.some(x=>typeof x!=='string'||!x.length||x.length>100)||new Set(v).size!==v.length)throw new InvalidInvestigation('Invalid dataset references');return v;};
const day = (v:unknown):string => {if(typeof v!=='string'||!/^\d{4}-\d{2}-\d{2}$/.test(v)||!Number.isFinite(Date.parse(v))||new Date(v).toISOString().slice(0,10)!==v)throw new InvalidInvestigation('Invalid reference date');return v;};
const stamp = (v:unknown):string|null => {if(v===null||v===undefined)return null;if(typeof v!=='string'||v.length>50||!/(Z|[+-]\d\d:\d\d)$/.test(v)||!Number.isFinite(Date.parse(v)))throw new InvalidInvestigation('Invalid timestamp');return v;};
const integer = (v:unknown,min:number,max:number):number => {if(!Number.isInteger(v)||Number(v)<min||Number(v)>max)throw new InvalidInvestigation('Invalid integer');return Number(v);};
function bounded(value:unknown,max=262144){const encoded=JSON.stringify(value);if(!encoded||encoded.length>max)throw new InvalidInvestigation('Record exceeds local research size limit');return JSON.parse(encoded);}

function origin(value:unknown,historical=false){
    if(value===undefined)return undefined;
    const copy=bounded(value);
    if(!object(copy))throw new InvalidInvestigation('Invalid original evidence');
    const finding=historical?(object(copy.snapshot)?copy.snapshot.finding:undefined):copy.finding;
    if(!object(finding)||!object(finding.evidence)||!object(finding.evidence.baseline)||!['unusual','correlation','divergence'].includes(String(finding.type)))throw new InvalidInvestigation('Invalid original finding');
    for(const period of [finding.evidence.baseline,finding.evidence.recent].filter(Boolean)){if(!object(period))throw new InvalidInvestigation('Invalid evidence period');for(const key of ['observations','expected','missing','completeness'])if(period[key]!==undefined&&typeof period[key]!=='number')throw new InvalidInvestigation('Invalid period count');}
    text(finding.headline);text(finding.label);day(finding.observation_date);ids(finding.datasets);
    if(!object(finding.configuration))throw new InvalidInvestigation('Invalid original configuration');day(finding.configuration.start);day(finding.configuration.end);
    if(!historical){if(!stamp(copy.generated_at))throw new InvalidInvestigation('Missing discovery timestamp');text(copy.snapshot_fingerprint,200);}day(finding.evidence.baseline.start);day(finding.evidence.baseline.end);
    for(const k of ['movement','display_movement','absolute_movement_percentile','standardized_magnitude','recent_correlation','baseline_correlation','divergence_z','correlation_difference'])if(finding.evidence[k]!==undefined&&finding.evidence[k]!==null&&typeof finding.evidence[k]!=='number')throw new InvalidInvestigation('Invalid numerical evidence');
    for(const k of ['units','display_units'])if(finding.evidence[k]!==undefined)text(finding.evidence[k],200);
    if(finding.evidence.recent){if(!object(finding.evidence.recent))throw new InvalidInvestigation('Invalid evidence period');day(finding.evidence.recent.start);day(finding.evidence.recent.end);}
    if(historical){
        text(copy.label);text(copy.notes);if(!object(copy.snapshot)||!object(copy.similarity))throw new InvalidInvestigation('Invalid historical evidence');text(copy.similarity.reason);if(!object(copy.snapshot.pattern)||copy.current_pattern!==null&&!object(copy.current_pattern))throw new InvalidInvestigation('Missing historical pattern');
        for(const p of [copy.snapshot.pattern,copy.current_pattern].filter(Boolean)){
            if(!object(p)||!Array.isArray(p.observations)||p.observations.length>5000)throw new InvalidInvestigation('Invalid historical preview');text(p.units,200);
            for(const o of p.observations){if(!object(o))throw new InvalidInvestigation('Invalid historical point');day(o.date);if(o.value!==null&&typeof o.value!=='number')throw new InvalidInvestigation('Invalid historical values');}
        }
    }
    return copy;
}
export function validateReceipt(value:unknown):CalculationReceipt|null {
    if(value===null||value===undefined)return null;
    const r=bounded(value,65536);
    if(!object(r)||r.schema_version!==1||!object(r.parameters)||!Array.isArray(r.datasets)||r.datasets.length>4||!Array.isArray(r.statistics)||r.statistics.length>6||!Array.isArray(r.effective_ranges)||r.effective_ranges.length>4||!Array.isArray(r.limitations)||!object(r.exact_replay)||r.exact_replay.available!==false)throw new InvalidInvestigation('Invalid calculation receipt');
    const inspect=(v:unknown)=>{if(Array.isArray(v)){for(const x of v)inspect(x);}else if(object(v))for(const [k,x] of Object.entries(v)){if(['observations','raw_observations','rolling','scatter'].includes(k)&&x!==null&&typeof x==='object')throw new InvalidInvestigation('Observation arrays are not saved in receipts');inspect(x);}};
    inspect(r);text(r.method_version,100);if(!stamp(r.calculated_at))throw new InvalidInvestigation('Receipt timestamp missing');text(r.exact_replay.reason);
    for(const k of ['parameter_fingerprint','result_fingerprint'])if(typeof r[k]!=='string'||!(/^[a-f0-9]{64}$/).test(r[k]))throw new InvalidInvestigation('Invalid calculation fingerprint');
    for(const d of r.datasets){if(!object(d))throw new InvalidInvestigation('Invalid dataset receipt');text(d.dataset_id,100);text(d.definition_identifier,100);text(d.input_fingerprint,100);text(d.units,256);text(d.frequency,30);}
    for(const range of r.effective_ranges){if(!object(range))throw new InvalidInvestigation('Invalid effective range');text(range.dataset_id,100);text(range.units,256);text(range.transformation,40);if(range.start)day(String(range.start).slice(0,10));if(range.end)day(String(range.end).slice(0,10));}
    r.limitations.forEach((v:unknown)=>text(v));return r as unknown as CalculationReceipt;
}
function references(value:unknown):EvidenceReference[]{
    if(value===undefined)return [];if(!Array.isArray(value)||value.length>50)throw new InvalidInvestigation('Invalid evidence references');
    return value.map(v=>{
        if(!object(v))throw new InvalidInvestigation('Invalid evidence reference');
        const reference:EvidenceReference={id:text(v.id,100),dataset_ids:ids(v.dataset_ids),start:v.start===null?null:day(v.start),end:v.end===null?null:day(v.end),calculation_fingerprint:v.calculation_fingerprint===null?null:text(v.calculation_fingerprint,100),note:text(v.note)};
        if(v.capture!==undefined){
            if(!object(v.capture)||!object(v.capture.dataset_labels)||!object(v.capture.workspace))throw new InvalidInvestigation('Invalid evidence capture');
            const receipt=validateReceipt(v.capture.receipt),attached=stamp(v.capture.attached_at);
            if(!receipt||!attached||receipt.result_fingerprint!==reference.calculation_fingerprint)throw new InvalidInvestigation('Evidence receipt mismatch');
            const config=migrateInvestigation({id:'capture',title:'Evidence',version:3,note:'',datasets:reference.dataset_ids,...receipt.parameters,workspace:v.capture.workspace},attached);
            if(!receiptMatches(config,receipt)||config.datasets.join()!==reference.dataset_ids.join()||config.start!==reference.start||config.end!==reference.end||receipt.datasets.map(d=>d.dataset_id).join()!==reference.dataset_ids.join())throw new InvalidInvestigation('Evidence settings mismatch');
            const labels=v.capture.dataset_labels;
            reference.capture={attached_at:attached,dataset_labels:Object.fromEntries(reference.dataset_ids.map(id=>[id,text(labels[id],500)])),timeframe:text(v.capture.timeframe,100),workspace:config.workspace,receipt};
        }
        return reference;
    });
}
/** Validates old saves without validating IDs against the current public catalog.
 * Unknown/revoked IDs remain references, never authorization or invented evidence. */
export function migrateInvestigation(value:unknown,now:string,newRecord=false):InvestigationV4 {
    const v=bounded(value);if(!object(v)||![2,3,4].includes(Number(v.version)))throw new InvalidInvestigation('Unsupported research version; original retained');
    const selected=ids(v.datasets),start=day(v.start),end=day(v.end);if(start>end)throw new InvalidInvestigation('Reversed period');
    const transformations:Record<string,Transformation>={}, horizons:Record<string,number>={};
    if(v.transformations!==undefined&&!object(v.transformations))throw new InvalidInvestigation('Invalid transformations');
    for(const [id,mode] of Object.entries(v.transformations||{})){if(!modes.includes(String(mode)))throw new InvalidInvestigation('Invalid transformation');if(selected.includes(id))transformations[id]=mode as Transformation;}
    if(v.horizons!==undefined&&!object(v.horizons))throw new InvalidInvestigation('Invalid horizons');
    for(const [id,h] of Object.entries(v.horizons||{}))if(selected.includes(id))horizons[id]=integer(h,1,252);
    if(v.workspace!==undefined){if(!object(v.workspace))throw new InvalidInvestigation('Invalid chart configuration');if(v.workspace.hidden!==undefined&&!Array.isArray(v.workspace.hidden))throw new InvalidInvestigation('Invalid hidden series');if(v.workspace.axis_assignment!==undefined&&!object(v.workspace.axis_assignment))throw new InvalidInvestigation('Invalid axes');if(v.workspace.lead_lag!==undefined&&!object(v.workspace.lead_lag))throw new InvalidInvestigation('Invalid shift');}
    const out:InvestigationV4={
        id:text(v.id,100),title:text(v.title,500),datasets:selected,note:text(v.note??''),collection:text(v.collection??'Macro outlook',100),
        version:4,research_question:text(v.research_question??''),working_hypothesis:text(v.working_hypothesis??''),
        supporting_evidence:references(v.supporting_evidence),contradictory_evidence:references(v.contradictory_evidence),
        alternative_explanations:text(v.alternative_explanations??''),limitations_and_uncertainty:text(v.limitations_and_uncertainty??''),conclusion:text(v.conclusion??''),
        created_at:v.version===4?stamp(v.created_at):newRecord?now:null,
        updated_at:v.version===4?stamp(v.updated_at):newRecord?now:null,
        migrated_at:v.version===4?stamp(v.migrated_at):newRecord?null:now,
        revision:v.version===4?integer(v.revision,0,Number.MAX_SAFE_INTEGER):0,
        start,end,timeframe:text(v.timeframe??'Saved',100),transformations,horizons,
        observation_basis:v.observation_basis==='trading_sessions'?'trading_sessions':'native',
        alignment:v.alignment==='period_end'?'period_end':'native',rolling_window:integer(v.rolling_window??12,3,252),window_explicit:v.window_explicit===undefined?v.rolling_window!==undefined:!!v.window_explicit,
        workspace:restoreWorkspace({...v,datasets:selected} as unknown as Investigation),
        original_calculation:validateReceipt(v.original_calculation),saved_calculation:validateReceipt(v.saved_calculation),
    };
    const evidenceIds=[...out.supporting_evidence,...out.contradictory_evidence].map(e=>e.id);
    if(new Set(evidenceIds).size!==evidenceIds.length)throw new InvalidInvestigation('Duplicate evidence IDs');
    out.workspace.recession=!!out.workspace.recession;
    out.workspace.axis_assignment=Object.fromEntries(Object.entries(out.workspace.axis_assignment).filter(([,v])=>v==='left'||v==='right'));
    if(!['months','quarters','weeks','calendar_days'].includes(out.workspace.lead_lag.unit))out.workspace.lead_lag.unit='months';
    if(!out.id)throw new InvalidInvestigation('Missing investigation ID');
    if(v.discovery!==undefined)out.discovery=origin(v.discovery) as unknown as InvestigationV4['discovery'];
    if(v.historical_context!==undefined)out.historical_context=origin(v.historical_context,true) as unknown as InvestigationV4['historical_context'];
    return out;
}
export function newInvestigation(id:string,now:string,start:string,end:string):InvestigationV4 {
    return migrateInvestigation({id,title:'Untitled investigation',datasets:['cpi','unemployment'],note:'',version:3,start,end,timeframe:'5Y',workspace:defaultWorkspace()},now,true);
}
export function preserveOriginal(incoming:InvestigationV4,previous?:InvestigationV4):InvestigationV4 {
    const next=structuredClone(incoming);
    if(!previous)return next;
    const originals=new Map([...previous.supporting_evidence,...previous.contradictory_evidence].map(e=>[e.id,e]));
    for(const kind of ['supporting_evidence','contradictory_evidence'] as const)next[kind]=next[kind].map(e=>originals.has(e.id)?{...structuredClone(originals.get(e.id)!),note:e.note}:e);
    return {...next,created_at:previous.created_at,migrated_at:previous.migrated_at,discovery:structuredClone(previous.discovery),historical_context:structuredClone(previous.historical_context),original_calculation:structuredClone(previous.original_calculation)};
}
export function comparisonParameters(i:InvestigationV4,rollingWindow=i.rolling_window){
    return {datasets:i.datasets,transformations:Object.fromEntries(i.datasets.map(id=>[id,i.transformations[id]||'level'])),horizons:Object.fromEntries(i.datasets.map(id=>[id,['percent','mom','pp','jobs'].includes(i.transformations[id]||'level')?(i.horizons[id]||1):1])),observation_basis:i.observation_basis,start:i.start,end:i.end,alignment:i.datasets.length>1?i.alignment:'native',rolling_window:rollingWindow,lead_lag:i.datasets.length>1&&i.datasets.includes(i.workspace.lead_lag.dataset_id)&&i.workspace.lead_lag.periods?i.workspace.lead_lag:null};
}
const canonical=(v:unknown):string=>JSON.stringify(v,(_,x)=>object(x)?Object.fromEntries(Object.keys(x).sort().map(k=>[k,x[k]])):x);
export function receiptMatches(i:InvestigationV4,r:CalculationReceipt,window=i.rolling_window){return canonical(comparisonParameters(i,window))===canonical(r.parameters);}
