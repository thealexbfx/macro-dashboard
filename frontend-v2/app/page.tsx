'use client';
import { useCallback, useEffect, useState } from 'react';
import { Activity, Bookmark, ArrowUpRight, ChartNoAxesCombined, ChevronRight, Compass, Database, Folder, Globe, Search, Sparkles, Star } from 'lucide-react';
import { MarketWidget, EconomicWidget, DatasetMetadata } from '../components/data-widgets';
import { timeframeStart, formatDatasetValue, referenceLabel, freshness, type Timeframe } from '../lib/presentation';
import { Button } from '../components/ui/button';
import { request, type Dataset, type Comparison, type Investigation, type Transformation } from '../lib/contracts';
const tabs = ['Today', 'Investigate', 'Dataset Explorer', 'Ask MacroLens', 'My Research'];
const icons = [Activity, ChartNoAxesCombined, Database, Sparkles, Folder];
import { InvestigationWorkspace } from '../components/investigation-workspace';
import { defaultWorkspace, restoreWorkspace, readInvestigations, appendInvestigation } from '../lib/workspace';
const yesterday = () => new Date(Date.now() - 86400000).toISOString().slice(0, 10);
export default function Page() {
    const [tab, setTab] = useState('Today'), [datasets, setDatasets] = useState<Dataset[]>([]), [loading, setLoading] = useState(true), [error, setError] = useState(''), [selected, setSelected] = useState(['cpi', 'unemployment']), [range, setRange] = useState('5Y'), [start, setStart] = useState(() => timeframeStart('5Y', yesterday())), [end, setEnd] = useState(yesterday), [transformations, setTransformations] = useState<Record<string, Transformation>>({}), [alignment, setAlignment] = useState<'native' | 'period_end'>('native'), [rollingWindow, setRollingWindow] = useState(12), [comparison, setComparison] = useState<Comparison | null>(null), [comparing, setComparing] = useState(false), [compareError, setCompareError] = useState(''), [search, setSearch] = useState(''), [category, setCategory] = useState('All categories'), [region, setRegion] = useState('All regions'), [source, setSource] = useState('All sources'), [favorites, setFavorites] = useState<string[]>([]), [onlyFav, setOnlyFav] = useState(false), [saved, setSaved] = useState<Investigation[]>([]), [note, setNote] = useState(''), [question, setQuestion] = useState(''), [notice, setNotice] = useState(''), [collection, setCollection] = useState('All collections');
    const [workspace,setWorkspace]=useState(defaultWorkspace);
    const load = useCallback(async () => {
        setLoading(true);
        setError('');
        try {
            setDatasets(await request<Dataset[]>('datasets'));
        }
        catch (e) {
            setError((e as Error).message);
        }
        finally {
            setLoading(false);
        }
    }, []);
    useEffect(() => {
        load();
        try {
            setSaved(readInvestigations(localStorage));
            setFavorites(JSON.parse(localStorage.getItem('ml-favorites') || '[]'));
        }
        catch {
            setNotice('Browser storage could not be read. Existing records were not changed.');
        }
    }, [load]);
    useEffect(() => {
        if (tab !== 'Investigate')
            return;
        const controller = new AbortController();
        setComparison(null);
        setCompareError('');
        if (!selected.length) {
            setComparing(false);
            return;
        }
        setComparing(true);
        request<Comparison>('compare', { datasets: selected, transformations, start, end, alignment: selected.length > 1 ? alignment : "native", rolling_window: rollingWindow, lead_lag: selected.length>1&&selected.includes(workspace.lead_lag.dataset_id)&&workspace.lead_lag.periods?workspace.lead_lag:undefined }, controller.signal).then(setComparison).catch(e => {
            if (e.name !== 'AbortError')
                setCompareError(e.message);
        }).finally(() => {
            if (!controller.signal.aborted)
                setComparing(false);
        });
        return () => controller.abort();
    }, [tab, selected, transformations, start, end, alignment, rollingWindow, workspace.lead_lag]);
    function navigate(name: string) { setTab(name); setSearch(''); }
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
    function save() {
        const record: Investigation = { id: crypto.randomUUID(), title: selected.map(id => datasets.find(d => d.id === id)?.name || id).join(' / '), datasets: selected, note, collection: 'Macro outlook', version: 3, workspace, timeframe: range, transformations, start, end, alignment: selected.length > 1 ? alignment : "native", rolling_window: rollingWindow };
        try {
            const next=appendInvestigation(localStorage,record);
            setSaved(next);
            setNotice('Investigation saved locally. References and settings only; reopening retrieves revised data, not a frozen snapshot.');
        }
        catch {
            setNotice('Browser storage is full or unavailable; investigation was not saved.');
        }
    }
    function preset(r: Timeframe) { const endpoint = yesterday(); setRange(r); setEnd(endpoint); setStart(timeframeStart(r, endpoint)); }
    function download() {
        if (!comparison)
            return;
        const escape = (v: unknown) => `"${String(v ?? '').replaceAll('"', '""')}"`;
        const rows = [['dataset_id', 'provider_id', 'source', 'date', 'kind', 'transformation', 'value', 'units', 'source_reference_date', 'shift_periods', 'shift_unit']];
        for (const d of comparison.datasets) {
            for (const o of comparison.raw_observations[d.id])
                rows.push([d.id, d.provider_id, d.source, o.date, 'raw', 'level', String(o.value ?? ''), d.units, o.date, '0', '']);
            const s = comparison.series.find(s => s.id === d.id)!;
            for (const o of s.observations)
                rows.push([d.id, d.provider_id, d.source, o.date, 'analytical', s.transformation, String(o.value ?? ''), s.units, s.source_dates?.[o.date]||'',String(s.shift_periods||0),s.shift_unit||'']);
        }
        const url = URL.createObjectURL(new Blob([rows.map(r => r.map(escape).join(',')).join('\r\n')], { type: 'text/csv;charset=utf-8' }));
        const a = document.createElement('a');
        a.href = url;
        a.download = 'macrolens-observations.csv';
        a.click();
        URL.revokeObjectURL(url);
    }
    const shown = datasets.filter(d => (d.name + ' ' + d.source + ' ' + d.provider_id).toLowerCase().includes(search.toLowerCase()) && (category === 'All categories' || d.category === category) && (region === 'All regions' || d.region === region) && (source === 'All sources' || d.source === source) && (!onlyFav || favorites.includes(d.id)));
    function openDataset(id: string, mode?:Transformation) { setSelected([id]); setTransformations(mode?{[id]:mode}:{});setWorkspace({...defaultWorkspace(),mode:'overlay',chart_type:mode==='jobs'?'bar':'line'}); navigate('Investigate'); }
    return <div className="shell"><aside><a className="brand" href="#" onClick={() => navigate('Today')}><span className="brandmark"><ChartNoAxesCombined size={23}/></span>MacroLens<span className="version">2.0</span></a><nav>{tabs.map((name, i) => { const Icon = icons[i]; return <button key={name} className={tab === name ? 'active' : ''} onClick={() => navigate(name)}><Icon size={18}/>{name}{name === 'Ask MacroLens' && <span className="new">AI</span>}</button>; })}</nav></aside><div className="main"><header><div><Globe size={15}/> Global macro <ChevronRight size={13}/> <b>{tab}</b></div><span className="mock">REAL OBSERVATIONS · DELAYED</span></header><main className={tab==='Investigate'?'investigate-page':undefined}><div className="page-heading"><div><div className="eyebrow">YOUR EDGE STARTS WITH CONTEXT</div><h1>{tab === 'Today' ? 'The macro picture. In focus.' : tab}</h1><p>{tab === 'Today' ? 'Follow the signals. Connect the dots. Discover what matters.' : tab === 'Investigate' ? 'Turn an observation into a deeper understanding.' : tab === 'Dataset Explorer' ? 'A world of economic data, ready to explore.' : tab === 'Ask MacroLens' ? 'Better questions. Deeper macro context.' : 'Your ideas, connected and collected.'}</p></div><span className="date">RESEARCH WORKSPACE<br /><b>{new Date().toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' })}</b></span></div>{notice && <div className="notice" role="status">{notice}<button onClick={() => setNotice('')}>Dismiss</button></div>}{error && <div className="notice" role="alert">{error} <button onClick={load}>Retry connection</button></div>}{loading && <p role="status" className="quiet">Retrieving source observations… providers may take a few seconds.</p>}
    {tab === 'Today' && <><div className="market-grid">{['sp500', 'gold', 'us10y', 'dxy', 'wti'].map(id => <MarketWidget key={id} id={id} dataset={datasets.find(d => d.id === id)} loading={loading} onOpen={() => openDataset(id)}/>)}</div><p className="quiet market-disclosure">Completed provider daily labels, excluding today (UTC). Delayed observations, not live quotes. Changes are relative to the previous available source observation; missing sessions may widen that interval. Gold GC=F and WTI CL=F are continuous futures, not spot prices.</p><div className="section-title"><h2><Compass size={18}/>Discovery Radar <span className="pill">PHASE 3</span></h2><span>Interesting moves. Worth a closer look.</span></div><div className="radar-grid">{[['POLICY DIVERGENCE', 'Policy paths in context'], ['INFLATION WATCH', 'The final mile of disinflation'], ['CROSS-ASSET SIGNAL', 'Relationships worth investigating']].map(r => <article className="card radar" key={r[0]}><div className="signal"><span />{r[0]}</div><h3>{r[1]}</h3><p>Signal detection is not active in Phase 2. Explore real observations in the research workspace.</p><div className="radar-footer"><small>Unavailable · Phase 3</small><button onClick={() => navigate('Investigate')}>Explore data <ChevronRight size={14}/></button></div></article>)}</div><div className="lower-grid"><section><div className="section-title"><h2>Economic pulse</h2><button onClick={() => navigate('Dataset Explorer')}>Explore datasets →</button></div><div className="indicator-grid">{['cpi_nsa', 'unemployment', 'fed_funds', 'payrolls', 'real_gdp_growth'].map(id => <EconomicWidget key={id} id={id} dataset={datasets.find(d => d.id === id)} onOpen={() => openDataset(id,datasets.find(d=>d.id===id)?.recommended_headline_transformation)}/>)}</div></section><section><div className="section-title"><h2>Research opportunities</h2></div><div className="card opportunities">{['Compare inflation and unemployment', 'Explore policy rates and Treasury yields', 'Review growth and labour data'].map((s, i) => <button key={s} onClick={() => { setSelected([['cpi', 'unemployment'], ['fed_funds', 'us10y'], ['real_gdp_growth', 'payrolls']][i]); setTransformations({}); navigate('Investigate'); }}><div>{s}<small>Research prompt · No inferred signal</small></div><ChevronRight size={16}/></button>)}</div></section></div></>}
    {tab === 'Investigate' && <InvestigationWorkspace datasets={datasets} selected={selected} range={range} start={start} end={end} transformations={transformations} alignment={alignment} rollingWindow={rollingWindow} comparison={comparison} comparing={comparing} error={compareError} settings={workspace} note={note} onSettings={setWorkspace} onTransformations={setTransformations} onAlignment={setAlignment} onWindow={setRollingWindow} onPreset={preset} onCustom={()=>setRange('Custom')} onStart={v=>{setStart(v);setRange('Custom');}} onEnd={v=>{setEnd(v);setRange('Custom');}} onToggle={toggle} onAdd={()=>navigate('Dataset Explorer')} onSave={save} onDownload={download} onNote={setNote}/>}
    {tab === 'Dataset Explorer' && <><div className="toolbar filters"><label className="search"><Search size={17}/><input placeholder="Search datasets or sources…" aria-label="Search datasets" value={search} onChange={e => setSearch(e.target.value)}/></label>{[[category, setCategory, 'All categories', Array.from(new Set(datasets.map(d => d.category)))], [region, setRegion, 'All regions', Array.from(new Set(datasets.map(d => d.region)))], [source, setSource, 'All sources', Array.from(new Set(datasets.map(d => d.source)))]].map(([value, setter, label, options]) => <select key={String(label)} aria-label={String(label)} value={String(value)} onChange={e => (setter as (v: string) => void)(e.target.value)}><option>{String(label)}</option>{(options as string[]).map(o => <option key={o}>{o}</option>)}</select>)}<Button variant="outline" onClick={() => setOnlyFav(!onlyFav)}><Star size={15}/>{onlyFav ? 'Favourites only' : 'All datasets'}</Button><Button variant="outline" onClick={load} disabled={loading}>Refresh</Button></div><div className="card table-wrap"><table><thead><tr><th>Dataset / source</th><th>Category / region</th><th>Frequency / units</th><th>Latest reference</th><th>Favourite</th><th>Compare</th></tr></thead><tbody>{shown.map(d => <tr key={d.id}><td><b>{d.name}</b><small>{d.source}</small><DatasetMetadata dataset={d}/></td><td>{d.category}<small>{d.region}</small></td><td>{d.frequency}<small>{d.units}</small></td><td>{referenceLabel(d)}<small className={d.status === 'stale' ? 'freshness stale' : 'freshness'}>{freshness(d)}</small><b className="explorer-value" title={String(d.latest_value ?? '')}>{formatDatasetValue(d)}</b></td><td><button aria-label={`Favourite ${d.name}`} aria-pressed={favorites.includes(d.id)} onClick={() => favorite(d.id)}><Star size={17} fill={favorites.includes(d.id) ? '#edb867' : 'none'}/></button></td><td><input type="checkbox" aria-label={`Compare ${d.name}`} checked={selected.includes(d.id)} disabled={!selected.includes(d.id) && selected.length >= 4} onChange={() => toggle(d.id)}/></td></tr>)}</tbody></table>{!loading && !shown.length && <p className="quiet">No datasets match your filters.</p>}<div className="table-bottom">{selected.length}/4 datasets selected<Button disabled={!selected.length} onClick={() => navigate('Investigate')}>Compare selected <ArrowUpRight size={15}/></Button></div></div></>}
    {tab === 'Ask MacroLens' && <div className="ask-layout"><div className="card ask-card"><span className="ai-orb"><Sparkles size={28}/></span><h2>What are you curious about?</h2><p>Explore the connections behind the macro picture.</p><div className="suggestions">{['Is inflation cooling faster than expected?', 'How do interest rates influence equities?', 'What is the outlook for US growth?'].map(q => <button key={q} onClick={() => setQuestion(q)}>{q}<ArrowUpRight size={15}/></button>)}</div><form onSubmit={e => e.preventDefault()}><textarea aria-label="Research question" value={question} onChange={e => setQuestion(e.target.value)} placeholder="Ask a macroeconomic research question…"/><Button disabled type="submit">Available in Phase 3</Button></form><small>NOT LIVE IN PHASE 2 · No AI requests are sent</small></div><div className="card insight"><h3><Sparkles size={16}/> Research with context</h3><p>The existing Ask backend is preserved for Phase 3. Explore actual observations and descriptive statistics in Investigate.</p></div></div>}
    {tab === 'My Research' && <><div className="toolbar"><label className="search"><Search size={17}/><input aria-label="Search saved research" placeholder="Search your investigations…" value={search} onChange={e => setSearch(e.target.value)}/></label><select aria-label="Collection" value={collection} onChange={e => setCollection(e.target.value)}><option>All collections</option><option>Macro outlook</option></select><Button onClick={() => navigate('Investigate')}>+ New investigation</Button></div>{!saved.length ? <div className="card empty"><Bookmark size={32}/><h2>Your next insight starts here.</h2><p>Save an investigation to collect charts, comparisons and notes in this workspace.</p><Button onClick={() => navigate('Investigate')}>Start investigating</Button></div> : <div className="research-grid">{saved.filter(s => (s.title + ' ' + s.note).toLowerCase().includes(search.toLowerCase()) && (collection === 'All collections' || s.collection === collection)).map(s => <article className="card insight" key={s.id}><span className="eyebrow">{s.collection}</span><h3>{s.title}</h3><p>{s.note || 'No research notes yet.'}</p><p>{(s.version === 2 || s.version === 3) ? `${s.start} to ${s.end} · References only; observations refresh on reopen.` : 'Phase 1 prototype note — preserved. Mock dataset IDs are not automatically mapped to real data.'}</p>{s.version===3&&s.workspace&&<p className="saved-workspace-settings">{s.workspace.mode} · {s.workspace.chart_type} · {s.timeframe||'Custom'}{s.workspace.lead_lag.periods?` · ${s.workspace.lead_lag.periods>0?'+':''}${s.workspace.lead_lag.periods} ${s.workspace.lead_lag.unit.replace('_',' ')}`:''}</p>}<Button variant="outline" onClick={() => {
                        setNote(s.note);
                        if ((s.version === 2 || s.version === 3)) {
                            setSelected(s.datasets);
                            setTransformations(s.transformations || {});
                            setStart(s.start!);
                            setEnd(s.end!);
                            setAlignment(s.alignment || 'native');
                            setRollingWindow(s.rolling_window || 12);
                            setRange(s.timeframe || 'Saved');
                            setWorkspace(restoreWorkspace(s));
                            navigate('Investigate');
                        }
                        else {
                            setNotice('Prototype note loaded. Choose real datasets to create a new investigation; the original note remains saved.');
                            navigate('Investigate');
                        }
                    }}>Open investigation <ArrowUpRight size={15}/></Button></article>)}</div>}</>}
    <footer><span><span className="footer-dot"/>MacroLens Research</span><span>Phase 2 · Real observations · Latest revisions · No causal claims</span><span>Built for the bigger picture.</span></footer></main></div></div>;
}
