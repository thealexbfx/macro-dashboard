// Read-only source connectivity audit. This never verifies economic observations.
import {createHash} from 'node:crypto';
import {readFile, mkdir, writeFile} from 'node:fs/promises';
import {join, resolve} from 'node:path';
import {fileURLToPath} from 'node:url';

const manifest = JSON.parse(await readFile(new URL('./boj-historical-gap-candidates.json', import.meta.url)));
const MAX_BYTES = 1024 * 1024;
const TIMEOUT_MS = 8000;
const approved = url => {
  try {
    const u = new URL(url);
    return u.protocol === 'https:' && u.hostname === 'www.boj.or.jp' &&
      !u.username && !u.password && !u.search && !u.hash;
  } catch { return false; }
};
export async function probeSource(url, transport = fetch) {
  if (!approved(url)) return {url, status:'UNRESOLVED', reason:'unapproved_url'};
  let response;
  try {
    response = await transport(url, {method:'GET', redirect:'error', signal:AbortSignal.timeout(TIMEOUT_MS),
      headers:{accept:'text/html,application/pdf'}});
  } catch { return {url, status:'UNRESOLVED', reason:'network_or_timeout'}; }
  const http_status = response.status;
  const type = response.headers.get('content-type')?.split(';')[0].trim().toLowerCase() ?? null;
  if (!response.ok || !['text/html','application/pdf'].includes(type)) {
    await response.body?.cancel().catch(()=>{});
    return {url, status:'UNRESOLVED', http_status, content_type:type,
      reason:response.ok?'unexpected_content_type':'http_error'};
  }
  const reader = response.body?.getReader();
  if (!reader) return {url,status:'UNRESOLVED',http_status,reason:'empty_body'};
  const chunks=[]; let size=0;
  try {
    while (true) {
      const {done,value}=await reader.read();
      if (done) break;
      size+=value.byteLength;
      if (size>MAX_BYTES) return {url,status:'UNRESOLVED',http_status,reason:'response_too_large'};
      chunks.push(Buffer.from(value));
    }
  } catch { return {url,status:'UNRESOLVED',http_status,reason:'body_read_failed'}; }
  finally { await reader.cancel().catch(()=>{}); }
  if (!size) return {url,status:'UNRESOLVED',http_status,reason:'empty_body'};
  const bytes=Buffer.concat(chunks);
  if (type==='application/pdf' && bytes.subarray(0,5).toString('ascii')!=='%PDF-')
    return {url,status:'UNRESOLVED',http_status,reason:'malformed_pdf'};
  if (type==='text/html' && !/<html\b|<!doctype html/i.test(bytes.toString('utf8').slice(0,4096)))
    return {url,status:'UNRESOLVED',http_status,reason:'malformed_html'};
  return {url,status:'SOURCE_RETRIEVED_NOT_ECONOMICALLY_VERIFIED',http_status,content_type:type,
    content_sha256:createHash('sha256').update(bytes).digest('hex'),bytes:size};
}
export async function auditGapSources(transport = fetch) {
  const urls=[...new Set(manifest.candidates.flatMap(x=>[x.source_url,x.corroborating_official_url]).filter(Boolean))];
  const sources=[];
  for (const url of urls) sources.push(await probeSource(url,transport));
  return {scope:'SOURCE_CONNECTIVITY_ONLY',candidate_count:manifest.candidates.length,
    source_count:urls.length,mapping_status:'UNCONFIGURED',historical_completeness:'PARTIAL',
    production_approval:'NOT_APPROVED',commercial_rights:'PENDING',sources};
}
if (process.argv[1] && resolve(process.argv[1])===fileURLToPath(import.meta.url)) {
  if (!process.argv[2]) throw Error('Disposable output directory required');
  const report=await auditGapSources();
  await mkdir(process.argv[2],{recursive:true});
  await writeFile(join(process.argv[2],'boj_historical_gap_source_receipts.json'),
    JSON.stringify(report,null,2)+'\n');
  console.log(JSON.stringify({scope:report.scope,source_count:report.source_count,
    retrieved:report.sources.filter(x=>x.status==='SOURCE_RETRIEVED_NOT_ECONOMICALLY_VERIFIED').length}));
}
