// BOJ original 2026 PDF decisions; two selected events only, NOT full history.
import {execFileSync} from 'node:child_process';
const EVENTS=[
  {decision_date:'2026-06-16',effective_date:'2026-06-17',rate:1,
   url:'https://www.boj.or.jp/en/mopo/mpmdeci/mpr_2026/k260616a.pdf'},
  {decision_date:'2026-09-18',effective_date:'2026-09-24',rate:1.25,
   url:'https://www.boj.or.jp/en/mopo/mpmdeci/mpr_2026/k260918a.pdf'}
];
const MAX_PDF=524288,MAX_TEXT=131072;
const displayDate=s=>new Date(s+'T00:00:00Z').toLocaleDateString('en-US',{
  month:'long',day:'numeric',year:'numeric',timeZone:'UTC'});
export function pdfFirstPage(pdf) {
  return execFileSync('pdftotext',['-f','1','-l','1','-layout','-','-'],
    {input:pdf,timeout:5000,maxBuffer:MAX_TEXT,windowsHide:true}).toString('utf8');
}
export function checkBojPolicyPdf(text,event) {
  if(typeof text!=='string'||Buffer.byteLength(text)>MAX_TEXT)
    return {outcome:'UNRESOLVED',error_category:'missing_or_oversize_text'};
  const s=text.replace(/\s+/g,' ').trim();
  if(!s.includes(displayDate(event.decision_date)))
    return {outcome:'UNRESOLVED',error_category:'decision_date_not_proven'};
  if(!/\bBank of Japan\b/.test(s)||
     !/Change in the Guideline for Money Market Operations/i.test(s))
    return {outcome:'UNRESOLVED',error_category:'publisher_or_document_not_proven'};
  const matches=[...s.matchAll(/The Bank will encourage the uncollateralized overnight call rate to remain at around (\d{1,2}(?:\.\d{1,3})?) percent\b/gi)];
  if(matches.length!==1)return {outcome:'UNRESOLVED',error_category:'target_phrase_not_unique'};
  const target=Number(matches[0][1]);
  if(target!==event.rate)return {outcome:'MISMATCH',error_category:'unexpected_target_level'};
  if(!s.toLowerCase().includes(('new guideline for money market operations will be effective from '+displayDate(event.effective_date)).toLowerCase()))
    return {outcome:'UNRESOLVED',error_category:'effective_date_not_proven'};
  return {outcome:'PUBLISHER_PDF_POLICY_DECISION_SAMPLE',error_category:null,
    decision_date:event.decision_date,effective_date:event.effective_date,
    target_percent:target,unit:'percent',
    concept:'ANNOUNCED_GUIDELINE_NOT_OBSERVED_MARKET_RATE',verified_pdf_page:1};
}
async function readPdf(response) {
  const reader=response.body?.getReader();if(!reader)return {error:'empty_body'};
  let size=0;const chunks=[];
  try {
    while(true){const {value,done}=await reader.read();if(done)break;
      size+=value.byteLength;if(size>MAX_PDF)return {error:'oversize_pdf'};
      chunks.push(Buffer.from(value));}
  }catch{return {error:'pdf_body_read_failed'};}
  finally{await reader.cancel().catch(()=>{});}
  const pdf=Buffer.concat(chunks);
  return pdf.subarray(0,8).toString('ascii').startsWith('%PDF-')?{pdf}:{error:'not_a_pdf'};
}
export async function probeBojPolicyPdfs(transport=fetch,delay=async()=>{},extract=pdfFirstPage) {
  const report={publisher:'Bank of Japan',target_mapping:'G7-JP-22',
    purpose:'TWO_SELECTED_ORIGINAL_2026_DECISION_PDFS',
    mapping_status:'UNCONFIGURED',full_history_verified:false,
    intervening_meetings_verified:false,release_vintages_verified:false,
    rights_status:'PENDING',production_approval:'NOT_APPROVED',events:[]};
  for(const e of EVENTS){
    let record;
    for(let attempt=1;attempt<=3;attempt++){
      await delay(attempt*300);
      let response;
      try{response=await transport(e.url,{method:'GET',redirect:'error',
        signal:AbortSignal.timeout(10000),headers:{accept:'application/pdf'}});}
      catch{if(attempt===3)record={outcome:'UNRESOLVED',error_category:'network_or_timeout'};continue;}
      const receipt={http_status:response.status,retrieved_utc:new Date().toISOString()};
      if(!response.ok){
        await response.body?.cancel().catch(()=>{});
        if(attempt<3&&(response.status===429||response.status>=500))continue;
        record={...receipt,outcome:'UNRESOLVED',error_category:'http_'+response.status};break;
      }
      if(!/application\/pdf/i.test(response.headers.get('content-type')??'')){
        await response.body?.cancel().catch(()=>{});
        record={...receipt,outcome:'UNRESOLVED',error_category:'wrong_content_type'};break;
      }
      const loaded=await readPdf(response);
      if(loaded.error){record={...receipt,outcome:'UNRESOLVED',error_category:loaded.error};break;}
      let text;
      try{text=extract(loaded.pdf);}
      catch{record={...receipt,outcome:'UNRESOLVED',error_category:'pdf_extraction_failed_or_missing'};break;}
      record={...receipt,...checkBojPolicyPdf(text,e)};break;
    }
    report.events.push({source_url:e.url,decision_date:e.decision_date,
      ...(record??{outcome:'UNRESOLVED',error_category:'no_receipt'})});
  }
  report.confirmed_events=report.events.filter(x=>x.outcome==='PUBLISHER_PDF_POLICY_DECISION_SAMPLE').length;
  return report;
}
