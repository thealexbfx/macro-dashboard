import {readFile, mkdir, writeFile} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import {join} from 'node:path';
import {setTimeout as sleep} from 'node:timers/promises';
import {verifyStatcan} from './statcan.mjs';
import {verifyBls} from './bls.mjs';
import {verifyEcb} from './ecb.mjs';
import {verifyOns, verifyBoe} from './uk.mjs';
import {verifyTreasury} from './treasury.mjs';
import {getSeriesSpec, validateManifestRegistry} from './series-registry.mjs';

const euroPolicy = new Set(['G7-DE-22', 'G7-FR-22', 'G7-IT-22']);

export function parseManifest(csv) {
  const [header, ...lines] = csv.trim().split(/\r?\n/);
  const keys = header.split(',');
  const rows = lines.map(line => {
    const fields = [...line.matchAll(/(?:^|,)("(?:[^"]|"")*"|[^,\r\n]*)/g)]
      .map(([, value]) => value.startsWith('"') ? value.slice(1, -1).replaceAll('""', '"') : value);
    if (fields.length !== keys.length) throw new Error('Malformed manifest row');
    return Object.fromEntries(keys.map((key, i) => [key, fields[i]]));
  });
  const expected = new Set(['US', 'GB', 'DE', 'FR', 'IT', 'CA', 'JP'].flatMap(
    country => ['01', '07', '11', '22', '23'].map(concept => 'G7-' + country + '-' + concept)));
  const seen = new Set();
  if (![35, 245].includes(rows.length) || rows.some(row =>
    !/^G7-(US|GB|DE|FR|IT|CA|JP)-(0[1-9]|[12][0-9]|3[0-5])$/.test(row.mapping_id) ||
    seen.has(row.mapping_id) || (seen.add(row.mapping_id), false) ||
    row.operational_outcome !== 'NOT_TESTED') ||
    [...expected].some(id => !seen.has(id))) {
    throw new Error('Unexpected G7 manifest mappings, count or seed statuses');
  }
  return rows;
}

const limit = 65536;
async function boundedJson(response) {
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let size = 0;
  let body = '';
  try {
    while (true) {
      const {value, done} = await reader.read();
      if (done) return JSON.parse(body + decoder.decode());
      size += value.byteLength;
      if (size > limit) throw new RangeError('response_too_large');
      body += decoder.decode(value, {stream: true});
    }
  } finally {
    await reader.cancel().catch(() => {});
  }
}

async function request(url, transport, delay) {
  for (let attempt = 1; attempt <= 3; attempt++) {
    await delay(attempt * 1000);
    let response;
    try {
      response = await transport(url, {
        method: 'GET', redirect: 'error', signal: AbortSignal.timeout(8000),
        headers: {accept: 'application/json'},
      });
    } catch {
      if (attempt < 3) continue;
      return {http_status: null, error: 'network_or_timeout', attempt};
    }
    const receipt = {http_status: response.status, attempt, retrieved_utc: new Date().toISOString()};
    if (!response.ok) {
      await response.body?.cancel().catch(() => {});
      if (attempt < 3 && (response.status === 429 || response.status >= 500)) continue;
      return {...receipt, error: 'http_' + response.status};
    }
    try {
      return {...receipt, payload: await boundedJson(response)};
    } catch (error) {
      if (error instanceof SyntaxError) return {...receipt, error: 'invalid_json'};
      if (error instanceof RangeError) return {...receipt, error: 'response_too_large'};
      if (attempt === 3) return {...receipt, error: 'body_read_failed'};
    }
  }
}

export async function verify(row, transport = fetch, delay = sleep) {
  const id = row.mapping_id;
  const shared = euroPolicy.has(id);
  const spec = getSeriesSpec(id);
  const series = spec?.adapter === 'boc-valet' ? spec.seriesId : null;
  const expectedLabel = series ? new RegExp(spec.expectedLabel, 'i') : null;
  const url = series ? 'https://www.bankofcanada.ca/valet/observations/' + series + '/json?recent=5' : null;
  const result = {
    mapping_id: id, publisher: row.proposed_original_publisher,
    canonical_series_key: shared ? 'ECB-POLICY-RATE' : id,
    source_url: url, publisher_discovery_url: row.publisher_discovery_url || null,
    publisher_series_id: series ?? null, definition: null, frequency: null, unit: null,
    seasonal_adjustment: null, first_evidenced: null, last_evidenced: null,
    check_utc: new Date().toISOString(), http_status: null, observations: [], metadata: null,
    outcome: 'UNRESOLVED', verification_scope: 'NONE', production_approval: 'NOT_APPROVED', identity_status: 'UNRESOLVED', access_status: 'NOT_TESTED',
    history_status: 'NOT_ESTABLISHED', vintage_status: 'NOT_ESTABLISHED',
    rights_status: 'PENDING', comparability: row.comparability,
    mismatch_notes: null, review_note: row.review_note,
    error_category: 'missing_exact_identifier',
    rights_note: id.endsWith('-23') ? 'Review yield methodology, market data provenance and commercial display/export rights.' :
      'Source-specific commercial display and export review pending.',
  };
  if (spec?.adapter === 'statcan-wds') return verifyStatcan(row, result, spec, transport, delay);
  if (spec?.adapter === 'bls-v1') return verifyBls(row, result, spec, transport, delay);
  if (spec?.adapter === 'ecb-csv') return verifyEcb(row, result, spec, transport, delay);
  if (spec?.adapter === 'ons-timeseries') return verifyOns(row, result, spec, transport, delay);
  if (spec?.adapter === 'boe-iadb') return verifyBoe(row, result, spec, transport, delay);
  if (spec?.adapter === 'us-treasury-xml') return verifyTreasury(row, result, spec, transport, delay);
  if (!url) return result;

  const {payload, error, ...receipt} = await request(url, transport, delay);
  Object.assign(result, receipt);
  if (error) {
    const invalid = error === 'invalid_json';
    return {...result, outcome: invalid ? 'UNRESOLVED' : 'ACCESS_BLOCKED',
      access_status: invalid ? 'RETRIEVED' : 'BLOCKED', error_category: error};
  }
  result.access_status = 'RETRIEVED';
  const metadata = payload?.seriesDetail?.[series];
  if (typeof metadata?.label !== 'string' || !metadata.label.trim() || !Array.isArray(payload?.observations)) {
    return {...result, error_category: 'malformed_payload'};
  }
  if (!expectedLabel.test(metadata.label)) {
    return {...result, outcome: 'MISMATCH', error_category: 'invalid_metadata',
      identity_status: 'MISMATCH', mismatch_notes: 'Expected series key and publisher label were not evidenced.'};
  }
  const clean = value => typeof value === 'string' ? value.replace(/[\x00-\x1f\x7f]/g, ' ').slice(0, 240) : null;
  result.metadata = {label: clean(metadata.label), description: clean(metadata.description)};
  result.definition = result.metadata.description || result.metadata.label;
  result.identity_status = 'MATCHED';
  const observations = payload.observations.flatMap(item => {
    const value = item?.[series]?.v;
    return typeof item?.d === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(item.d) &&
      typeof value === 'string' && /^-?\d+(\.\d+)?$/.test(value) && value.length <= 24
      ? [{period: item.d, value}] : [];
  }).sort((a, b) => a.period.localeCompare(b.period));
  if (!observations.length) return {...result, error_category: 'no_usable_observations'};

  return {...result, outcome: 'VERIFIED', verification_scope: 'RECENT_SAMPLE_ONLY', observations: observations.slice(-5),
    first_evidenced: observations.at(-5)?.period ?? observations[0].period,
    last_evidenced: observations.at(-1).period, history_status: 'SAMPLE_ONLY',
    frequency: 'Daily', error_category: null};
}

async function main(out) {
  if (!out) throw new Error('Supply a disposable output directory');
  const manifestPath = process.argv[3] || new URL('manifest.csv', import.meta.url);
  const rows = parseManifest(await readFile(manifestPath, 'utf8'));
  const registry = validateManifestRegistry(rows);
  const records = [];
  for (const row of rows) records.push(await verify(row));
  for (const row of records.filter(record => record.source_url)) {
    console.log(JSON.stringify({mapping_id: row.mapping_id, outcome: row.outcome,
      http_status: row.http_status, error_category: row.error_category}));
  }
  const fields = [...new Set(records.flatMap(Object.keys))];
  const cell = value => '"' + (value == null ? '' : typeof value === 'object' ? JSON.stringify(value) :
    String(value)).replaceAll('"', '""') + '"';
  const matrix = [fields.join(','), ...records.map(row => fields.map(key => cell(row[key])).join(','))];
  const summary = ['# G7 Core Batch 1 verification', '',
    'Mappings: ' + registry.manifest_count + ' | Configured: ' + registry.configured_count + ' | Unconfigured: ' + registry.unconfigured_count, '' ,
    'VERIFIED records establish publisher identity and retrieval of a bounded recent sample only. Full historical coverage and release vintages are unconfirmed. Commercial rights remain pending and production approval has not been granted.',
    '', '| Mapping | Publisher | Outcome | HTTP | Error | Rights |',
    '| --- | --- | --- | --- | --- | --- |',
    ...records.map(r => '| ' + [r.mapping_id, r.publisher, r.outcome, r.http_status ?? '-',
      r.error_category ?? '-', r.rights_status].join(' | ') + ' |'), ''];
  await mkdir(out, {recursive: true});
  await Promise.all([
    writeFile(join(out, 'g7_core_batch1_verification.json'), JSON.stringify(records, null, 2) + '\n'),
    writeFile(join(out, 'g7_core_batch1_matrix.csv'), matrix.join('\n') + '\n'),
    writeFile(join(out, 'G7_CORE_BATCH1_SUMMARY.md'), summary.join('\n')),
  ]);
}

if (process.argv[1] === fileURLToPath(import.meta.url)) await main(process.argv[2]);
