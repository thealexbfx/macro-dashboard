// BOJ original 2026 policy statements. Development-only, bounded and fail-closed.
// This verifies TWO selected original PDF decision statements, not full history.
import {spawnSync} from 'node:child_process';

export const PDF_EVENTS=Object.freeze([
  {decision_date:'2026-06-16',effective_date:'2026-06-17',expected_percent:1,
   url:'https://www.boj.or.jp/en/mopo/mpmdeci/mpr_2026/k260616a.pdf'},
  {decision_date:'2026-09-18',effective_date:'2026-09-24',expected_percent:1.25,
   url:'https://www.boj.or.jp/en/mopo/mpmdeci/mpr_2026/k260918a.pdf'}
]);
const MAX_PDF_BYTES=524288;
export function pdfToText(pdf, spawn = spawnSync) {
  const result = spawn('pdftotext', ['-f', '1', '-l', '1', '-enc', 'UTF-8', '-', '-'], {
    input: pdf, timeout: 5000, maxBuffer: 262144, encoding: 'utf8', windowsHide: true,
    env: {...process.env, LC_ALL: 'C'},
  });
  if (result.error?.code === 'ENOENT') return {error_category: 'pdftotext_missing'};
  if (result.error?.code === 'ETIMEDOUT') return {error_category: 'pdf_text_extraction_timeout'};
  if (result.error?.code === 'ENOBUFS') return {error_category: 'pdf_text_extraction_output_limit'};
  if (result.error || result.status !== 0) {
    const malformed = !result.error && result.status === 1 &&
      /couldn.t find trailer dictionary|couldn.t read xref table|damaged pdf|may not be a pdf|invalid xref/i.test(result.stderr ?? '');
    return {error_category: malformed ? 'malformed_pdf' : 'pdf_text_extraction_failed'};
  }
  if (typeof result.stdout !== 'string' || !result.stdout.trim()) {
    return {error_category: 'pdf_text_extraction_empty'};
  }
  return {text: result.stdout};
}
const dateWords=day=>new Date(day+'T00:00:00Z').toLocaleDateString('en-US',{
  month:'long',day:'numeric',year:'numeric',timeZone:'UTC'});
export function verifyBojPdfDecision(text,event) {
  if(typeof text!=='string'||!text.trim()||text.length>200000)
    return {outcome:'UNRESOLVED',error_category:'missing_extracted_text'};
  const normalized=text.replace(/\s+/g,' ').trim();
  if(!normalized.includes('Bank of Japan')||
     !normalized.includes('Change in the Guideline for Money Market Operations'))
    return {outcome:'UNRESOLVED',error_category:'publisher_or_document_identity_missing'};
  if(!normalized.replace(/^\d+\s+/, '').startsWith(dateWords(event.decision_date)+' Bank of Japan Change in the Guideline for Money Market Operations'))
    return {outcome:'UNRESOLVED',error_category:'decision_date_not_proven'};
  const match=normalized.match(/The Bank will encourage the uncollateralized overnight call rate to remain at around\s+(\d{1,2}(?:\.\d{1,2})?)\s+percent\b/i);
  if(!match)return {outcome:'UNRESOLVED',error_category:'target_guideline_not_proven'};
  if(Number(match[1])!==event.expected_percent)
    return {outcome:'UNRESOLVED',error_category:'announced_rate_conflicts_with_source'};
  const footnote=normalized.match(/new guideline for money market operations will be effective from\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),\s+(20\d\d)/i);
  if(!footnote)return {outcome:'UNRESOLVED',error_category:'effective_date_not_proven'};
  const effective=new Date(footnote[1]+' '+footnote[2]+', '+footnote[3]+' 00:00:00 GMT');
  if(Number.isNaN(effective.valueOf())||effective.toISOString().slice(0,10)!==event.effective_date)
    return {outcome:'UNRESOLVED',error_category:'effective_date_conflicts_with_source'};
  return {outcome:'PUBLISHER_DECISION_EVENT_SAMPLE',error_category:null,
    decision_date:event.decision_date,effective_date:event.effective_date,
    effective_date_source:'BOJ_ORIGINAL_STATEMENT_FOOTNOTE',
    announced_target_percent:event.expected_percent,
    event_type:'ANNOUNCED_POLICY_GUIDELINE_NOT_OBSERVED_MARKET_RATE',
    verification_scope:'TWO_SELECTED_2026_DOCUMENTS_ONLY'};
}
export async function probeBoj2026Pdfs(transport=fetch,delay=async()=>{},extractText=pdfToText){
  const output={publisher:'Bank of Japan',purpose:'SELECTED_2026_PDF_DECISION_EVIDENCE',
    target_mapping:'G7-JP-22',mapping_status:'UNCONFIGURED',
    full_history_verified:false,intervening_meetings_verified:false,
    vintage_history_verified:false,rights_status:'PENDING',
    production_approval:'NOT_APPROVED',events:[]};
  for(const event of PDF_EVENTS){
    let receipt=null;
    for(let attempt=1;attempt<=3;attempt++){
      await delay(attempt*350);
      let response;
      try{response=await transport(event.url,{method:'GET',redirect:'error',
        signal:AbortSignal.timeout(8000),headers:{accept:'application/pdf'}});}
      catch{if(attempt===3)receipt={outcome:'UNRESOLVED',error_category:'network_or_timeout'};continue;}
      const common={http_status:response.status,retrieved_utc:new Date().toISOString()};
      if(!response.ok){
        await response.body?.cancel().catch(()=>{});
        if(attempt<3&&(response.status===429||response.status>=500))continue;
        receipt={...common,outcome:'UNRESOLVED',error_category:'http_'+response.status};break;
      }
      if(!/application\/pdf/i.test(response.headers.get('content-type')??'')){
        await response.body?.cancel().catch(()=>{});
        receipt={...common,outcome:'UNRESOLVED',error_category:'unexpected_content_type'};break;
      }
      const reader=response.body?.getReader();
      if(!reader){receipt={...common,outcome:'UNRESOLVED',error_category:'empty_body'};break;}
      const chunks=[];let size=0,oversize=false,failed=false;
      try{while(true){const {done,value}=await reader.read();if(done)break;
        size+=value.byteLength;if(size>MAX_PDF_BYTES){oversize=true;break;}
        chunks.push(Buffer.from(value));}}
      catch{failed=true;}
      finally{await reader.cancel().catch(()=>{});}
      if(oversize||failed){
        receipt={...common,outcome:'UNRESOLVED',error_category:oversize?'oversize_pdf':'pdf_body_read_failed'};break;}
      const pdf=Buffer.concat(chunks);
      if(pdf.subarray(0,5).toString('ascii')!=='%PDF-'){
        receipt={...common,outcome:'UNRESOLVED',error_category:'malformed_pdf'};break;}
      let extraction;
      try {
        extraction = extractText(pdf);
      } catch {
        extraction = {error_category: 'pdf_text_extraction_failed'};
      }
      receipt = extraction.text === undefined
        ? {...common, outcome: 'UNRESOLVED', error_category: extraction.error_category}
        : {...common, ...verifyBojPdfDecision(extraction.text, event)};
      break;
    }
    output.events.push({source_url:event.url,expected_decision_date:event.decision_date,
      ...(receipt??{outcome:'UNRESOLVED',error_category:'no_receipt'})});
  }
  output.selected_events_verified=output.events.filter(e=>e.outcome==='PUBLISHER_DECISION_EVENT_SAMPLE').length;
  return output;
}
