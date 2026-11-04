'use client';
import { useCallback, useEffect, useState, useMemo } from 'react';
import { CatalogExplorer, type CatalogPage } from '../components/catalog-explorer';
import {AppShell,pageLabel,viewQuery,viewPage} from '../components/app-shell';
import {ResearchLibrary} from '../components/research-library';
import {ResearchDataPicker} from '../components/research-data-picker';
import {HomeDashboard} from '../components/home-dashboard';
import { defaultRollingWindow, timeframeStart, type Timeframe } from '../lib/presentation';
import { Button } from '../components/ui/button';
import { request, type Dataset, type Comparison, type Investigation, type Transformation, type InvestigationV4 } from '../lib/contracts';
import { DiscoveryRadar, DiscoveryEvidence, HistoricalComparison } from '../components/discovery-radar';
import { InvestigationWorkspace } from '../components/investigation-workspace';
import { commonFrequency, defaultWorkspace } from '../lib/workspace';
import {useResearchFoundation} from '../lib/use-research-foundation';
import {ResearchQuestion,ResearchReview,CalculationHistory} from '../components/research-journey';
import {newInvestigation,receiptMatches} from '../lib/investigation';
const storageCopy:Record<string,string>={'Draft saved on this browser':'Changes saved in this browser','Investigation saved on this browser':'Saved in this browser','Research restored from this browser':'Resumed from this browser','New local draft':'New draft · this browser','Draft changes not yet saved':'Unsaved changes','Saving draft on this browser…':'Saving…','Draft is not saved':'Not saved','Saved version; newer draft changes are pending':'Saved; newer edits pending'};
const yesterday = () => new Date(Date.now() - 86400000).toISOString().slice(0, 10);
export default function Page() {
    const research=useResearchFoundation(), {record, setRecord, saved,flush:flushResearch,fail:failResearch}=research;
    function field<K extends keyof InvestigationV4>(key:K){return (v:InvestigationV4[K]|((p:InvestigationV4[K])=>InvestigationV4[K]))=>setRecord(p=>({...p,[key]:typeof v==='function'?(v as (p:InvestigationV4[K])=>InvestigationV4[K])(p[key]):v}));}
    const selected=record.datasets,setSelected=field('datasets'),range=record.timeframe,setRange=field('timeframe'),start=record.start,setStart=field('start'),end=record.end,setEnd=field('end'),transformations=record.transformations,setTransformations=field('transformations'),alignment=record.alignment,setAlignment=field('alignment'),rollingWindow=record.rolling_window,setRollingWindow=field('rolling_window'),note=record.note,setNote=field('note'),workspace=record.workspace,setWorkspace=field('workspace'),horizons=record.horizons,setHorizons=field('horizons'),observationBasis=record.observation_basis,setObservationBasis=field('observation_basis'),discoverySnapshot=record.discovery,historicalContext=record.historical_context;
    const windowExplicit=record.window_explicit,setWindowExplicit=field('window_explicit');
    const [tab,setTab]=useState('Today'),[viewReady,setViewReady]=useState(false),[homeData,setHomeData]=useState<Dataset[]>([]),[homeIssue,setHomeIssue]=useState(false),[datasets,setDatasets]=useState<Dataset[]>([]),[loading,setLoading]=useState(true),[error,setError]=useState(''),[comparison,setComparison]=useState<Comparison|null>(null),[comparing,setComparing]=useState(false),[compareError,setCompareError]=useState(''),[favorites,setFavorites]=useState<string[]>([]),[notice,setNotice]=useState(''),[saving,setSaving]=useState(false);
    const activeHorizons=useMemo(()=>Object.fromEntries(selected.map(id=>[id,['percent','mom','pp','jobs'].includes(transformations[id]||'level')?(horizons[id]||1):1])),[selected,transformations,horizons]);

    const effectiveWindow=windowExplicit?rollingWindow:defaultRollingWindow(commonFrequency(datasets.filter(d=>selected.includes(d.id))));
    const mergeMetadata = useCallback((rows:Dataset[]) => setDatasets(current=>{const map=new Map(current.map(d=>[d.id,d]));for(const d of rows)map.set(d.id,d);return [...map.values()];}),[]);
    const [unavailable,setUnavailable]=useState<string[]>([]);
    const load = useCallback(async () => {
        setLoading(true);
        setError('');
        try {
            const page=await request<CatalogPage>('catalog?limit=100');
            mergeMetadata(page.items);
            const today=['sp500','us10y','gold','cpi_nsa','unemployment'];
            setHomeIssue(false);
            let index=0;await Promise.all(Array.from({length:3},async()=>{while(index<today.length){const id=today[index++];try{const result=await request<{dataset:Dataset}>(`observations/${id}?preview=true&limit=40`);mergeMetadata([result.dataset]);setHomeData(current=>[...current.filter(d=>d.id!==result.dataset.id),result.dataset]);}catch{setHomeIssue(true);}}}));
        }
        catch (e) {
            setError((e as Error).message);
        }
        finally {
            setLoading(false);
        }
    }, [mergeMetadata]);
    useEffect(() => {
        if(!research.ready)return;
        load();
        try {
            setFavorites(JSON.parse(localStorage.getItem('ml-favorites') || '[]'));
        }
        catch {
            setNotice('Browser storage could not be read. Existing records were not changed.');
        }
    }, [load,research.ready]);
    useEffect(()=>{if(!research.ready||tab!=='Investigate')return;const controller=new AbortController();Promise.all(selected.map(async id=>{try{const d=await request<Dataset>(`catalog/${encodeURIComponent(id)}`,undefined,controller.signal);mergeMetadata([d]);return null;}catch{return id;}})).then(ids=>{if(!controller.signal.aborted)setUnavailable(ids.filter((id):id is string=>id!==null));});return()=>controller.abort();},[research.ready,tab,selected,mergeMetadata]);
    const calculationRequest=useMemo(()=>({datasets:selected,transformations:Object.fromEntries(selected.map(id=>[id,transformations[id]||'level'])),horizons:activeHorizons,observation_basis:observationBasis,start,end,alignment:selected.length>1?alignment:'native',rolling_window:effectiveWindow,lead_lag:selected.length>1&&selected.includes(workspace.lead_lag.dataset_id)&&workspace.lead_lag.periods?workspace.lead_lag:null}),[selected,transformations,activeHorizons,observationBasis,start,end,alignment,effectiveWindow,workspace.lead_lag]);
    useEffect(() => {
        if (!research.ready || tab !== 'Investigate')
            return;
        const controller = new AbortController();
        setComparison(null);
        setCompareError('');
        if (!selected.length) {
            setComparing(false);
            return;
        }
        setComparing(true);
        request<Comparison>('compare', calculationRequest, controller.signal).then(setComparison).catch(e => {
            if (e.name !== 'AbortError')
                setCompareError(e.message);
        }).finally(() => {
            if (!controller.signal.aborted)
                setComparing(false);
        });
        return () => controller.abort();
    }, [research.ready, tab, selected, calculationRequest]);
    useEffect(()=>{if(!research.ready)return;setTab(viewPage(window.location.search)||(research.restored?'Investigate':'Today'));setViewReady(true);},[research.ready,research.restored]);
    useEffect(()=>{if(!research.ready)return;const restore=()=>{void flushResearch().catch(failResearch).then(()=>setTab(viewPage(window.location.search)||'Today'));};window.addEventListener('popstate',restore);return()=>window.removeEventListener('popstate',restore);},[research.ready,flushResearch,failResearch]);
    // Keep the effective calculation window in the durable record as metadata arrives.
    useEffect(()=>{if(research.ready&&!windowExplicit&&record.rolling_window!==effectiveWindow)setRecord(p=>({...p,rolling_window:effectiveWindow}));},[research.ready,windowExplicit,record.rolling_window,effectiveWindow,setRecord]);
    async function navigate(name:string){try{await research.flush();}catch(e){research.fail(e);}setTab(name);const next='?view='+viewQuery(name);if(window.location.search!==next)window.history.pushState(null,'',next);window.scrollTo({top:0,behavior:'auto'});}

    function toggle(id: string) {
        const next=selected.includes(id)?selected.filter(x=>x!==id):selected.length<4?[...selected,id]:selected;
        setSelected(next);setWorkspace(w=>({...w,mode:w.mode==='scatter'&&next.length!==2?'separate':w.mode,chart_type:w.chart_type==='scatter'&&next.length!==2?'line':w.chart_type,hidden:next.every(id=>w.hidden.includes(id))?[]:w.hidden.filter(id=>next.includes(id)),lead_lag:next.includes(w.lead_lag.dataset_id)?w.lead_lag:{...w.lead_lag,periods:0}}));
    }
    function favorite(id: string) {
        const next = favorites.includes(id) ? favorites.filter(x => x !== id) : [...favorites, id];
        try {
            localStorage.setItem('ml-favorites', JSON.stringify(next));
            setFavorites(next);
        }
        catch {
            setNotice('Unable to save favourites in this browser');
        }
    }
    const canAttach=!!comparison?.provenance&&!comparing&&!compareError&&!unavailable.length&&receiptMatches({...record,rolling_window:effectiveWindow},comparison.provenance,effectiveWindow);
    async function save(){
        if(saving)return false;setSaving(true);
        try{
            const title=record.research_question.trim().slice(0,500)||(record.title==='Untitled investigation'?record.datasets.map(id=>datasets.find(d=>d.id===id)?.name||id).join(' / ')||'Untitled investigation':record.title);
            setRecord(p=>({...p,title}));
            await research.save(canAttach?comparison!.provenance!:undefined);
            setNotice(canAttach?'Research saved.':'Research saved. Earlier evidence is unchanged; no new result was recorded.');
            return true;
        }catch(e){research.fail(e);return false;}finally{setSaving(false);}
    }
    async function saveExit(){if(await save())await navigate('My Research');}
    function preset(r: Timeframe) { const endpoint = yesterday(); setRange(r); setEnd(endpoint); setStart(r==='MAX'&&datasets.some(d=>selected.includes(d.id)&&d.native_storage)?(datasets.filter(d=>selected.includes(d.id)).map(d=>d.native_history_start||(d.native_storage?'0001-01-01':'1990-01-01')).sort()[0]||'0001-01-01'):timeframeStart(r, endpoint)); }
    function download() {
        if (!comparison)
            return;
        const escape = (v: unknown) => `"${String(v ?? '').replaceAll('"', '""')}"`;
        const rows = [['dataset_id', 'provider_id', 'source', 'date', 'kind', 'transformation', 'value', 'units', 'source_reference_date', 'shift_periods', 'shift_unit','horizon_observations','observation_basis']];
        for (const d of comparison.datasets) {
            for (const o of comparison.raw_observations[d.id])
                rows.push([d.id, d.provider_id, d.source, o.date, 'raw', 'level', String(o.value ?? ''), d.units, o.date, '0', '', '1','native']);
            const s = comparison.series.find(s => s.id === d.id)!;
            for (const o of s.observations)
                rows.push([d.id, d.provider_id, d.source, o.date, 'analytical', s.transformation, String(o.value ?? ''), s.units, s.source_dates?.[o.date]||'',String(s.shift_periods||0),s.shift_unit||'',String(s.horizon_observations||1),s.observation_basis||'native']);
        }
        const url = URL.createObjectURL(new Blob([rows.map(r => r.map(escape).join(',')).join('\r\n')], { type: 'text/csv;charset=utf-8' }));
        const a = document.createElement('a');
        a.href = url;
        a.download = 'macrolens-observations.csv';
        a.click();
        URL.revokeObjectURL(url);
    }
    async function begin(ids=['cpi','unemployment'],mode?:Transformation,questionText=''){
        const endpoint=yesterday(),r=newInvestigation(crypto.randomUUID(),new Date().toISOString(),timeframeStart('5Y',endpoint),endpoint);
        r.research_question=questionText;r.datasets=ids;r.transformations=mode?{[ids[0]]:mode}:{};r.workspace={...defaultWorkspace(),mode:ids.length===1?'overlay':'separate',chart_type:mode==='jobs'?'bar':'line'};
        await openInvestigation(r);
    }
    function openDataset(id:string,mode?:Transformation){void begin([id],mode);}
    async function openInvestigation(s:Investigation){try{await research.open(s);setComparison(null);setTab('Investigate');window.history.pushState(null,'','?view=research');}catch(e){research.fail(e);}}
    async function saveDiscovery(value:Investigation):Promise<boolean>{try{await research.open(value);await research.save(null);setNotice('Discovery evidence saved on this browser. Current calculations remain separate.');return true;}catch(e){research.fail(e);return false;}}
    if(!research.ready||!viewReady)return <main aria-busy="true"><p>Opening local research…</p></main>;
    return <AppShell active={tab} onNavigate={navigate}>
    {tab!=='Today'&&tab!=='Investigate'&&<div className="page-heading"><h1>{pageLabel(tab)}</h1><p>{tab==='Investigate'?'Follow your question. Keep the evidence.':tab==='Discovery Radar'?'A few signals worth understanding.':tab==='My Research'?'Your questions, evidence and conclusions.':tab==='Dataset Explorer'?'Find the data behind your question.':'AI assistance is not available.'}</p></div>}
    {notice&&<div className="notice" role="status">{notice}<button onClick={()=>setNotice('')}>Dismiss</button></div>}
    {error&&<div className="notice" role="alert">{error}<button onClick={load}>Retry connection</button></div>}
    {tab==='Today'&&<HomeDashboard datasets={homeData} loading={loading} dataIssue={homeIssue} records={[...saved.filter(s=>!research.drafts.some(d=>d.record.id===s.id)),...research.drafts.map(d=>d.record)]} onStart={q=>void begin(undefined,undefined,q)} onResume={openInvestigation} onDataset={openDataset} onDiscover={()=>navigate('Discovery Radar')}/>}
    {tab === 'Discovery Radar' && <DiscoveryRadar onOpen={openInvestigation} onSave={saveDiscovery}/>}
    {(tab==='Investigate'||tab==='My Research'||research.error)&&<section className="ml-storage" aria-label="Local research persistence"><span role="status">{storageCopy[research.status]||research.status}</span><details><summary>Backup & recovery</summary><Button variant="outline" onClick={()=>research.exportDraft()}>Export active draft</Button></details>{research.error&&<div role="alert">{research.error}<Button variant="outline" onClick={()=>research.flush().catch(research.fail)}>Retry draft save</Button><Button variant="outline" onClick={()=>research.exportDraft()}>Export active draft</Button></div>}</section>}
    {tab==='Investigate'&&<ResearchQuestion record={record} onChange={setRecord}/>}
    {tab==='Investigate'&&<ResearchDataPicker selected={selected} datasets={comparison?[...datasets.filter(d=>!comparison.datasets.some(c=>c.id===d.id)),...comparison.datasets]:datasets} onToggle={toggle} onMetadata={mergeMetadata} onBrowse={()=>navigate('Dataset Explorer')}/>}
    {tab === 'Investigate' && discoverySnapshot&&<details className="card discovery-origin ml-origin"><summary>Started from: {discoverySnapshot.finding.headline}</summary><span className="eyebrow">ORIGINAL DISCOVERY SNAPSHOT</span><h3>{discoverySnapshot.finding.headline}</h3><p>Detected {new Date(discoverySnapshot.generated_at).toLocaleString()}. The evidence below is preserved; charts and statistics recalculate using latest revised observations and your current settings.</p><DiscoveryEvidence finding={discoverySnapshot.finding}/>{Array.isArray(discoverySnapshot.finding.limitations)&&<ul>{discoverySnapshot.finding.limitations.filter((v):v is string=>typeof v==='string').map((v,i)=><li key={i}>{v}</li>)}</ul>}<div className="discovery-actions"><Button variant="outline" onClick={()=>{setStart(discoverySnapshot.finding.evidence.baseline.start);setEnd(discoverySnapshot.finding.evidence.baseline.end);setRange('Custom');}}>View baseline window</Button>{discoverySnapshot.finding.evidence.recent&&<Button variant="outline" onClick={()=>{setStart(discoverySnapshot.finding.evidence.recent!.start);setEnd(discoverySnapshot.finding.evidence.recent!.end);setRange('Custom');}}>View recent window</Button>}<Button variant="outline" onClick={()=>{setStart(discoverySnapshot.finding.configuration.start);setEnd(discoverySnapshot.finding.configuration.end);setRange('Custom');}}>View full discovery period</Button></div><details><summary>Original calculation settings & evidence</summary><pre className="provenance-record">{JSON.stringify(discoverySnapshot.finding,null,2)}</pre></details></details>}
    {tab === 'Investigate' && historicalContext&&<details className="card historical-origin ml-origin"><summary>Original historical comparison</summary><span className="eyebrow">PRESERVED HISTORICAL COMPARISON</span><h3>{historicalContext.label}</h3><HistoricalComparison record={historicalContext}/><p className="quiet">Both panels above are the saved comparison snapshot. The workspace below recalculates from current revised data.</p></details>}
    {tab === 'Investigate'&&unavailable.length>0&&<div role="alert"><b>Some saved data is unavailable.</b><p>Your writing and saved evidence are safe. Choose other data for new results.</p><details><summary>Unavailable references</summary>{unavailable.join(', ')}</details></div>}
    {tab === 'Investigate' && <InvestigationWorkspace horizons={activeHorizons} observationBasis={observationBasis} onHorizons={setHorizons} onObservationBasis={setObservationBasis} datasets={datasets} selected={selected} range={range} start={start} end={end} transformations={transformations} alignment={alignment} rollingWindow={effectiveWindow} comparison={comparison} comparing={comparing} error={compareError} settings={workspace} note={note} onSettings={setWorkspace} onTransformations={setTransformations} onAlignment={setAlignment} onWindow={v=>{setRollingWindow(v);setWindowExplicit(true);}} onPreset={preset} onCustom={()=>setRange('Custom')} onStart={v=>{setStart(v);setRange('Custom');}} onEnd={v=>{setEnd(v);setRange('Custom');}} onToggle={toggle} onAdd={()=>document.getElementById('research-data-search')?.focus()} saving={saving} onSave={save} onDownload={download} onNote={setNote}/>}
    {tab==='Investigate'&&<ResearchReview record={record} onChange={setRecord} comparison={comparing?null:comparison} canAttach={canAttach} saving={saving} onSave={save} onSaveExit={saveExit}/>}
    {tab==='Investigate'&&<CalculationHistory record={record} comparison={comparison}/>}
    {tab === 'Dataset Explorer' && <CatalogExplorer selected={selected} favorites={favorites} onFavorite={favorite} onToggle={toggle} onCompare={()=>navigate('Investigate')} onMetadata={mergeMetadata}/>}
    {tab==='Ask MacroLens'&&<section className="ml-surface ml-empty"><h2>AI assistance is not available</h2><p>Explore observed data and develop your own interpretation.</p><Button onClick={()=>navigate('Investigate')}>Back to Research</Button></section>}
    {tab==='My Research'&&<ResearchLibrary saved={saved} drafts={research.drafts} datasets={datasets} onResume={openInvestigation} onCreate={()=>void begin()} onExport={r=>research.exportDraft(r)}/>}
    </AppShell>;
}
