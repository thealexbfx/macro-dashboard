'use client';
import { useCallback, useEffect, useState, useMemo } from 'react';
import { Activity, Bookmark, ArrowUpRight, ChartNoAxesCombined, ChevronRight, Compass, Database, Folder, Globe, Search, Sparkles } from 'lucide-react';
import { CatalogExplorer, type CatalogPage } from '../components/catalog-explorer';
import { MarketWidget, EconomicWidget } from '../components/data-widgets';
import { defaultRollingWindow, timeframeStart, type Timeframe } from '../lib/presentation';
import { Button } from '../components/ui/button';
import { request, type Dataset, type Comparison, type Investigation, type Transformation, type InvestigationV4 } from '../lib/contracts';
const tabs = ['Today', 'Discovery Radar', 'Investigate', 'Dataset Explorer', 'Ask MacroLens', 'My Research'];
const icons = [Activity, Compass, ChartNoAxesCombined, Database, Sparkles, Folder];
import { DiscoveryRadar, DiscoveryEvidence, HistoricalComparison, DiscoveryHighlights } from '../components/discovery-radar';
import { InvestigationWorkspace } from '../components/investigation-workspace';
import { commonFrequency, defaultWorkspace } from '../lib/workspace';
import {useResearchFoundation} from '../lib/use-research-foundation';
import {ResearchQuestion,ResearchReview,CalculationHistory} from '../components/research-journey';
import {newInvestigation,receiptMatches} from '../lib/investigation';
const yesterday = () => new Date(Date.now() - 86400000).toISOString().slice(0, 10);
export default function Page() {
    const research=useResearchFoundation(), {record, setRecord, saved}=research;
    function field<K extends keyof InvestigationV4>(key:K){return (v:InvestigationV4[K]|((p:InvestigationV4[K])=>InvestigationV4[K]))=>setRecord(p=>({...p,[key]:typeof v==='function'?(v as (p:InvestigationV4[K])=>InvestigationV4[K])(p[key]):v}));}
    const selected=record.datasets,setSelected=field('datasets'),range=record.timeframe,setRange=field('timeframe'),start=record.start,setStart=field('start'),end=record.end,setEnd=field('end'),transformations=record.transformations,setTransformations=field('transformations'),alignment=record.alignment,setAlignment=field('alignment'),rollingWindow=record.rolling_window,setRollingWindow=field('rolling_window'),note=record.note,setNote=field('note'),workspace=record.workspace,setWorkspace=field('workspace'),horizons=record.horizons,setHorizons=field('horizons'),observationBasis=record.observation_basis,setObservationBasis=field('observation_basis'),discoverySnapshot=record.discovery,historicalContext=record.historical_context;
    const windowExplicit=record.window_explicit,setWindowExplicit=field('window_explicit');
    const [tab,setTab]=useState('Today'),[datasets,setDatasets]=useState<Dataset[]>([]),[loading,setLoading]=useState(true),[error,setError]=useState(''),[comparison,setComparison]=useState<Comparison|null>(null),[comparing,setComparing]=useState(false),[compareError,setCompareError]=useState(''),[search,setSearch]=useState(''),[favorites,setFavorites]=useState<string[]>([]),[question,setQuestion]=useState(''),[notice,setNotice]=useState(''),[collection,setCollection]=useState('All collections'),[saving,setSaving]=useState(false);
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
            const today=['sp500','gold','us10y','dxy','wti','cpi_nsa','unemployment','fed_funds','payrolls','real_gdp_growth'];
            let index=0;await Promise.all(Array.from({length:3},async()=>{while(index<today.length){const id=today[index++];try{const result=await request<{dataset:Dataset}>(`observations/${id}?preview=true&limit=40`);mergeMetadata([result.dataset]);}catch{/* Individual widgets retain unavailable state. */}}}));
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
    useEffect(()=>{if(research.ready&&research.restored)setTab('Investigate');},[research.ready,research.restored]);
    // Keep the effective calculation window in the durable record as metadata arrives.
    useEffect(()=>{if(research.ready&&!windowExplicit&&record.rolling_window!==effectiveWindow)setRecord(p=>({...p,rolling_window:effectiveWindow}));},[research.ready,windowExplicit,record.rolling_window,effectiveWindow,setRecord]);
    async function navigate(name:string){try{await research.flush();}catch(e){research.fail(e);}setTab(name);setSearch('');window.scrollTo({top:0,behavior:'auto'});}

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
            setNotice(canAttach?'Research and current calculation saved on this browser.':'Research saved on this browser. No new calculation was captured; earlier evidence remains unchanged.');
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
    async function begin(ids=['cpi','unemployment'],mode?:Transformation){
        const endpoint=yesterday(),r=newInvestigation(crypto.randomUUID(),new Date().toISOString(),timeframeStart('5Y',endpoint),endpoint);
        r.datasets=ids;r.transformations=mode?{[ids[0]]:mode}:{};r.workspace={...defaultWorkspace(),mode:ids.length===1?'overlay':'separate',chart_type:mode==='jobs'?'bar':'line'};
        await openInvestigation(r);
    }
    function openDataset(id:string,mode?:Transformation){void begin([id],mode);}
    async function openInvestigation(s:Investigation){try{await research.open(s);setComparison(null);setTab('Investigate');}catch(e){research.fail(e);}}
    async function saveDiscovery(value:Investigation):Promise<boolean>{try{await research.open(value);await research.save(null);setNotice('Discovery evidence saved on this browser. Current calculations remain separate.');return true;}catch(e){research.fail(e);return false;}}
    if(!research.ready)return <main aria-busy="true"><p>Opening local research…</p></main>;
    return <div className="shell"><aside><a className="brand" href="#" onClick={() => navigate('Today')}><span className="brandmark"><ChartNoAxesCombined size={23}/></span>MacroLens<span className="version">2.0</span></a><nav>{tabs.map((name, i) => { const Icon = icons[i]; return <button key={name} className={tab === name ? 'active' : ''} onClick={() => navigate(name)}><Icon size={18}/>{name}{name === 'Ask MacroLens' && <span className="new">AI</span>}</button>; })}</nav></aside><div className="main"><header><div><Globe size={15}/> Global macro <ChevronRight size={13}/> <b>{tab}</b></div><span className="mock">REAL OBSERVATIONS · DELAYED</span></header><main className={tab==='Investigate'?'investigate-page':tab==='Discovery Radar'?'discovery-page':undefined}><div className="page-heading"><div><div className="eyebrow">YOUR EDGE STARTS WITH CONTEXT</div><h1>{tab === 'Today' ? 'The macro picture. In focus.' : tab}</h1><p>{tab === 'Today' ? 'Follow the signals. Connect the dots. Discover what matters.' : tab === 'Discovery Radar' ? 'Systematic discovery. Questions grounded in observations.' : tab === 'Investigate' ? 'Turn an observation into a deeper understanding.' : tab === 'Dataset Explorer' ? 'A world of economic data, ready to explore.' : tab === 'Ask MacroLens' ? 'Better questions. Deeper macro context.' : 'Your ideas, connected and collected.'}</p></div><span className="date">RESEARCH WORKSPACE<br /><b>{new Date().toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' })}</b></span></div>{notice && <div className="notice" role="status">{notice}<button onClick={() => setNotice('')}>Dismiss</button></div>}{error && <div className="notice" role="alert">{error} <button onClick={load}>Retry connection</button></div>}{loading && <p role="status" className="quiet">Retrieving source observations… providers may take a few seconds.</p>}
    {tab === 'Today' && <><div className="market-grid">{['sp500', 'gold', 'us10y', 'dxy', 'wti'].map(id => <MarketWidget key={id} id={id} dataset={datasets.find(d => d.id === id)} loading={loading} onOpen={() => openDataset(id)}/>)}</div><p className="quiet market-disclosure">Delayed closing data, not live quotes. Changes compare available observations. Gold and WTI are continuous futures, not spot prices. Yahoo closing prices have not been independently confirmed. Compact lines connect valid sessions; see Investigate for missing observations.</p><div className="section-title"><h2><Compass size={18}/>Discovery Radar</h2><span>Evidence-first research</span></div><DiscoveryHighlights onOpen={openInvestigation} onRadar={()=>navigate('Discovery Radar')}/><div className="lower-grid"><section><div className="section-title"><h2>Economic pulse</h2><button onClick={() => navigate('Dataset Explorer')}>Explore datasets →</button></div><div className="indicator-grid">{['cpi_nsa', 'unemployment', 'fed_funds', 'payrolls', 'real_gdp_growth'].map(id => <EconomicWidget key={id} id={id} dataset={datasets.find(d => d.id === id)} onOpen={() => openDataset(id,datasets.find(d=>d.id===id)?.recommended_headline_transformation)}/>)}</div></section><section><div className="section-title"><h2>Research opportunities</h2></div><div className="card opportunities">{['Compare inflation and unemployment', 'Explore policy rates and Treasury yields', 'Review growth and labour data'].map((s, i) => <button key={s} onClick={() => { void begin([['cpi', 'unemployment'], ['fed_funds', 'us10y'], ['real_gdp_growth', 'payrolls']][i]); }}><div>{s}<small>Research prompt · No inferred signal</small></div><ChevronRight size={16}/></button>)}</div></section></div></>}
    {tab === 'Discovery Radar' && <DiscoveryRadar onOpen={openInvestigation} onSave={saveDiscovery}/>}
    {<section className="card insight" aria-label="Local research persistence"><p role="status">{research.status} · Browser-local only; no cloud sync.</p>{research.error&&<p role="alert">{research.error} <Button variant="outline" onClick={()=>research.flush().catch(research.fail)}>Retry draft save</Button></p>}<Button variant="outline" onClick={research.exportDraft}>Export active draft</Button></section>}
    {tab==='Investigate'&&<ResearchQuestion record={record} onChange={setRecord}/>}
    {tab==='Investigate'&&<CalculationHistory record={record} comparison={comparison}/>}
    {tab === 'Investigate' && discoverySnapshot&&<section className="card discovery-origin"><span className="eyebrow">ORIGINAL DISCOVERY SNAPSHOT</span><h3>{discoverySnapshot.finding.headline}</h3><p>Detected {new Date(discoverySnapshot.generated_at).toLocaleString()}. The evidence below is preserved; charts and statistics recalculate using latest revised observations and your current settings.</p><DiscoveryEvidence finding={discoverySnapshot.finding}/>{Array.isArray(discoverySnapshot.finding.limitations)&&<ul>{discoverySnapshot.finding.limitations.filter((v):v is string=>typeof v==='string').map((v,i)=><li key={i}>{v}</li>)}</ul>}<div className="discovery-actions"><Button variant="outline" onClick={()=>{setStart(discoverySnapshot.finding.evidence.baseline.start);setEnd(discoverySnapshot.finding.evidence.baseline.end);setRange('Custom');}}>View baseline window</Button>{discoverySnapshot.finding.evidence.recent&&<Button variant="outline" onClick={()=>{setStart(discoverySnapshot.finding.evidence.recent!.start);setEnd(discoverySnapshot.finding.evidence.recent!.end);setRange('Custom');}}>View recent window</Button>}<Button variant="outline" onClick={()=>{setStart(discoverySnapshot.finding.configuration.start);setEnd(discoverySnapshot.finding.configuration.end);setRange('Custom');}}>View full discovery period</Button></div><details><summary>Original calculation settings & evidence</summary><pre className="provenance-record">{JSON.stringify(discoverySnapshot.finding,null,2)}</pre></details></section>}
    {tab === 'Investigate' && historicalContext&&<section className="card historical-origin"><span className="eyebrow">PRESERVED HISTORICAL COMPARISON</span><h3>{historicalContext.label}</h3><HistoricalComparison record={historicalContext}/><p className="quiet">Both panels above are the saved comparison snapshot. The workspace below recalculates from current revised data.</p></section>}
    {tab === 'Investigate'&&unavailable.length>0&&<div role="alert">Some saved dataset references are unavailable, retired or private: {unavailable.join(', ')}. Your saved research and favourites were preserved. Remove an unavailable reference to continue.</div>}
    {tab === 'Investigate' && <InvestigationWorkspace horizons={activeHorizons} observationBasis={observationBasis} onHorizons={setHorizons} onObservationBasis={setObservationBasis} datasets={datasets} selected={selected} range={range} start={start} end={end} transformations={transformations} alignment={alignment} rollingWindow={effectiveWindow} comparison={comparison} comparing={comparing} error={compareError} settings={workspace} note={note} onSettings={setWorkspace} onTransformations={setTransformations} onAlignment={setAlignment} onWindow={v=>{setRollingWindow(v);setWindowExplicit(true);}} onPreset={preset} onCustom={()=>setRange('Custom')} onStart={v=>{setStart(v);setRange('Custom');}} onEnd={v=>{setEnd(v);setRange('Custom');}} onToggle={toggle} onAdd={()=>navigate('Dataset Explorer')} saving={saving} onSave={save} onDownload={download} onNote={setNote}/>}
    {tab==='Investigate'&&<ResearchReview record={record} onChange={setRecord} comparison={comparing?null:comparison} canAttach={canAttach} saving={saving} onSave={save} onSaveExit={saveExit}/>}
    {tab === 'Dataset Explorer' && <CatalogExplorer selected={selected} favorites={favorites} onFavorite={favorite} onToggle={toggle} onCompare={()=>navigate('Investigate')} onMetadata={mergeMetadata}/>}
    {tab === 'Ask MacroLens' && <div className="ask-layout"><div className="card ask-card"><span className="ai-orb"><Sparkles size={28}/></span><h2>What are you curious about?</h2><p>Explore the connections behind the macro picture.</p><div className="suggestions">{['Is inflation cooling faster than expected?', 'How do interest rates influence equities?', 'What is the outlook for US growth?'].map(q => <button key={q} onClick={() => setQuestion(q)}>{q}<ArrowUpRight size={15}/></button>)}</div><form onSubmit={e => e.preventDefault()}><textarea aria-label="Research question" value={question} onChange={e => setQuestion(e.target.value)} placeholder="Ask a macroeconomic research question…"/><Button disabled type="submit">Available in Phase 3</Button></form><small>NOT LIVE IN PHASE 2 · No AI requests are sent</small></div><div className="card insight"><h3><Sparkles size={16}/> Research with context</h3><p>The existing Ask backend is preserved for Phase 3. Explore actual observations and descriptive statistics in Investigate.</p></div></div>}
    {tab === 'My Research' && <>{research.drafts.some(d=>!saved.some(s=>s.id===d.record.id))&&<section className="card insight local-research-drafts"><h2>Local drafts</h2>{research.drafts.filter(d=>!saved.some(s=>s.id===d.record.id)).map(d=><p key={d.record.id}><Button variant="outline" onClick={()=>openInvestigation(d.record)}>{d.record.research_question||d.record.title} · Open draft</Button></p>)}</section>}<div className="toolbar"><label className="search"><Search size={17}/><input aria-label="Search saved research" placeholder="Search your investigations…" value={search} onChange={e => setSearch(e.target.value)}/></label><select aria-label="Collection" value={collection} onChange={e => setCollection(e.target.value)}><option>All collections</option><option>Macro outlook</option><option>Discovery Radar</option></select><Button onClick={() => void begin()}>+ New investigation</Button></div>{!saved.length ? <div className="card empty"><Bookmark size={32}/><h2>Your next insight starts here.</h2><p>Save an investigation to collect charts, comparisons and notes in this workspace.</p><Button onClick={() => void begin()}>Start investigating</Button></div> : <div className="research-grid">{saved.filter(s => (s.title + ' ' + s.research_question + ' ' + s.conclusion + ' ' + s.note).toLowerCase().includes(search.toLowerCase()) && (collection === 'All collections' || s.collection === collection)).map(s => <article className="card insight" key={s.id}><span className="eyebrow">{s.collection}</span><h3>{s.research_question||s.title}</h3><p className="quiet">Saved revision {s.revision} · Updated {s.updated_at?new Date(s.updated_at).toLocaleString():'not recorded for this older research'}{research.drafts.some(d=>d.record.id===s.id)?' · Local draft available':''}</p>{s.conclusion&&<p>{s.conclusion}</p>}{s.discovery&&<p className="discovery-type">Saved discovery · {s.discovery.finding.label}<br/>Original evidence: {s.discovery.finding.observation_date}</p>}<p>{s.note || 'No research notes yet.'}</p><p>{(s.version === 4) ? `${s.start} to ${s.end} · ${s.discovery?'Evidence snapshot preserved; charts refresh on reopen.':'References only; observations refresh on reopen.'}` : 'Phase 1 prototype note — preserved. Mock dataset IDs are not automatically mapped to real data.'}</p>{(s.version===4)&&s.workspace&&<p className="saved-workspace-settings">{s.workspace.mode} · {s.workspace.chart_type} · {s.timeframe||'Custom'}{s.workspace.lead_lag.periods?` · ${s.workspace.lead_lag.periods>0?'+':''}${s.workspace.lead_lag.periods} ${s.workspace.lead_lag.unit.replace('_',' ')}`:''}</p>}<Button variant="outline" onClick={() => openInvestigation(s)}>Open investigation <ArrowUpRight size={15}/></Button></article>)}</div>}</>}
    <footer><span><span className="footer-dot"/>MacroLens Research</span><span>Phase 3.2 · Real observations · Latest revisions · No causal claims</span><span>Built for the bigger picture.</span></footer></main></div></div>;
}
