// Development-only audit of original BOJ decisions.
import {createHash} from 'node:crypto';
import {readFile, mkdir, writeFile} from 'node:fs/promises';
import {join, resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
import {setTimeout as sleep} from 'node:timers/promises';
import {pdfToText} from './boj-2026-pdf.mjs';

const origin = 'https://www.boj.or.jp/en/mopo/mpmdeci/';
const cutoff = '2026-10-30';
const maxBytes = 1024 * 1024;
const manifest = JSON.parse(await readFile(new URL('./boj-historical-sources.json', import.meta.url)));
const dateWords = date => new Date(date + 'T00:00:00Z').toLocaleDateString('en-US', {
  month: 'long', day: 'numeric', year: 'numeric', timeZone: 'UTC',
});
const clean = text => text.normalize('NFKC')
  .replace(/[‐‑–−]/g, '-').replace(/\s+/g, ' ').trim();
const escape = text => text.replace(/[.*+?^$()[\]{}|\\]/g, '\\$&');
const number = String.raw`(\d{1,3}(?:\.\d{1,4})?)`;
const overnight = 'uncollateralized overnight call rate';
const callPrefix = String.raw`\b(?:The Bank(?: of Japan)? will encourage|Encourage) the ${overnight} to `;
const callPattern = new RegExp(callPrefix +
  String.raw`(?:remain at|move on average) around ${number}(?:\s+to\s+${number})?\s*(?:percent\b|%)`, 'g');
const reservePattern = /(?:aiming (?:for |at )?the outstanding balance of (?:the )?current accounts (?:held )?at the Bank at|(?:raised from around \d+ trillion yen to)) around (\d+)(?: to (\d+))? trillion yen/gi;
const basePattern = /the monetary base will increase at an annual pace of about (\d+)(?:\s*-\s*(\d+))? trillion yen/gi;
const negativePattern = /The Bank will apply a negative interest rate of minus (\d+(?:\.\d+)?) percent to (?:the(?: \d+)? Policy-Rate Balances|current accounts that financial institutions hold at the Bank)/gi;
const yccPattern = /10-year JGB yields will remain (?:more or less at the current level \(around zero percent\)|at around zero percent)/gi;
const percentage = 'percent_per_annum';

function uniqueMatch(text, pattern, parse) {
  const values = [...text.matchAll(pattern)].map(parse);
  const distinct = new Map(values.map(value => [JSON.stringify(value), value]));
  return distinct.size === 1 ? distinct.values().next().value : undefined;
}
const asNumberOrRange = ([, lower, upper]) => upper === undefined ? Number(lower) : [Number(lower), Number(upper)];

function target(instrument, value, unit, qualifier) {
  return {
    instrument, unit, qualifier,
    value: typeof value === 'number' ? value : null,
    lower: Array.isArray(value) ? value[0] : null,
    upper: Array.isArray(value) ? value[1] : null,
  };
}

function effectiveEvidence(text, date, rule) {
  if (rule === 'negative') {
    return uniqueMatch(text, /A negative interest rate of minus 0\.1 percent will be effective from the reserve maintenance period, which commences from ([A-Za-z]+)\s*(\d{1,2}), (20\d{2})\./gi,
      ([, month, day, year]) => [month + ' ' + day + ', ' + year, 'RESERVE_MAINTENANCE_FOOTNOTE']);
  }
  if (date === '2010-10-05' && /around 0 to 0\.1 percent,\s*\d*\s*effective immediately\b/i.test(text)) {
    return [dateWords(date), 'EXPLICIT_IMMEDIATE_EFFECT'];
  }
  return uniqueMatch(text,
    /The new guideline for (?:money )?market operations(?: and the new interest rate on the current account balances)? will be effective from ([A-Za-z]+ \d{1,2}, 20\d{2})\./gi,
    ([, label]) => [label, 'GUIDELINE_EFFECTIVE_DATE_FOOTNOTE']);
}

function htmlText(html) {
  return clean(html
    .replace(/<!--[\s\S]*?-->/g, ' ')
    .replace(/<(script|style|template)\b[^>]*>[\s\S]*?<\/\1\s*>/gi, ' ')
    .replace(/<[^>]*>/g, ' ')
    .replace(/&(nbsp|quot|ldquo|rdquo|ndash|mdash|amp|#39|#160);/gi, (_, key) =>
      ({nbsp:' ',quot:'"',ldquo:'"',rdquo:'"',ndash:'-',mdash:'-',amp:'&','#39':"'",'#160':' '})[key.toLowerCase()]));
}

const unresolved = reason => ({
  verification_status: 'UNRESOLVED', reason, targets: [],
  effective_date: null, effective_date_status: 'UNRESOLVED', publication_date: null,
});

export function parseDecision(raw, row) {
  const [date, file, , rule, expected, effective, title] = row;
  const pdf = file.endsWith('.pdf');
  const header = pdf
    ? new RegExp('^\\s*(?:1\\s+)?' + escape(dateWords(date)) + ' Bank of Japan ' + escape(title) + '(?= |$)')
    : new RegExp('^' + escape(title) + ' ' + escape(dateWords(date)) + ' Bank of Japan(?= |$)');
  const markup = pdf ? null : raw.replace(/<!--[^]*?-->|<(script|style|template)\b[^>]*>[^]*?<\/\1\s*>/gi, ' ');
  const content = pdf ? raw : markup.match(/<h1\b[^>]*>[\s\S]*?(?=<\/main\b|<footer\b|$)/i)?.[0];
  if (!content) return unresolved('document_identity_or_decision_date_unproven');
  const text = (pdf ? clean(content) : htmlText(content)).replace(/[“”]/g, '"');
  // Normalize the publisher's typographic quotation marks consistently.
  if (!header.test(text)) return unresolved('document_identity_or_decision_date_unproven');

  let parsed;
  let targets;
  if (rule === 'call') {
    parsed = uniqueMatch(text, callPattern, asNumberOrRange);
    targets = [target('OVERNIGHT_CALL_RATE', parsed, percentage, 'AROUND')];
  } else if (rule === 'zirp') {
    const low = new RegExp(callPrefix + 'move as low as possible', 'i').test(text);
    const initial = uniqueMatch(text, /initially aim to guide the above call rate to move around (\d+\.\d+)\s*%/gi, asNumberOrRange);
    if (low) parsed = initial;
    targets = [
      target('OVERNIGHT_CALL_RATE', null, null, 'AS_LOW_AS_POSSIBLE'),
      target('OVERNIGHT_CALL_RATE', initial, percentage, 'INITIAL_GUIDANCE_ONLY'),
    ];
  } else if (rule === 'zero') {
    if (new RegExp(callPrefix + 'remain at effectively zero percent', 'i').test(text)) parsed = 0;
    targets = [target('OVERNIGHT_CALL_RATE', parsed, percentage, 'EFFECTIVELY_ZERO')];
  } else if (rule === 'reserves') {
    parsed = uniqueMatch(text, reservePattern, asNumberOrRange);
    targets = [target('BOJ_CURRENT_ACCOUNT_BALANCES', parsed, 'trillion_jpy', 'AROUND')];
  } else if (rule === 'reserve_floor') {
    parsed = uniqueMatch(text, /outstanding balance of current accounts held at the Bank at above (\d+) trillion yen/gi, asNumberOrRange);
    targets = [target('BOJ_CURRENT_ACCOUNT_BALANCES', parsed, 'trillion_jpy', 'ABOVE')];
  } else if (rule === 'base') {
    parsed = uniqueMatch(text, basePattern, asNumberOrRange);
    targets = [target('MONETARY_BASE_ANNUAL_GROWTH', parsed, 'trillion_jpy_per_year', 'AROUND')];
  } else if (rule === 'negative' || rule.startsWith('ycc')) {
    const rate = uniqueMatch(text, negativePattern, ([, value]) => -Number(value));
    targets = [target('BOJ_POLICY_RATE_BALANCES', rate, percentage, 'APPLIED_RATE')];
    if (rule === 'negative') parsed = rate;
    if (rule.startsWith('ycc') && rate !== undefined && [...text.matchAll(yccPattern)].length) {
      parsed = [rate, 0];
      targets.push(target('JGB_10Y_YIELD_TARGET', 0, percentage, 'AROUND'));
      if (rule === 'ycc_band' || rule === 'ycc_flex') {
        const pattern = rule === 'ycc_band'
          ? /to between around plus and minus (\d+(?:\.\d+)?) percentage points/gi
          : /range of around plus and minus (\d+(?:\.\d+)?) percentage points from the target level, while it will conduct yield curve control with greater flexibility, regarding the upper and lower bounds of the range as references/gi;
        const band = uniqueMatch(text, pattern, asNumberOrRange);
        parsed.push(band);
        targets.push(target('JGB_10Y_YIELD_DEVIATION', band, 'percentage_points',
          rule === 'ycc_band' ? 'SYMMETRIC_BAND' : 'SYMMETRIC_REFERENCE_BAND'));
      }
      if (rule === 'ycc_flex') {
        const offer = uniqueMatch(text, /offer to purchase 10-year JGBs at (\d+(?:\.\d+)?) percent every business day through fixed-rate purchase operations/gi, asNumberOrRange);
        parsed.push(offer);
        targets.push(target('JGB_10Y_FIXED_RATE_PURCHASE_OFFER', offer, percentage, 'OFFER_RATE'));
      }
      if (rule === 'ycc_reference') {
        const reference = uniqueMatch(text, /regard the upper bound of (\d+(?:\.\d+)?) percent for 10-year JGB yields as a reference/gi, asNumberOrRange);
        parsed.push(reference);
        targets.push(target('JGB_10Y_YIELD_UPPER_REFERENCE', reference, percentage, 'UPPER_REFERENCE'));
      }
    }
  }
  if (parsed === undefined) return unresolved('guideline_missing_or_ambiguous');
  if (JSON.stringify(parsed) !== JSON.stringify(expected)) return unresolved('guideline_conflicts_with_reviewed_source');
  const evidence = effectiveEvidence(text, date, rule);
  if ((effective || evidence) && (!effective || evidence?.[0] !== dateWords(effective))) {
    return unresolved('effective_date_missing_or_conflicting');
  }
  return {
    verification_status: 'DOCUMENT_VERIFIED', decision_date_status: 'DOCUMENT_HEADER_CONFIRMED', reason: null, targets,
    publication_date: date, publication_timestamp: null, publication_timezone: 'Asia/Tokyo',
    publication_precision: 'DATE_ONLY',
    effective_date: effective, effective_date_status: evidence?.[1] ?? 'NOT_ESTABLISHED',
  };
}

async function retrieve(file, transport, delay, extract) {
  if (!/^(?:state_\d{4}\/(?:index|k\d+[a-z]?)\.htm|mpr_\d{4}\/k\d+[a-z]?\.(?:htm|pdf))$/.test(file)) {
    throw new Error('Invalid BOJ manifest path');
  }
  const pdf = file.endsWith('.pdf');
  const contentType = pdf ? 'application/pdf' : 'text/html';
  await delay(250);
  let response;
  try {
    response = await transport(origin + file, {
      method: 'GET', redirect: 'error', signal: AbortSignal.timeout(8000),
      headers: {accept: contentType},
    });
  } catch {
    return {http_status: null, publisher_connectivity: 'UNRESOLVED', reason: 'network_or_timeout', retrieved_utc: null};
  }
  const metadata = {http_status: response.status, publisher_connectivity: 'RESPONDED', retrieved_utc: new Date().toISOString()};
  if (!response.ok || response.headers.get('content-type')?.split(';')[0].trim().toLowerCase() !== contentType) {
    await response.body?.cancel().catch(() => {});
    return {...metadata, reason: response.ok ? 'unexpected_content_type' : 'http_error'};
  }
  const reader = response.body?.getReader();
  if (!reader) return {...metadata, reason: 'empty_body'};
  const chunks = [];
  let size = 0;
  try {
    while (true) {
      const {done, value} = await reader.read();
      if (done) break;
      size += value.byteLength;
      if (size > maxBytes) return {...metadata, reason: 'response_too_large'};
      chunks.push(Buffer.from(value));
    }
  } catch {
    return {...metadata, reason: 'body_read_failed'};
  } finally {
    await reader.cancel().catch(() => {});
  }
  if (!size) return {...metadata, reason: 'empty_body'};
  const bytes = Buffer.concat(chunks);
  const identity = {...metadata, content_sha256: createHash('sha256').update(bytes).digest('hex'), content_type: contentType};
  if (!pdf) return {...identity, text: bytes.toString('utf8')};
  if (bytes.subarray(0, 5).toString('ascii') !== '%PDF-') return {...identity, reason: 'malformed_pdf'};
  try {
    const result = extract(bytes, file.endsWith('/k160921a.pdf') ? 2 : 1);
    return {...identity, text: result.text, reason: result.error_category ?? null};
  } catch {
    return {...identity, reason: 'pdf_text_extraction_failed'};
  }
}

function dateFromArchive(label) {
  const match = label.match(/^([A-Za-z]+)\.?\s+(\d{1,2}),\s*(\d{4})$/);
  if (!match) return null;
  const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
  const month = months.indexOf(match[1].slice(0, 3));
  if (month < 0) return null;
  const date = match[3] + '-' + String(month + 1).padStart(2, '0') + '-' + match[2].padStart(2, '0');
  const parsed = new Date(date + 'T00:00:00Z');
  return Number.isNaN(parsed.valueOf()) || parsed.toISOString().slice(0, 10) !== date ? null : date;
}

export function archiveDates(html, year) {
  // The publisher's year indexes may use a heading rather than a table caption.
  // Identify the table by its Date/Title header and its nearby year heading,
  // never by arbitrary date-looking text elsewhere on the page.
  const heading = new RegExp('Statements on Monetary Policy\\s+' + year, 'i');
  const tables = [...html.matchAll(/<table\b[^>]*>[\s\S]*?<\/table\s*>/gi)];
  const candidates = tables.filter(match => {
    const prefix = html.slice(Math.max(0, match.index - 2500), match.index);
    const body = match[0];
    const rows = [...body.matchAll(/<tr\b[^>]*>([\s\S]*?)<\/tr\s*>/gi)];
    const first = rows[0]?.[1] ?? '';
    const headers = [...first.matchAll(/<t[dh]\b[^>]*>([\s\S]*?)<\/t[dh]\s*>/gi)]
      .map(cell => htmlText(cell[1]).toLowerCase());
    return (heading.test(prefix) || heading.test(body)) &&
      headers.length >= 2 && headers[0] === 'date' && headers[1] === 'title';
  });
  if (candidates.length !== 1) return null;
  const dates = new Set();
  const rows = [...candidates[0][0].matchAll(/<tr\b[^>]*>([\s\S]*?)<\/tr\s*>/gi)].slice(1);
  if (!rows.length) return null;
  for (const [, row] of rows) {
    const cells = [...row.matchAll(/<t[dh]\b[^>]*>([\s\S]*?)<\/t[dh]\s*>/gi)];
    if (cells.length < 2) return null;
    const date = dateFromArchive(htmlText(cells[0][1]));
    if (!date || !date.startsWith(year + '-')) return null;
    // A listed decision must link to a publisher document, not merely be text.
    if (!/<a\b[^>]*href\s*=/i.test(cells[1][1])) return null;
    if (date <= cutoff) dates.add(date);
  }
  return dates.size ? [...dates].sort() : null;
}

const gaps = [
  {from: null, through: '1998-09-08', status: 'UNSUPPORTED_BY_THIS_INVENTORY', reason: 'earlier_guidelines_and_discount_rate_need_separate_reconstruction'},
  {from: '1998-09-09', through: '2024-03-18', status: 'UNRESOLVED', reason: 'selected_anchors_only_meeting_census_and_instrument_changes_pending'},
  {from: '2026-10-31', through: null, status: 'OUT_OF_SCOPE', reason: 'fixed_audit_cutoff'},
];

export async function auditBojHistory({transport = fetch, delay = sleep, extract = (bytes, pages) => pdfToText(bytes, undefined, pages), rows = manifest} = {}) {
  const events = [];
  for (const row of rows) {
    const [date, file, regime, , , , title] = row;
    const {text, reason, ...source} = await retrieve(file, transport, delay, extract);
    events.push({
      decision_date: date, regime, frequency: 'DECISION_EVENT',
      source_url: origin + file, source_document_title: title, source_document_type: 'BOJ_DECISION_STATEMENT',
      decision_date_status: 'MANIFEST_CANDIDATE',
      ...source, revision_status: 'HISTORICAL_VINTAGES_UNRESOLVED', revision_of_sha256: null,
      ...(text === undefined ? unresolved(reason) : parseDecision(text, row)),
    });
  }
  const periods = [];
  for (const year of [2024, 2025, 2026]) {
    const file = 'state_' + year + '/index.htm';
    const {text, reason, ...source} = await retrieve(file, transport, delay, extract);
    const dates = text === undefined ? null : archiveDates(text, year);
    const from = year === 2024 ? '2024-03-19' : year + '-01-01';
    const listed = dates?.filter(date => date >= from) ?? [];
    const scoped = events.filter(event => event.decision_date >= from && event.decision_date.startsWith(year + '-'));
    const verified = new Set(scoped.filter(event => event.verification_status === 'DOCUMENT_VERIFIED').map(event => event.decision_date));
    const unresolvedDates = listed.filter(date => !verified.has(date));
    const unlisted = dates ? scoped.filter(event => !listed.includes(event.decision_date)).map(event => event.decision_date) : [];
    periods.push({
      from, through: year === 2026 ? cutoff : year + '-12-31',
      archive_url: origin + file, ...source, listed_dates: listed,
      unresolved_dates: unresolvedDates, manifest_dates_missing_from_archive: unlisted,
      status: dates && listed.length && !unresolvedDates.length && !unlisted.length
        ? 'LISTED_DATES_RECONCILED' : 'UNRESOLVED',
      archive_error: dates ? null : reason ?? 'archive_table_unproven',
    });
  }
  return {
    schema_version: 1, publisher: 'Bank of Japan', candidate_mapping: 'G7-JP-22', mapping_status: 'UNCONFIGURED',
    cutoff, historical_completeness: 'PARTIAL', full_history_verified: false, economic_comparability: 'REGIME_SPECIFIC',
    revision_vintages_verified: false, commercial_rights: 'PENDING', production_approval: 'NOT_APPROVED',
    document_counts: {selected: events.length, verified: events.filter(e => e.verification_status === 'DOCUMENT_VERIFIED').length},
    periods, gaps, events,
  };
}

if (process.argv[1] && fileURLToPath(import.meta.url) === resolve(process.argv[1])) {
  const output = process.argv[2];
  if (!output) throw new Error('Provide a disposable output directory');
  const report = await auditBojHistory();
  await mkdir(output, {recursive: true});
  await writeFile(join(output, 'boj_historical_policy_evidence.json'), JSON.stringify(report, null, 2) + '\n');
  console.log(JSON.stringify({boJ_history: report.document_counts, full_history_verified: report.full_history_verified}));
}
