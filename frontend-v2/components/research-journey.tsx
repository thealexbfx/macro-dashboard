'use client';
import {useState} from 'react';
import type {Comparison,InvestigationV4} from '../lib/contracts';
import {transformLabels} from '../lib/contracts';
import {receiptMatches} from '../lib/investigation';
import {attachCalculation,changeEvidence,applyEvidenceSettings,type EvidenceKind} from '../lib/research-evidence';
import {Button} from './ui/button';

type EditorProps={record:InvestigationV4;onChange:(r:InvestigationV4)=>void};
export function ResearchQuestion({record:r,onChange}:EditorProps){
    return <section className="card journey-question" aria-labelledby="question-heading">
        <span className="eyebrow">YOUR INVESTIGATION</span><h2 id="question-heading">Research question</h2>
        <label htmlFor="investigation-question">What do you want to understand?</label>
        <textarea id="investigation-question" aria-label="Investigation question" maxLength={20000} value={r.research_question} onChange={e=>onChange({...r,research_question:e.target.value})} placeholder="Start with a question. You can change it as you investigate."/>
        <label htmlFor="working-hypothesis">Working hypothesis</label>
        <textarea id="working-hypothesis" maxLength={20000} value={r.working_hypothesis} onChange={e=>onChange({...r,working_hypothesis:e.target.value})} placeholder="What might explain this? It is fine to leave this provisional."/>
        <p className="quiet">Your question, hypothesis and conclusion are your interpretation. No field is mandatory. Original Discovery evidence remains below when available.</p>
        <div className="journey-links"><a href="#research-evidence">Review evidence</a><a href="#research-challenge">Challenge the explanation</a><a href="#research-conclusion">Write a conclusion</a></div>
    </section>;
}

export function CalculationHistory({record:r,comparison}:{record:InvestigationV4;comparison:Comparison|null}){
    return <details className="card journey-history"><summary>Saved evidence and current calculation</summary>
        {([['Original calculation',r.original_calculation],['Last saved calculation',r.saved_calculation],['Current recalculation',comparison?.provenance]] as const).map(([label,receipt])=><section key={label}><h3>{label}</h3>{receipt?<><p>{receipt.calculated_at} · {receipt.method_version} · Result {receipt.result_fingerprint.slice(0,12)}</p><p>{String(receipt.parameters.start)} to {String(receipt.parameters.end)}</p><details><summary>Calculation receipt</summary><pre className="provenance-record">{JSON.stringify(receipt,null,2)}</pre></details></>:<p>No calculation receipt was captured. Historical success or evidence is not inferred.</p>}</section>)}
        <p className="quiet">Current charts use latest revised observations. Receipts preserve compact results and input fingerprints, not frozen observations; exact historical replay is unavailable.</p>
    </details>;
}

export function ResearchReview({record:r,onChange,comparison,canAttach,saving,onSave,onSaveExit}:{comparison:Comparison|null;canAttach:boolean;saving:boolean;onSave:()=>void;onSaveExit:()=>void}&EditorProps){
    const [feedback,setFeedback]=useState('');
    const report=(error:unknown)=>setFeedback(error instanceof Error?error.message:'Evidence action could not be completed.');
    function attach(kind:EvidenceKind){setFeedback('');try{onChange(attachCalculation(r,comparison,kind,crypto.randomUUID(),new Date().toISOString()));}catch(e){report(e);}}
    const items=[...r.supporting_evidence.map(e=>({item:e,kind:'supporting_evidence' as EvidenceKind})),...r.contradictory_evidence.map(e=>({item:e,kind:'contradictory_evidence' as EvidenceKind}))];
    return <div className="journey-review">
        <section className="card journey-section" id="research-evidence" aria-labelledby="evidence-heading"><h2 id="evidence-heading">Evidence</h2>
            <p>Attach the calculation currently shown in the charts. Supporting or contradictory is your assessment, not a statistical verdict.</p>
            <div className="journey-actions"><Button disabled={!canAttach} onClick={()=>attach('supporting_evidence')}>Attach supporting calculation</Button><Button variant="outline" disabled={!canAttach} onClick={()=>attach('contradictory_evidence')}>Attach contradictory calculation</Button></div>
            {feedback&&<p role="alert">{feedback}</p>}
            {!canAttach&&<p className="quiet">Evidence attachment needs a successful calculation for the current settings. You can still write and save your research.</p>}
            {!items.length&&<p className="quiet">No calculations attached yet. Compare datasets above, then attach the evidence you want to discuss.</p>}
            <div className="journey-evidence-list">{items.map(({item:e,kind},index)=>{const capture=e.capture,receipt=capture?.receipt;return <article key={e.id} className="journey-evidence" aria-label={`Evidence ${index+1}`}>
                <div className="journey-evidence-heading"><h3>{kind==='supporting_evidence'?'Supporting':'Contradictory'} evidence</h3><Button variant="outline" onClick={()=>onChange({...r,supporting_evidence:r.supporting_evidence.filter(x=>x.id!==e.id),contradictory_evidence:r.contradictory_evidence.filter(x=>x.id!==e.id)})}>Remove evidence {index+1}</Button></div>
                <p>{e.dataset_ids.map(id=>capture?.dataset_labels[id]||id).join(' / ')}</p><p>{e.start||'Period not recorded'} to {e.end||'Period not recorded'}{capture?` · ${capture.timeframe} · ${capture.workspace.mode} / ${capture.workspace.chart_type}`:''}</p>
                {capture&&receipt?<><p className="quiet">Attached {new Date(capture.attached_at).toLocaleString()} · Calculated {new Date(receipt.calculated_at).toLocaleString()}</p>
                    <p>Saved calculation · Preserved numerical summary</p>
                    <p>{Object.entries(receipt.parameters.transformations||{}).map(([id,t])=>`${capture.dataset_labels[id]||id}: ${transformLabels[t as keyof typeof transformLabels]||String(t)}`).join(' / ')}</p>
                    {receipt.statistics.map((s,i)=><p key={i}>Saved Pearson correlation: {typeof s.correlation==='number'?s.correlation.toFixed(3):'unavailable'} · {typeof s.observations==='number'?s.observations:'Unknown'} paired observations. Descriptive association does not establish causation.</p>)}
                    {receipt.datasets.map(d=><p className="quiet" key={d.dataset_id}>{capture.dataset_labels[d.dataset_id]||d.dataset_id} · Source reference: {typeof d.source_identifier==='string'?d.source_identifier:d.dataset_id}</p>)}
                    <p className="quiet">{comparison?.provenance&&receiptMatches(r,comparison.provenance)?comparison.provenance.parameter_fingerprint===receipt.parameter_fingerprint?(comparison.provenance.result_fingerprint===receipt.result_fingerprint?'Current calculation has the same result fingerprint.':'Current calculation differs from this attachment. The saved evidence is preserved.'):'Current charts use different calculation settings. This attachment retains its own settings.':'No matching current calculation is available. Saved evidence remains a historical reference.'}</p>
                    <Button variant="outline" onClick={()=>{try{onChange(applyEvidenceSettings(r,e.id));document.querySelector('.research-workspace')?.scrollIntoView({behavior:'smooth'});}catch(error){report(error);}}}>Use saved settings with latest data</Button><details><summary>Saved settings, sources and limitations</summary>{receipt.limitations.map((v,i)=><p key={i}>{v}</p>)}<p>Original numerical summary only. Exact historical replay is unavailable.</p><pre className="provenance-record">{JSON.stringify(capture,null,2)}</pre></details>
                </>:<p className="quiet">Older reference: no numerical receipt was captured. It is not reconstructed from current data.</p>}
                <label>Evidence classification<select aria-label={`Classification for evidence ${index+1}`} value={kind} onChange={event=>onChange(changeEvidence(r,e.id,e.note,event.target.value as EvidenceKind))}><option value="supporting_evidence">Supporting</option><option value="contradictory_evidence">Contradictory</option></select></label>
                <label>Your annotation<textarea aria-label={`Annotation for evidence ${index+1}`} maxLength={20000} value={e.note} onChange={event=>onChange(changeEvidence(r,e.id,event.target.value,kind))} placeholder="Why does this matter to your question? This is your interpretation."/></label>
            </article>;})}</div>
        </section>
        <section className="card journey-section" id="research-challenge" aria-labelledby="challenge-heading"><h2 id="challenge-heading">Challenge your explanation</h2><p>What would make you reconsider? Consider a different period or transformation, contradictory evidence, missing observations, revisions and sample size. These prompts do not validate or reject your hypothesis.</p>
            <label htmlFor="alternatives">Alternative explanations</label><textarea id="alternatives" maxLength={20000} value={r.alternative_explanations} onChange={e=>onChange({...r,alternative_explanations:e.target.value})} placeholder="What else could produce this pattern?"/>
            <label htmlFor="uncertainty">Limitations and uncertainty</label><textarea id="uncertainty" maxLength={20000} value={r.limitations_and_uncertainty} onChange={e=>onChange({...r,limitations_and_uncertainty:e.target.value})} placeholder="What can this evidence not establish?"/>
        </section>
        <section className="card journey-section" id="research-conclusion" aria-labelledby="conclusion-heading"><h2 id="conclusion-heading">My conclusion</h2><p>Your interpretation can remain provisional. Saving does not mark a hypothesis as proven.</p><label htmlFor="conclusion">Provisional conclusion</label><textarea id="conclusion" maxLength={20000} value={r.conclusion} onChange={e=>onChange({...r,conclusion:e.target.value})} placeholder="What do you think now, and what would change your mind?"/>
            <div className="journey-actions"><Button disabled={saving} onClick={onSave}>Save research</Button><Button variant="outline" disabled={saving} onClick={onSaveExit}>Save and return to My Research</Button></div><p className="quiet">Saved on this browser only. You can reopen, reconsider and update the same investigation.</p>
        </section>
    </div>;
}
