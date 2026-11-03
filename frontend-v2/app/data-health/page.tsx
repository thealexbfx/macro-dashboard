'use client';

import { useState } from 'react';
import Link from 'next/link';
import { displayTime, healthLabel, type DataHealth } from '../../lib/data-health';

export default function DataHealthPage() {
  const [token, setToken] = useState('');
  const [report, setReport] = useState<DataHealth | null>(null);
  const [offset, setOffset] = useState(0);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  async function load(next = 0) {
    setLoading(true); setError('');
    try {
      const response = await fetch(`/api/v2/discovery/admin/data-health?offset=${next}&limit=100`, {
        headers: { Authorization: `Bearer ${token}` }, cache: 'no-store',
        referrerPolicy: 'no-referrer', signal: AbortSignal.timeout(30000),
      });
      if (!response.ok) throw new Error(response.status === 403 ? 'Administrator access required.' : 'Report unavailable. Existing data is preserved.');
      setReport(await response.json()); setOffset(next);
    } catch (cause) { setReport(null); setError(cause instanceof Error ? cause.message : 'Unable to load the report.'); }
    finally { setLoading(false); }
  }
  return <main style={{ maxWidth: 1400, margin: '0 auto', padding: 24 }}>
    <Link href="/">← MacroLens</Link>
    <h1>Data health</h1>
    <p>Administrator report. Source checks, observation dates and publication dates are distinct.</p>
    <form onSubmit={event => { event.preventDefault(); void load(); }} style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginBottom: 24 }}>
      <label>Administrator token <input aria-label="Administrator token" type="password" autoComplete="off" value={token} onChange={e => setToken(e.target.value)} /></label>
      <button disabled={loading || !token} type="submit">{loading ? 'Checking…' : 'Refresh report'}</button>
      <button type="button" onClick={() => { setToken(''); setReport(null); setError(''); }}>Lock report</button>
    </form>
    <p>The token stays in this page’s memory only. This report does not run ingestion or change permissions.</p>
    {error && <p role="alert">{error}</p>}
    {report && <>
      <p>Report checked: {displayTime(report.as_of)}</p>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 24, margin: '24px 0' }}>
        <div>Public datasets<strong style={{ display: 'block', fontSize: 28 }}>{report.summary.public}</strong></div>
        <div>Active automatic refresh<strong style={{ display: 'block', fontSize: 28 }}>{report.summary.automatic_refresh}/{report.summary.public}</strong></div>
        <div>Verified successful checks<strong style={{ display: 'block', fontSize: 28 }}>{report.summary.verified_automatic_refresh}</strong></div>
        <div>Healthy<strong style={{ display: 'block', fontSize: 28 }}>{report.summary.healthy}</strong></div>
        <div>Needs attention<strong style={{ display: 'block', fontSize: 28 }}>{report.summary.needs_attention}</strong></div>
      </div>
      <p>SQLite and journal: {(Object.values(report.resources.sqlite_bytes).reduce((a, b) => a + b, 0) / 1048576).toFixed(1)} MiB · Free disk: {(report.resources.free_disk_bytes / 1048576).toFixed(1)} MiB · {report.resources.disk_attention ? 'Review disk headroom' : 'Disk reserve available'}</p>
      <p>Cgroup memory: {report.resources['memory.current'] && report.resources['memory.max'] ? `${(Number(report.resources['memory.current']) / 1048576).toFixed(1)} MiB including file cache / ${(Number(report.resources['memory.max']) / 1048576).toFixed(0)} MiB limit` : 'Unavailable in this environment'}</p>
      <div style={{ overflowX: 'auto' }}><table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 14 }}>
        <thead><tr>{['Dataset', 'Status', 'Latest observation', 'Frequency', 'Last successful check', 'Next check'].map(label => <th key={label} style={{ textAlign: 'left', padding: 10 }}>{label}</th>)}</tr></thead>
        <tbody>{report.items.map(row => <tr key={row.id} style={{ borderTop: '1px solid #263a50' }}>
          <td style={{ padding: 10 }}>{row.name}<br /><small>{row.provider} · {row.id}</small></td>
          <td>{healthLabel(row.health)}{row.error_code && <div>{row.error_code} · {row.failures} failures</div>}</td>
          <td>{row.latest_observation_date || 'Not recorded'}</td><td>{row.frequency}</td>
          <td>{displayTime(row.last_success)}</td><td>{displayTime(row.next_check)}</td>
        </tr>)}</tbody>
      </table></div>
      <p>Showing {offset + 1}–{Math.min(offset + report.items.length, report.total)} of {report.total}</p>
      <button disabled={loading || offset === 0} onClick={() => void load(Math.max(0, offset - 100))}>Previous</button>{' '}
      <button disabled={loading || report.next_offset === null} onClick={() => void load(report.next_offset ?? 0)}>Next</button>
      <p>A source-lag warning calls for review; it does not claim that an unreleased economic observation is missing. Source failures retain last-good public data.</p>
    </>}
  </main>;
}
