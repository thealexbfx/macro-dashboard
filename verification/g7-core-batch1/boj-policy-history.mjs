// BOJ original historical money-market-operation guideline statements.
// Partial event verification ONLY, not complete G7-JP-22 history or effective dates.
import {parseBojPolicyGuideline} from './boj-policy-guideline.mjs';

const EVENTS=Object.freeze([
  {decision_date:'2025-01-24',expected_percent:0.5,
   url:'https://www.boj.or.jp/en/mopo/mpmdeci/state_2025/k250124a.htm'},
  {decision_date:'2025-12-19',expected_percent:0.75,
   url:'https://www.boj.or.jp/en/mopo/mpmdeci/state_2025/k251219a.htm'},
]);
const MAX_BYTES=1048576;
export function verifiedBojEvent(html,event) {
  const parsed=parseBojPolicyGuideline(html);
  if(parsed.outcome!=='PUBLISHER_GUIDELINE_SNAPSHOT')return {
    outcome:'UNRESOLVED',error_category:parsed.error_category??'guideline_missing'};
  if(parsed.level!==event.expected_percent)return {
    outcome:'MISMATCH',error_category:'expected_decision_rate_conflict'};
  const cleaned=html.replace(/<script\b[^>]*>[\s\S]*?<\/script\s*>/gi,' ')
    .replace(/<style\b[^>]*>[\s\S]*?<\/style\s*>/gi,' ')
    .replace(/<[^>]*>/g,' ').replace(/\s+/g,' ');
  const expected=new Date(event.decision_date+'T00:00:00Z').toLocaleDateString('en-US',{
    month:'long',day:'numeric',year:'numeric',timeZone:'UTC'});
  if(!cleaned.includes(expected))return {
    outcome:'UNRESOLVED',error_category:'decision_date_not_proven'};
  if(!/Bank of Japan/i.test(cleaned))return {
    outcome:'UNRESOLVED',error_category:'publisher_identity_missing'};
  return {outcome:'PUBLISHER_DECISION_EVENT_SAMPLE',error_category:null,
    decision_date:event.decision_date,announced_target_percent:parsed.level,
    decision_date_source:'original_BOJ_statement',
    effective_date:null,effective_date_status:'NOT_ESTABLISHED',
    event_type:'BOJ_MONEY_MARKET_GUIDELINE',
    policy_vs_market:'ANNOUNCED_TARGET_NOT_OBSERVED_MARKET_RATE'};
}
export async function probeBojPolicyHistory(transport=fetch,delay=async()=>{}) {
  const output={publisher:'Bank of Japan',purpose:'PARTIAL_ORIGINAL_DECISION_EVENT_CHECK',
    target_mapping:'G7-JP-22',mapping_status:'UNCONFIGURED',
    history_status:'PARTIAL_TWO_DECISIONS_ONLY',
    full_history_verified:false,effective_dates_verified:false,
    revision_vintages_verified:false,commercial_rights:'PENDING',
    production_approval:'NOT_APPROVED',events:[]};
  for(const e of EVENTS){
    const base={source_url:e.url,decision_date:e.decision_date};
    let receipt=null;
    for(let attempt=1;attempt<=3;attempt++){
      await delay(attempt*300);
      let response;
      try{response=await transport(e.url,{method:'GET',redirect:'error',
        signal:AbortSignal.timeout(8000),headers:{accept:'text/html'}});}
      catch{if(attempt===3)receipt={...base,outcome:'UNRESOLVED',error_category:'network_or_timeout'};continue;}
      const common={...base,http_status:response.status,retrieved_utc:new Date().toISOString()};
      if(!response.ok){
        await response.body?.cancel().catch(()=>{});
        if(attempt<3&&(response.status===429||response.status>=500))continue;
        receipt={...common,outcome:'UNRESOLVED',error_category:'http_'+response.status};break;
      }
      if(!/text\/html/i.test(response.headers.get('content-type')??'')){
        receipt={...common,outcome:'UNRESOLVED',error_category:'wrong_content_type'};break;
      }
      const reader=response.body?.getReader();
      if(!reader){receipt={...common,outcome:'UNRESOLVED',error_category:'empty_body'};break;}
      let text='',bytes=0,oversized=false,readFailure=false;const decoder=new TextDecoder();
      try{
        while(true){const {done,value}=await reader.read();if(done)break;
          bytes+=value.byteLength;if(bytes>MAX_BYTES){oversized=true;break;}
          text+=decoder.decode(value,{stream:true});}
        text+=decoder.decode();
      }catch{readFailure=true;}
      finally{await reader.cancel().catch(()=>{});}
      if(oversized||readFailure){
        receipt={...common,outcome:'UNRESOLVED',
          error_category:oversized?'oversize_html':'body_read_failed'};break;
      }
      receipt={...common,...verifiedBojEvent(text,e)};break;
    }
    output.events.push(receipt??{...base,outcome:'UNRESOLVED',error_category:'no_receipt'});
  }
  output.confirmed_events=output.events.filter(e=>e.outcome==='PUBLISHER_DECISION_EVENT_SAMPLE').length;
  output.all_selected_events_confirmed=output.confirmed_events===EVENTS.length;
  return output;
}
