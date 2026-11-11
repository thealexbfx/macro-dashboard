// BOJ current monetary-policy guideline, separate from observed overnight rate.
// This is a CURRENT SOURCE SNAPSHOT ONLY, not a historical target time series.
// Original publisher: https://www.boj.or.jp/en/index.htm
const URL='https://www.boj.or.jp/en/index.htm';
const MAX_BYTES=1572864;
const RATE_LABEL='BOJ_ANNOUNCED_UNCOLLATERALIZED_OVERNIGHT_CALL_RATE_TARGET';
export function parseBojPolicyGuideline(html) {
  if(typeof html!=='string' || html.length>MAX_BYTES ||
     !/<(?:!doctype html|html|main|body)\b/i.test(html)) return {
       outcome:'UNRESOLVED',error_category:'invalid_or_oversize_html'};
  // Remove executable/irrelevant sections; the output is never rendered as HTML.
  const page=html.replace(/<script\b[^>]*>[\s\S]*?<\/script\s*>/gi,' ')
    .replace(/<style\b[^>]*>[\s\S]*?<\/style\s*>/gi,' ')
    .replace(/<[^>]*>/g,' ').replace(/&nbsp;|&#160;|&#xA0;/gi,' ')
    .replace(/&amp;/gi,'&').replace(/\s+/g,' ').trim();
  const hits=[...page.matchAll(/The Bank will encourage the uncollateralized overnight call rate to remain at around\s+(\d{1,2}(?:\.\d{1,3})?)\s+percent\b/gi)];
  const levels=[...new Set(hits.map(m=>Number(m[1])))];
  if(levels.length!==1 || hits.length>3 || !Number.isFinite(levels[0]) ||
     levels[0]<0 || levels[0]>20) return {
       outcome:'UNRESOLVED',error_category:'ambiguous_or_missing_guideline'};
  return {outcome:'PUBLISHER_GUIDELINE_SNAPSHOT',error_category:null,
    level:levels[0],unit:'percent',label:RATE_LABEL,
    statement_kind:'BOJ_GUIDELINE_FOR_MONEY_MARKET_OPERATIONS',
    quote_pattern:'encourage uncollateralized overnight call rate to remain at around',
    frequency:'EVENT_DECISION_NOT_DAILY_OBSERVATION'};
}
export async function probeBojPolicyGuideline(transport=fetch,delay=async()=>{}) {
  const base={publisher:'Bank of Japan',url:URL,concept:'announced overnight rate target',
    target_mapping:'G7-JP-22',mapping_status:'UNCONFIGURED',
    verification_scope:'CURRENT_SOURCE_SNAPSHOT_ONLY',
    historical_target_series_verified:false,
    release_effective_date_verified:false,release_vintages_verified:false,
    rate_observations_verified:false,rights_status:'PENDING',
    production_approval:'NOT_APPROVED'};
  for(let attempt=1;attempt<=3;attempt++){
    await delay(attempt*350);
    let response;
    try{
      response=await transport(URL,{method:'GET',redirect:'error',
        signal:AbortSignal.timeout(8000),headers:{accept:'text/html'}});
    }catch {
      if(attempt===3)return {...base,outcome:'UNRESOLVED',http_status:null,
        error_category:'network_or_timeout'};
      continue;
    }
    const r={...base,http_status:response.status,retrieved_utc:new Date().toISOString()};
    if(!response.ok){
      await response.body?.cancel().catch(()=>{});
      if(attempt<3&&(response.status===429||response.status>=500))continue;
      return {...r,outcome:'UNRESOLVED',error_category:'http_'+response.status};
    }
    if(!/text\/html/i.test(response.headers.get('content-type')??''))
      return {...r,outcome:'UNRESOLVED',error_category:'unexpected_content_type'};
    const reader=response.body?.getReader();
    if(!reader)return {...r,outcome:'UNRESOLVED',error_category:'empty_body'};
    let received=0,text='',oversize=false;const decoder=new TextDecoder();
    try{
      while(true){const {done,value}=await reader.read();if(done)break;
        received+=value.byteLength;if(received>MAX_BYTES){oversize=true;break;}
        text+=decoder.decode(value,{stream:true});}
      if(oversize)return {...r,outcome:'UNRESOLVED',error_category:'oversize_html'};
      text+=decoder.decode();
    }catch{return {...r,outcome:'UNRESOLVED',error_category:'body_read_failed'};}
    finally{await reader.cancel().catch(()=>{});}
    // Never store HTML or unrelated monetary-policy percentages.
    return {...r,...parseBojPolicyGuideline(text)};
  }
}
