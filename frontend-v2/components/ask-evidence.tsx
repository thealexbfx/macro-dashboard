'use client';

import {useEffect, useRef, useState} from 'react';
import {request, type Dataset} from '../lib/contracts';
import {relativeChange, summarizeObservations} from '../lib/ask-evidence';

type Preview = {dataset: Dataset};
// A client-side precaution, not a commercial-use licence or server-side rights gate.
const eligible = (dataset: Dataset) => !/yahoo|yfinance/i.test(
    [dataset.source, dataset.provider, dataset.source_url, dataset.primary_source_url].join(' ')
) && dataset.release_metadata?.source_error_code !== 'market_source_rights_pending';

export function AskEvidence({datasets, onBrowse}: {datasets: Dataset[]; onBrowse: () => void}) {
    const [id, setId] = useState('');
    const [mode, setMode] = useState<'difference' | 'percent'>('difference');
    const [result, setResult] = useState<Preview | null>(null);
    const [pending, setPending] = useState(false);
    const [error, setError] = useState('');
    const active = useRef<AbortController | null>(null);
    useEffect(() => () => active.current?.abort(), []);

    async function calculate() {
        if (!datasets.some(dataset => dataset.id === id && eligible(dataset))) return;
        active.current?.abort();
        const controller = new AbortController();
        active.current = controller;
        setPending(true);
        setError('');
        setResult(null);
        try {
            const data = await request<Preview>(`observations/${encodeURIComponent(id)}?preview=true&limit=40`, undefined, controller.signal);
            if (!controller.signal.aborted) {
                if (data.dataset.id !== id || !eligible(data.dataset)) throw Error('Dataset identity or source eligibility mismatch');
                setResult(data);
            }
        } catch {
            if (!controller.signal.aborted) setError('Evidence is unavailable for this dataset. Try again or choose another dataset.');
        } finally {
            if (!controller.signal.aborted) setPending(false);
        }
    }

    const evidence = result && summarizeObservations(result.dataset.observations ?? []);
    const percent = evidence && relativeChange(evidence);
    const selected = datasets.find(dataset => dataset.id === id);
    const supportsPercent = (dataset: Dataset | undefined) =>
        dataset?.allowed_transformations.includes('percent') === true;
    const sourceUrl = result?.dataset.primary_source_url || result?.dataset.source_url;
    return <section className="ml-surface">
        <h1>Ask MacroLens</h1>
        <p>What changed between the two most recent usable observations?</p>
        <form onSubmit={event => {event.preventDefault(); if (id) void calculate();}}>
            <label htmlFor="ask-dataset">Dataset</label>{' '}
            <select id="ask-dataset" value={id} onChange={event => {
                active.current?.abort();
                setId(event.target.value); setMode('difference'); setResult(null); setError(''); setPending(false);
            }}>
                <option value="">Choose a dataset</option>
                {datasets.filter(eligible).map(dataset => <option key={dataset.id} value={dataset.id}>{dataset.name}</option>)}
            </select>{' '}
            <label htmlFor="ask-calculation">Calculation</label>{' '}
            <select id="ask-calculation" value={mode} onChange={event =>
                setMode(event.target.value === 'percent' ? 'percent' : 'difference')
            }>
                <option value="difference">Difference in source units</option>
                {supportsPercent(selected) && <option value="percent">Relative percentage change</option>}
            </select>{' '}
            <button type="submit" disabled={!id || pending}>{pending ? 'Retrieving evidence…' : 'Show evidence'}</button>
        </form>
        <button type="button" onClick={onBrowse}>Browse the data library</button>
        <div aria-live="polite">
            {error && <p>{error}</p>}
            {result && !evidence && <p>Two distinct, finite observations are required in the returned preview.</p>}
            {result && evidence && <>
                <h2>{result.dataset.name}</h2>
                <p>{evidence.latest.date} · {evidence.latest.value} {result.dataset.units}</p>
                <p>{evidence.previous.date} · {evidence.previous.value} {result.dataset.units}</p>
                {mode === 'difference' ? (
                    <p>Change = {evidence.latest.value} − {evidence.previous.value} = {Number(evidence.change.toPrecision(8))} in source units.</p>
                ) : percent === null || !supportsPercent(result.dataset) ? (
                    <p>Relative change requires two positive values from a dataset that supports percentage change.</p>
                ) : (
                    <p>Relative change = (({evidence.latest.value} − {evidence.previous.value}) ÷ {evidence.previous.value}) × 100 = {Number(percent.toPrecision(8))}%.</p>
                )}
                <p>Dataset {result.dataset.id} · {result.dataset.source} · {result.dataset.status}</p>
                {result.dataset.message && <p>{result.dataset.message}</p>}
                {sourceUrl && /^https?:\/\//i.test(sourceUrl) && <p><a href={sourceUrl}>Source for {result.dataset.name}</a></p>}
                <p>Missing values were skipped. The dates can span more than one reporting period. These observations alone cannot establish a cause.</p>
            </>}
        </div>
    </section>;
}
