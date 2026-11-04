import type {InvestigationV4} from './contracts';
import type {Draft} from './research-repository';
export interface LibraryItem{record:InvestigationV4;hasSaved:boolean;hasDraft:boolean}
/** A view over the existing repository, not a second saved-research model. */
export function researchLibrary(saved:InvestigationV4[],drafts:Draft[]):LibraryItem[]{
 const byId=new Map(saved.map(record=>[record.id,{record,hasSaved:true,hasDraft:false}]));
 for(const draft of drafts)byId.set(draft.record.id,{record:draft.record,hasSaved:byId.get(draft.record.id)?.hasSaved||false,hasDraft:true});
 return [...byId.values()].sort((a,b)=>(b.record.updated_at?Date.parse(b.record.updated_at):0)-(a.record.updated_at?Date.parse(a.record.updated_at):0));
}

export function hasResearchContent(r:InvestigationV4,hasSaved=false):boolean{
 return Boolean(hasSaved||r.revision>0||[r.research_question,r.note,r.conclusion,r.working_hypothesis,r.alternative_explanations,r.limitations_and_uncertainty].some(s=>s.trim())||r.supporting_evidence.length||r.contradictory_evidence.length||r.title!=='Untitled investigation'||r.timeframe!=='5Y'||r.datasets.join()!=='cpi,unemployment'||Object.values(r.transformations).some(t=>t!=='level')||r.window_explicit||r.workspace.mode!=='separate'||r.workspace.chart_type!=='line'||r.workspace.layout!=='stacked'||r.workspace.axes!=='shared'||r.workspace.recession||r.workspace.hidden.length||r.workspace.lead_lag.periods);
}
