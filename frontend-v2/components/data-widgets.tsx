'use client';
import { Area, AreaChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { ArrowUpRight } from 'lucide-react';
import type { Dataset } from '../lib/contracts';
import { dateLabel, formatDatasetValue, formatNumber, freshness, marketMovement, recentObservations, referenceLabel } from '../lib/presentation';
export function DatasetMetadata({ dataset: d }: {
    dataset: Dataset;
}) { return <details className="dataset-metadata"><summary>Source & methodology</summary><div><a href={d.source_url} target="_blank" rel="noreferrer">{d.source} · {d.provider_id} ↗</a><dl><dt>Exact latest source value</dt><dd>{d.latest_value === null ? 'Unavailable' : String(d.latest_value)}</dd><dt>Latest reference</dt><dd>{d.latest_observation_date || 'Unavailable'}</dd><dt>Previous observation</dt><dd>{dateLabel(d.previous_observation_date)}</dd><dt>Units</dt><dd>{d.units}</dd><dt>Frequency</dt><dd>{d.frequency}</dd><dt>Adjustment</dt><dd>{d.seasonal_adjustment || 'Not supplied by provider'}</dd><dt>Definition</dt><dd>{d.original_transformation}</dd><dt>Retrieved coverage</dt><dd>{d.coverage_start || 'Unknown'}–{d.coverage_end || 'Unknown'}</dd><dt>Retrieved at</dt><dd>{d.retrieved_at || 'Never'}</dd><dt>Publication date</dt><dd>{d.publication_date || 'Unavailable; reference dates are not release dates'}</dd></dl><p>{d.message}</p></div></details>; }
export function MarketWidget({ dataset: d, id, loading, onOpen }: {
    dataset: Dataset | undefined;
    id: string;
    loading: boolean;
    onOpen: () => void;
}) {
    const name = d?.name.replace(' — continuous futures', '') || ({ sp500: 'S&P 500', gold: 'Gold', us10y: 'US 10Y Treasury', dxy: 'US Dollar Index', wti: 'WTI crude oil' }[id]);
    const move = d ? marketMovement(d) : { value: null, unit: '%', label: 'Change unavailable' };
    const tone = move.value === null || move.value === 0 ? 'neutral' : move.value > 0 ? 'positive' : 'negative';
    const color = tone === 'negative' ? '#eb8294' : tone === 'positive' ? '#4ed4b1' : '#7c9fca';
    const state = loading && !d ? 'Loading…' : freshness(d);
    const rows = d ? recentObservations(d) : [];
    return <article className={`card market-widget ${d?.status === 'stale' ? 'is-stale' : ''}`} aria-label={`${name} market widget`}><button className="market-open" onClick={onOpen}><div className="widget-title"><span>{name}</span><ArrowUpRight size={16}/></div><span className="instrument-type">{id === 'gold' || id === 'wti' ? 'Continuous futures · not spot' : id === 'us10y' ? 'Constant-maturity yield' : 'Price index · daily close'}</span><strong title={d?.latest_value === null ? '' : String(d?.latest_value ?? '')}>{d ? formatDatasetValue(d) : loading ? 'Loading…' : 'Unavailable'}</strong><span className={`widget-move ${tone}`}>{move.value === null ? 'Change unavailable' : `${move.value > 0 ? '+' : ''}${formatNumber(move.value)}${move.unit === '%' ? '%' : ` ${move.unit}`}`}</span><span className="move-context">{d?.representation === 'rate' ? 'Yield change · not a bond return' : move.label.startsWith('Absolute') ? move.label : 'vs previous available close'}</span><div className="widget-spark" aria-label="Recent source observations">{rows.length > 0 && <ResponsiveContainer width="100%" height="100%"><AreaChart data={rows}><XAxis hide dataKey="date"/><YAxis hide domain={['auto', 'auto']}/><Tooltip labelFormatter={v => dateLabel(String(v))} formatter={v => [String(v), d?.units]} contentStyle={{ background: '#101c30', border: '1px solid #30415c', borderRadius: 6, fontSize: 13 }}/><Area dataKey="value" type="linear" isAnimationActive={false} stroke={color} fill={color} fillOpacity={.08} strokeWidth={1.8} connectNulls={false}/></AreaChart></ResponsiveContainer>}</div><span className="widget-date">{dateLabel(d?.latest_observation_date)}</span><span className={`freshness ${d?.status === 'stale' ? 'stale' : ''}`}>{state}</span></button>{d && <><div className="widget-source">{d.source}</div><DatasetMetadata dataset={d}/><span className="sr-only">Previous source observation {d.previous_observation_date}; {d.units}</span></>}</article>;
}
export function EconomicWidget({ dataset: d, id, onOpen }: {
    dataset: Dataset | undefined;
    id: string;
    onOpen: () => void;
}) { return <article className="card indicator economic-widget"><button className="economic-open" onClick={onOpen}><div className="card-label">{d?.name || id}</div><strong title={String(d?.latest_value ?? '')}>{d ? formatDatasetValue(d) : 'Loading…'}</strong><span className="economic-unit">{d?.units || 'Loading metadata…'}</span><div className="economic-reference">{d ? referenceLabel(d) : 'Reference unavailable'} · {d?.frequency || 'Pending'}</div><span className={d?.status === 'stale' ? 'freshness stale' : 'freshness'}>{freshness(d)}</span></button><div className="widget-source">{d?.source || 'Retrieving source'}</div>{d && <DatasetMetadata dataset={d}/>}</article>; }
