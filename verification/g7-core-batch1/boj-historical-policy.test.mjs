import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {archiveDates, auditBojHistory, parseDecision} from './boj-historical-policy.mjs';

const manifest = JSON.parse(await readFile(new URL('./boj-historical-sources.json', import.meta.url)));
const row = date => manifest.find(record => record[0] === date);
const call = 'The Bank will encourage the uncollateralized overnight call rate to remain at around ';
const effective = 'The new guideline for money market operations will be effective from ';
const statement = (date, body, record = row(date)) => {
  const label = new Date(date + 'T00:00:00Z').toLocaleDateString('en-US', {
    month: 'long', day: 'numeric', year: 'numeric', timeZone: 'UTC',
  });
  return record[1].endsWith('.pdf')
    ? '1\n' + label + '\nBank of Japan\n' + record[6] + '\n' + body
    : '<main><h1>' + record[6] + '</h1><p>' + label + '<br>Bank of Japan</p><p>' + body + '</p></main>';
};
const parse = (date, body) => parseDecision(statement(date, body), row(date));
const table = (year, rows) => '<table><caption>Statements on Monetary Policy ' + year +
  '</caption><tr><th>Date</th><th>Title</th></tr>' +
  rows.map(label => '<tr><td>' + label + '</td><td><a href="decision.htm">Decision</a></td></tr>').join('') + '</table>';

test('early call rate and zero-rate guidance preserve the distinction between a level and an instruction', () => {
  const result = parse('1998-09-09', 'The Bank of Japan will encourage the uncollateralized overnight call rate to move on average around 0.25%.');
  assert.equal(result.verification_status, 'DOCUMENT_VERIFIED');
  assert.equal(result.targets[0].value, 0.25);
  const zirp = parse('1999-02-12', 'The Bank of Japan will encourage the uncollateralized overnight call rate to move as low as possible. The Bank will initially aim to guide the above call rate to move around 0.15%, and subsequently induce further decline.');
  assert.equal(zirp.verification_status, 'DOCUMENT_VERIFIED');
  assert.equal(zirp.targets[0].value, null);
  assert.equal(zirp.targets[1].qualifier, 'INITIAL_GUIDANCE_ONLY');
  assert.equal(zirp.targets[1].value, 0.15);
  assert.equal(parse('2006-03-09', call.replace('around ', 'effectively zero percent.')).targets[0].qualifier, 'EFFECTIVELY_ZERO');
});

test('QE and QQE retain their own units, amounts, and ranges', () => {
  const qe = parse('2001-03-19', 'The Bank of Japan will conduct money market operations, aiming the outstanding balance of the current accounts at the Bank at around 5 trillion yen.');
  assert.equal(qe.verification_status, 'DOCUMENT_VERIFIED');
  assert.equal(qe.targets[0].unit, 'trillion_jpy');
  const qqe = parse('2013-04-04', 'The monetary base will increase at an annual pace of about 60–70 trillion yen.');
  assert.equal(qqe.verification_status, 'DOCUMENT_VERIFIED');
  assert.deepEqual(qqe.targets[0], {instrument:'MONETARY_BASE_ANNUAL_GROWTH', unit:'trillion_jpy_per_year',
    qualifier:'AROUND', value:null, lower:60, upper:70});
});

test('negative rate effective date and YCC instruments remain independent', () => {
  const negative = 'The Bank will apply a negative interest rate of minus 0.1 percent to current accounts that financial institutions hold at the Bank.';
  const nirp = parse('2016-01-29', negative + ' A negative interest rate of minus 0.1 percent will be effective from the reserve maintenance period, which commences from February16, 2016.');
  assert.equal(nirp.verification_status, 'DOCUMENT_VERIFIED');
  assert.equal(nirp.effective_date, '2016-02-16');
  const ycc = parse('2016-09-21', negative + ' 10-year JGB yields will remain more or less at the current level (around zero percent).');
  assert.deepEqual(ycc.targets.map(target => [target.instrument, target.value]), [['BOJ_POLICY_RATE_BALANCES', -0.1], ['JGB_10Y_YIELD_TARGET', 0]]);
  assert.equal(parse('2016-09-21', negative).verification_status, 'UNRESOLVED');
});

test('modern range, explicit dates, and no-change meetings remain distinct', () => {
  const march = parse('2024-03-19', call + '0 to 0.1 percent. The new guideline for market operations and the new interest rate on the current account balances will be effective from March 21, 2024.');
  assert.equal(march.effective_date, '2024-03-21');
  assert.equal(march.targets[0].lower, 0);
  assert.equal(march.targets[0].upper, 0.1);
  const modern = parse('2025-01-24', call + '0.5\npercent.1 ' + effective + 'January 27, 2025.');
  assert.equal(modern.verification_status, 'DOCUMENT_VERIFIED');
  assert.equal(modern.effective_date, '2025-01-27');
  const hold = parse('2025-03-19', call + '0.5 percent. A dissenter would encourage the uncollateralized overnight call rate to remain at around 0.75 percent.');
  assert.equal(hold.verification_status, 'DOCUMENT_VERIFIED');
  assert.equal(hold.effective_date, null);
  assert.equal(hold.publication_timestamp, null);
});

test('missing, conflicting, and synthetic evidence cannot create an observation', () => {
  const date = '2025-01-24';
  const valid = call + '0.5 percent. ' + effective + 'January 27, 2025.';
  for (const body of [
    valid.replace('January 27', 'January 26'),
    call + '0.5 percent. The loan rate will be effective from January 27, 2025.',
    valid + ' ' + call + '0.75 percent.',
    valid.replace(call, 'The observed overnight call rate was '),
    valid.replace('0.5 percent', '0.6 percent'),
  ]) {
    const result = parse(date, body);
    assert.equal(result.verification_status, 'UNRESOLVED');
    assert.deepEqual(result.targets, []);
  }
  assert.equal(parseDecision(statement(date, valid).replace('January 24, 2025', 'January 23, 2025'), row(date)).verification_status, 'UNRESOLVED');
  assert.equal(parseDecision(statement(date, valid).replace('Bank of Japan', 'Another Bank'), row(date)).verification_status, 'UNRESOLVED');
  assert.equal(parse('2025-03-19', '<script>' + call + '0.5 percent.</script>').verification_status, 'UNRESOLVED');
});

test('publisher archive de-duplicates dates and rejects unexpected dates or shape', () => {
  const fixture = table(2026, ['Oct.&nbsp;30, 2026', 'Oct. 30, 2026', 'Dec. 18, 2026']);
  assert.deepEqual(archiveDates(fixture, 2026), ['2026-10-30']);
  assert.equal(archiveDates(table(2026, ['Oct. 30, 2025']), 2026), null);
  assert.equal(archiveDates(table(2026, ['Feb. 30, 2026']), 2026), null);
  assert.equal(archiveDates('<h1>Bank of Japan</h1>', 2026), null);
});

test('publisher annual table without caption uses heading and linked titles', () => {
  const html = '<h1>Statements on Monetary Policy 2024</h1>' +
    '<table><thead><tr><th>Date</th><th>Title</th></tr></thead><tbody>' +
    '<tr><td>Dec.&nbsp;19,&nbsp;2024</td><td><a href="k241219a.htm">Statement on Monetary Policy</a></td></tr>' +
    '<tr><td>Dec. 19, 2024</td><td><a href="reference.pdf">Reference</a></td></tr>' +
    '<tr><td>Mar. 19, 2024</td><td><a href="k240319a.htm">Changes in the Framework</a></td></tr>' +
    '</tbody></table>';
  assert.deepEqual(archiveDates(html, 2024), ['2024-03-19','2024-12-19']);
  assert.equal(archiveDates(html.replace('<h1>Statements on Monetary Policy 2024</h1>', ''), 2024), null);
  assert.equal(archiveDates(html.replace('href="k240319a.htm"', 'data-url="k240319a.htm"'), 2024), null);
  assert.equal(archiveDates(html + html, 2024), null);
});

test('transport receipts stay bounded, sanitized and partial even when a year reconciles', async () => {
  const date = '2025-03-19';
  const report = await auditBojHistory({rows:[row(date)], delay:async () => {}, transport:async (url, options) => {
    assert.match(url, /^https:\/\/www\.boj\.or\.jp\/en\/mopo\/mpmdeci\//);
    assert.equal(options.redirect, 'error');
    assert.equal(options.method, 'GET');
    if (url.includes('k250319a')) return new Response(statement(date, call + '0.5 percent. private_body'), {headers:{'content-type':'text/html; charset=UTF-8'}});
    if (url.includes('2025')) return new Response(table(2025, ['Mar. 19, 2025']), {headers:{'content-type':'text/html'}});
    if (url.includes('2026')) return new Response(table(2026, ['Oct. 30, 2026']), {headers:{'content-type':'text/html'}});
    throw Error('private_diagnostic');
  }});
  assert.equal(report.document_counts.verified, 1);
  assert.equal(report.periods[1].status, 'LISTED_DATES_RECONCILED');
  assert.deepEqual(report.periods[2].unresolved_dates, ['2026-10-30']);
  assert.equal(report.periods[0].publisher_connectivity, 'UNRESOLVED');
  assert.match(report.events[0].content_sha256, /^[a-f0-9]{64}$/);
  assert.equal(report.historical_completeness, 'PARTIAL');
  assert.equal(report.mapping_status, 'UNCONFIGURED');
  assert.equal(report.production_approval, 'NOT_APPROVED');
  assert.doesNotMatch(JSON.stringify(report), /private_/);
});

test('malformed PDF, failed extraction, and oversized response stay unresolved', async () => {
  const samples = [row('2025-01-24'), row('2025-12-19'), row('2026-09-18')];
  const report = await auditBojHistory({rows:samples, delay:async () => {}, extract:() => {throw Error('private');}, transport:async url => {
    if (url.endsWith('index.htm')) return new Response(null, {status:404});
    const body = url.includes('250124') ? 'broken' : url.includes('251219') ? '%PDF-1.7' : 'x'.repeat(1048577);
    return new Response(body, {headers:{'content-type':'application/pdf'}});
  }});
  assert.deepEqual(report.events.map(event => event.reason), ['malformed_pdf','pdf_text_extraction_failed','response_too_large']);
  assert.equal(report.document_counts.verified, 0);
});

test('YCC yield targets, reference bands and purchase offers use separate instruments', () => {
  const basics = 'The Bank will apply a negative interest rate of minus 0.1 percent to the Policy-Rate Balances. 10-year JGB yields will remain at around zero percent. ';
  const reference = 'The Bank will regard the upper bound of 1.0 percent for 10-year JGB yields as a reference in its market operations.';
  const result = parse('2023-10-31', basics + reference);
  assert.equal(result.verification_status, 'DOCUMENT_VERIFIED');
  assert.deepEqual(result.targets.map(t => [t.instrument, t.value]), [
    ['BOJ_POLICY_RATE_BALANCES', -0.1], ['JGB_10Y_YIELD_TARGET', 0], ['JGB_10Y_YIELD_UPPER_REFERENCE', 1],
  ]);
  assert.equal(parse('2023-10-31', basics + reference.replace('1.0', '0.5')).verification_status, 'UNRESOLVED');
});
