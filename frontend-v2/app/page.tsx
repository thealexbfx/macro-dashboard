'use client';
import { useCallback, useEffect, useState } from 'react';
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { Activity, ArrowUpRight, Bookmark, ChartNoAxesCombined, ChevronRight, Compass, Database, Download, Folder, Globe, Search, Sparkles, Star } from 'lucide-react';
import { MarketWidget, EconomicWidget, DatasetMetadata } from '../components/data-widgets';
import { TIMEFRAMES, timeframeStart, dateLabel, formatNumber, formatDatasetValue, referenceLabel, freshness, type Timeframe } from '../lib/presentation';
import { Button } from '../components/ui/button';
import { request, transformLabels, type Dataset, type Comparison, type Investigation, type Transformation, type Observation } from '../lib/contracts';
const tabs = ['Today', 'Investigate', 'Dataset Explorer', 'Ask MacroLens', 'My Research'];
const icons = [Activity, ChartNoAxesCombined, Database, Sparkles, Folder];
const colors = ['#518cff', '#48cfba', '#b49aff', '#edb867'];
const yesterday = () => new Date(Date.now() - 86400000).toISOString().slice(0, 10);
const fmt = (n: number | null) => formatNumber(n, 3);
function HistoryChart({ data, units, color }: {
    data: Observation[];
    units: string;
    color: string;
}) {
    const shortDates = data.length > 0 && new Date(data.at(-1)!.date).getTime() - new Date(data[0].date).getTime() < 120 * 86400000;
    const tickDate = (v: string) => new Date(`${v}T00:00:00Z`).toLocaleDateString('en-GB', shortDates ? { day: 'numeric', month: 'short', timeZone: 'UTC' } : { month: 'short', year: '2-digit', timeZone: 'UTC' });
    return <ResponsiveContainer width="100%" height="100%"><LineChart data={data} margin={{ top: 12, right: 18, bottom: 8, left: 0 }}><CartesianGrid stroke="#243044" strokeDasharray="3 5" vertical={false}/><XAxis dataKey="date" tickFormatter={tickDate} tick={{ fill: '#9aaec9', fontSize: 12 }} minTickGap={32} axisLine={false} tickLine={false} tickMargin={10}/><YAxis tickFormatter={v => new Intl.NumberFormat('en-US', { notation: Math.abs(Number(v)) >= 1000 ? 'compact' : 'standard', maximumFractionDigits: Math.abs(Number(v)) < .01 ? 4 : 2 }).format(Number(v))} tick={{ fill: '#9aaec9', fontSize: 12 }} domain={['auto', 'auto']} width={66} axisLine={false} tickLine={false}/><Tooltip content={({ active, payload, label }) => active && payload?.length ? <div className="chart-tooltip"><b>{dateLabel(String(label))}</b><div style={{ color }}>{String(payload[0].value)} <span>{units}</span></div><small>Exact observation · no interpolation</small></div> : null}/><Line isAnimationActive={false} type="linear" dataKey="value" name={units} stroke={color} dot={data.length <= 35 ? { r: 2, strokeWidth: 0 } : false} activeDot={{ r: 5 }} strokeWidth={2} connectNulls={false}/></LineChart></ResponsiveContainer>;
}
export default function Page() {
    const [tab, setTab] = useState('Today'), [datasets, setDatasets] = useState<Dataset[]>([]), [loading, setLoading] = useState(true), [error, setError] = useState(''), [selected, setSelected] = useState(['cpi', 'unemployment']), [range, setRange] = useState('5Y'), [start, setStart] = useState(() => timeframeStart('5Y', yesterday())), [end, setEnd] = useState(yesterday), [transformations, setTransformations] = useState<Record<string, Transformation>>({}), [alignment, setAlignment] = useState<'native' | 'period_end'>('native'), [rollingWindow, setRollingWindow] = useState(12), [comparison, setComparison] = useState<Comparison | null>(null), [comparing, setComparing] = useState(false), [compareError, setCompareError] = useState(''), [search, setSearch] = useState(''), [category, setCategory] = useState('All categories'), [region, setRegion] = useState('All regions'), [source, setSource] = useState('All sources'), [favorites, setFavorites] = useState<string[]>([]), [onlyFav, setOnlyFav] = useState(false), [saved, setSaved] = useState<Investigation[]>([]), [note, setNote] = useState(''), [question, setQuestion] = useState(''), [notice, setNotice] = useState(''), [collection, setCollection] = useState('All collections');
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
            setSaved(JSON.parse(localStorage.getItem('ml-research') || '[]'));
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
        request<Comparison>('compare', { datasets: selected, transformations, start, end, alignment: selected.length > 1 ? alignment : "native", rolling_window: rollingWindow }, controller.signal).then(setComparison).catch(e => {
            if (e.name !== 'AbortError')
                setCompareError(e.message);
        }).finally(() => {
            if (!controller.signal.aborted)
                setComparing(false);
        });
        return () => controller.abort();
    }, [tab, selected, transformations, start, end, alignment, rollingWindow]);
    function navigate(name: string) { setTab(name); setSearch(''); }
    function toggle(id: string) { setSelected(s => s.includes(id) ? s.filter(x => x !== id) : s.length < 4 ? [...s, id] : s); }
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
        const next: Investigation[] = [{ id: crypto.randomUUID(), title: selected.map(id => datasets.find(d => d.id === id)?.name || id).join(' / '), datasets: selected, note, collection: 'Macro outlook', version: 2, transformations, start, end, alignment: selected.length > 1 ? alignment : "native", rolling_window: rollingWindow }, ...saved];
        try {
            localStorage.setItem('ml-research', JSON.stringify(next));
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
        const rows = [['dataset_id', 'provider_id', 'source', 'date', 'kind', 'transformation', 'value', 'units']];
        for (const d of comparison.datasets) {
            for (const o of comparison.raw_observations[d.id])
                rows.push([d.id, d.provider_id, d.source, o.date, 'raw', 'level', String(o.value ?? ''), d.units]);
            const s = comparison.series.find(s => s.id === d.id)!;
            for (const o of s.observations)
                rows.push([d.id, d.provider_id, d.source, o.date, 'analytical', s.transformation, String(o.value ?? ''), s.units]);
        }
        const url = URL.createObjectURL(new Blob([rows.map(r => r.map(escape).join(',')).join('\r\n')], { type: 'text/csv;charset=utf-8' }));
        const a = document.createElement('a');
        a.href = url;
        a.download = 'macrolens-observations.csv';
        a.click();
        URL.revokeObjectURL(url);
    }
    const shown = datasets.filter(d => (d.name + ' ' + d.source + ' ' + d.provider_id).toLowerCase().includes(search.toLowerCase()) && (category === 'All categories' || d.category === category) && (region === 'All regions' || d.region === region) && (source === 'All sources' || d.source === source) && (!onlyFav || favorites.includes(d.id)));
    function openDataset(id: string, mode?:Transformation) { setSelected([id]); setTransformations(mode?{[id]:mode}:{}); navigate('Investigate'); }
    return <div className="shell"><aside><a className="brand" href="#" onClick={() => navigate('Today')}><span className="brandmark"><ChartNoAxesCombined size={23}/></span>MacroLens<span className="version">2.0</span></a><nav>{tabs.map((name, i) => { const Icon = icons[i]; return <button key={name} className={tab === name ? 'active' : ''} onClick={() => navigate(name)}><Icon size={18}/>{name}{name === 'Ask MacroLens' && <span className="new">AI</span>}</button>; })}</nav></aside><div className="main"><header><div><Globe size={15}/> Global macro <ChevronRight size={13}/> <b>{tab}</b></div><span className="mock">REAL OBSERVATIONS · DELAYED</span></header><main><div className="page-heading"><div><div className="eyebrow">YOUR EDGE STARTS WITH CONTEXT</div><h1>{tab === 'Today' ? 'The macro picture. In focus.' : tab}</h1><p>{tab === 'Today' ? 'Follow the signals. Connect the dots. Discover what matters.' : tab === 'Investigate' ? 'Turn an observation into a deeper understanding.' : tab === 'Dataset Explorer' ? 'A world of economic data, ready to explore.' : tab === 'Ask MacroLens' ? 'Better questions. Deeper macro context.' : 'Your ideas, connected and collected.'}</p></div><span className="date">RESEARCH WORKSPACE<br /><b>{new Date().toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' })}</b></span></div>{notice && <div className="notice" role="status">{notice}<button onClick={() => setNotice('')}>Dismiss</button></div>}{error && <div className="notice" role="alert">{error} <button onClick={load}>Retry connection</button></div>}{loading && <p role="status" className="quiet">Retrieving source observations… providers may take a few seconds.</p>}
    {tab === 'Today' && <><div className="market-grid">{['sp500', 'gold', 'us10y', 'dxy', 'wti'].map(id => <MarketWidget key={id} id={id} dataset={datasets.find(d => d.id === id)} loading={loading} onOpen={() => openDataset(id)}/>)}</div><p className="quiet market-disclosure">Completed provider daily labels, excluding today (UTC). Delayed observations, not live quotes. Changes are relative to the previous available source observation; missing sessions may widen that interval. Gold GC=F and WTI CL=F are continuous futures, not spot prices.</p><div className="section-title"><h2><Compass size={18}/>Discovery Radar <span className="pill">PHASE 3</span></h2><span>Interesting moves. Worth a closer look.</span></div><div className="radar-grid">{[['POLICY DIVERGENCE', 'Policy paths in context'], ['INFLATION WATCH', 'The final mile of disinflation'], ['CROSS-ASSET SIGNAL', 'Relationships worth investigating']].map(r => <article className="card radar" key={r[0]}><div className="signal"><span />{r[0]}</div><h3>{r[1]}</h3><p>Signal detection is not active in Phase 2. Explore real observations in the research workspace.</p><div className="radar-footer"><small>Unavailable · Phase 3</small><button onClick={() => navigate('Investigate')}>Explore data <ChevronRight size={14}/></button></div></article>)}</div><div className="lower-grid"><section><div className="section-title"><h2>Economic pulse</h2><button onClick={() => navigate('Dataset Explorer')}>Explore datasets →</button></div><div className="indicator-grid">{['cpi_nsa', 'unemployment', 'fed_funds', 'payrolls', 'real_gdp_growth'].map(id => <EconomicWidget key={id} id={id} dataset={datasets.find(d => d.id === id)} onOpen={() => openDataset(id,datasets.find(d=>d.id===id)?.recommended_headline_transformation)}/>)}</div></section><section><div className="section-title"><h2>Research opportunities</h2></div><div className="card opportunities">{['Compare inflation and unemployment', 'Explore policy rates and Treasury yields', 'Review growth and labour data'].map((s, i) => <button key={s} onClick={() => { setSelected([['cpi', 'unemployment'], ['fed_funds', 'us10y'], ['real_gdp_growth', 'payrolls']][i]); setTransformations({}); navigate('Investigate'); }}><div>{s}<small>Research prompt · No inferred signal</small></div><ChevronRight size={16}/></button>)}</div></section></div></>}
    {tab === 'Investigate' && <><div className="toolbar"><div>{selected.map((id, i) => <button className="chip" key={id} onClick={() => toggle(id)}><i style={{ background: colors[i] }}/>{datasets.find(d => d.id === id)?.name || id} ×</button>)}</div><Button variant="outline" onClick={() => navigate('Dataset Explorer')}>+ Add dataset</Button><Button disabled={!comparison || comparing} onClick={save}><Bookmark size={15}/>Save investigation</Button></div><div className="card chart-card"><div className="chart-heading"><div><h2>{selected.length === 1 ? `${datasets.find(d => d.id === selected[0])?.name || selected[0]} — historical performance` : 'Historical comparison'}</h2><p>Source observations · Exact values in tooltips · No missing-data filling</p></div></div><div className="timeframe-bar"><span className="control-caption">Time range</span><div className="timeframe-options" role="group" aria-label="Historical timeframe">{TIMEFRAMES.map(r => <button key={r} aria-pressed={range === r} className={range === r ? 'chosen' : ''} onClick={() => preset(r)}>{r}</button>)}<button aria-pressed={range === 'Custom' || range === 'Saved'} className={range === 'Custom' || range === 'Saved' ? 'chosen' : ''} onClick={() => setRange('Custom')}>Custom</button></div><p className="selected-period">{dateLabel(start)} – {dateLabel(end)}{range === 'MAX' ? ' · MAX — retrieval limit: 1990 onward' : ''}</p></div>{(range === 'Custom' || range === 'Saved') && <div className="research-controls custom-dates"><label>From<input aria-label="Start date" type="date" min="1990-01-01" max={end} value={start} onChange={e => { setStart(e.target.value); setRange('Custom'); }}/></label><label>To<input aria-label="End date" type="date" min={start} max={yesterday()} value={end} onChange={e => { setEnd(e.target.value); setRange('Custom'); }}/></label></div>}<div className="transforms">{selected.map(id => { const d = datasets.find(d => d.id === id); return <label key={id}><span>Display · {d?.name || id}</span><select aria-label={`Transformation for ${id}`} value={transformations[id] || 'level'} onChange={e => setTransformations(t => ({ ...t, [id]: e.target.value as Transformation }))}>{(d?.allowed_transformations || ['level']).map(t => <option key={t} value={t}>{transformLabels[t]}</option>)}</select></label>; })}</div>{selected.length > 1 && <details className="advanced-analysis"><summary>Advanced Analysis</summary><div className="research-controls"><label>Frequency alignment<select aria-label="Frequency alignment" value={alignment} onChange={e => setAlignment(e.target.value as 'native' | 'period_end')}><option value="native">Native frequency (same frequency only)</option><option value="period_end">Explicit period-end last observation</option></select></label><label>Rolling correlation window<select aria-label="Rolling correlation window" value={rollingWindow} onChange={e => setRollingWindow(Number(e.target.value))}>{[6, 12, 24, 60].map(n => <option key={n} value={n}>{n} observations</option>)}</select></label></div><p>These settings affect statistical comparisons. Mixed frequencies require explicit alignment; missing observations are never filled.</p></details>}{comparing && <p role="status" className="quiet">Loading historical observations and calculating statistics…</p>}{compareError && <div className="notice" role="alert">{compareError}</div>}{!selected.length && <p>Select a dataset to begin your investigation.</p>}<div className="chart-series-grid">{comparison?.series.map((s, i) => <section key={s.id} className="series-panel"><div className="series-legend"><b><i style={{ background: colors[i] }}/>{s.name}</b><span>{s.units} · {transformLabels[s.transformation]}</span></div><div className="real-chart"><HistoryChart data={s.observations} units={s.units} color={colors[i]}/></div><div className="series-provenance">{comparison.datasets.find(d => d.id === s.id)?.source} · {comparison.datasets.find(d => d.id === s.id)?.frequency} · {freshness(comparison.datasets.find(d => d.id === s.id))}</div></section>)}</div>{comparison && <div className="table-bottom"><span>Charts use {comparison.alignment === 'native' ? 'native reference dates' : 'explicit common period-end labels'}.</span><Button variant="outline" onClick={download}><Download size={15}/>Download observations</Button></div>}</div><div className="insight-grid"><div className="card insight"><h3>Research context</h3>{comparison && <><p>Data facts describe the selected observations and transformations. Correlation does not establish causation.</p><details className="methodology-details"><summary>Methodology & limitations</summary>{comparison.warnings.map(w => <p key={w}>{w}</p>)}</details></>}{!comparison && <p>Sources and quality notes appear after a successful comparison.</p>}</div><div className="card insight"><h3>Statistical insights <span className="facts-label">DATA FACTS</span></h3>{comparison?.statistics.map((s, i) => <div key={i} className="stat"><b>{s.left} / {s.right}</b><p>Pearson r: {fmt(s.correlation)} · {s.observations} overlapping observations</p><p>{s.frequency} · {s.start} to {s.end}<br />{s.transformations.map(t => transformLabels[t]).join(' / ')}<br />{s.missing_periods} missing comparison periods · {s.alignment}</p><p>Latest complete {s.rolling_window}-period rolling r: {fmt([...s.rolling].reverse().find(o => o.value !== null)?.value ?? null)}</p><div className="rolling-chart"><HistoryChart data={s.rolling} units="Rolling Pearson correlation" color="#b49aff"/></div></div>)}{comparison?.series.map(s => { const values = s.observations.filter(o => o.value !== null); return <p key={s.id}>{s.name}: {values.length} usable observations; first {formatNumber(values[0]?.value ?? null)}, last {formatNumber(values.at(-1)?.value ?? null)} {s.units}.</p>; })}{!comparison?.statistics.length && <p>Select at least two compatible datasets for correlation.</p>}</div><div className="card insight"><h3>Research notes</h3><p className="note-caption">Your interpretation and hypotheses</p><textarea aria-label="Investigation notes" placeholder="What stands out? Capture a hypothesis…" value={note} onChange={e => setNote(e.target.value)}/><p>Saved locally as dataset references and settings. Data revisions may change results when reopened.</p>{comparison?.datasets.map(d => <div className="source-facts" key={d.id}><p><b>{d.name}</b><br />{referenceLabel(d)} · {freshness(d)}</p><DatasetMetadata dataset={d}/></div>)}</div></div></>}
    {tab === 'Dataset Explorer' && <><div className="toolbar filters"><label className="search"><Search size={17}/><input placeholder="Search datasets or sources…" aria-label="Search datasets" value={search} onChange={e => setSearch(e.target.value)}/></label>{[[category, setCategory, 'All categories', Array.from(new Set(datasets.map(d => d.category)))], [region, setRegion, 'All regions', Array.from(new Set(datasets.map(d => d.region)))], [source, setSource, 'All sources', Array.from(new Set(datasets.map(d => d.source)))]].map(([value, setter, label, options]) => <select key={String(label)} aria-label={String(label)} value={String(value)} onChange={e => (setter as (v: string) => void)(e.target.value)}><option>{String(label)}</option>{(options as string[]).map(o => <option key={o}>{o}</option>)}</select>)}<Button variant="outline" onClick={() => setOnlyFav(!onlyFav)}><Star size={15}/>{onlyFav ? 'Favourites only' : 'All datasets'}</Button><Button variant="outline" onClick={load} disabled={loading}>Refresh</Button></div><div className="card table-wrap"><table><thead><tr><th>Dataset / source</th><th>Category / region</th><th>Frequency / units</th><th>Latest reference</th><th>Favourite</th><th>Compare</th></tr></thead><tbody>{shown.map(d => <tr key={d.id}><td><b>{d.name}</b><small>{d.source}</small><DatasetMetadata dataset={d}/></td><td>{d.category}<small>{d.region}</small></td><td>{d.frequency}<small>{d.units}</small></td><td>{referenceLabel(d)}<small className={d.status === 'stale' ? 'freshness stale' : 'freshness'}>{freshness(d)}</small><b className="explorer-value" title={String(d.latest_value ?? '')}>{formatDatasetValue(d)}</b></td><td><button aria-label={`Favourite ${d.name}`} aria-pressed={favorites.includes(d.id)} onClick={() => favorite(d.id)}><Star size={17} fill={favorites.includes(d.id) ? '#edb867' : 'none'}/></button></td><td><input type="checkbox" aria-label={`Compare ${d.name}`} checked={selected.includes(d.id)} disabled={!selected.includes(d.id) && selected.length >= 4} onChange={() => toggle(d.id)}/></td></tr>)}</tbody></table>{!loading && !shown.length && <p className="quiet">No datasets match your filters.</p>}<div className="table-bottom">{selected.length}/4 datasets selected<Button disabled={!selected.length} onClick={() => navigate('Investigate')}>Compare selected <ArrowUpRight size={15}/></Button></div></div></>}
    {tab === 'Ask MacroLens' && <div className="ask-layout"><div className="card ask-card"><span className="ai-orb"><Sparkles size={28}/></span><h2>What are you curious about?</h2><p>Explore the connections behind the macro picture.</p><div className="suggestions">{['Is inflation cooling faster than expected?', 'How do interest rates influence equities?', 'What is the outlook for US growth?'].map(q => <button key={q} onClick={() => setQuestion(q)}>{q}<ArrowUpRight size={15}/></button>)}</div><form onSubmit={e => e.preventDefault()}><textarea aria-label="Research question" value={question} onChange={e => setQuestion(e.target.value)} placeholder="Ask a macroeconomic research question…"/><Button disabled type="submit">Available in Phase 3</Button></form><small>NOT LIVE IN PHASE 2 · No AI requests are sent</small></div><div className="card insight"><h3><Sparkles size={16}/> Research with context</h3><p>The existing Ask backend is preserved for Phase 3. Explore actual observations and descriptive statistics in Investigate.</p></div></div>}
    {tab === 'My Research' && <><div className="toolbar"><label className="search"><Search size={17}/><input aria-label="Search saved research" placeholder="Search your investigations…" value={search} onChange={e => setSearch(e.target.value)}/></label><select aria-label="Collection" value={collection} onChange={e => setCollection(e.target.value)}><option>All collections</option><option>Macro outlook</option></select><Button onClick={() => navigate('Investigate')}>+ New investigation</Button></div>{!saved.length ? <div className="card empty"><Bookmark size={32}/><h2>Your next insight starts here.</h2><p>Save an investigation to collect charts, comparisons and notes in this workspace.</p><Button onClick={() => navigate('Investigate')}>Start investigating</Button></div> : <div className="research-grid">{saved.filter(s => (s.title + ' ' + s.note).toLowerCase().includes(search.toLowerCase()) && (collection === 'All collections' || s.collection === collection)).map(s => <article className="card insight" key={s.id}><span className="eyebrow">{s.collection}</span><h3>{s.title}</h3><p>{s.note || 'No research notes yet.'}</p><p>{s.version === 2 ? `${s.start} to ${s.end} · References only; observations refresh on reopen.` : 'Phase 1 prototype note — preserved. Mock dataset IDs are not automatically mapped to real data.'}</p><Button variant="outline" onClick={() => {
                        setNote(s.note);
                        if (s.version === 2) {
                            setSelected(s.datasets);
                            setTransformations(s.transformations || {});
                            setStart(s.start!);
                            setEnd(s.end!);
                            setAlignment(s.alignment || 'native');
                            setRollingWindow(s.rolling_window || 12);
                            setRange('Saved');
                            navigate('Investigate');
                        }
                        else {
                            setNotice('Prototype note loaded. Choose real datasets to create a new investigation; the original note remains saved.');
                            navigate('Investigate');
                        }
                    }}>Open investigation <ArrowUpRight size={15}/></Button></article>)}</div>}</>}
    <footer><span><span className="footer-dot"/>MacroLens Research</span><span>Phase 2 · Real observations · Latest revisions · No causal claims</span><span>Built for the bigger picture.</span></footer></main></div></div>;
}
