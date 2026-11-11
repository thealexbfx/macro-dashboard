// BOJ first-party observed uncollateralized overnight call rate (average).
// DEVELOPMENT EVIDENCE ONLY. This is NOT Japan's announced policy-rate target.
const ENDPOINT='https://www.stat-search.boj.or.jp/api/v1/getDataCode';
const SERIES='STRDCLUCON', DB='FM01';
const TYPE='OBSERVED_UNCOLLATERALIZED_OVERNIGHT_CALL_RATE_AVERAGE';
const maxBytes=524288;
const kind=v=>v===null?'null':Array.isArray(v)?'array':typeof v;
const keys=v=>v && typeof v==='object' && !Array.isArray(v)
  ? Object.keys(v).filter(k=>/^[A-Z][A-Z0-9_]{0,48}$/.test(k)).sort().slice(0,24):[];
export function observedBojShape(payload) {
  const first=Array.isArray(payload?.RESULTSET)?payload.RESULTSET[0]:null;
  const values=first?.VALUES;
  return {root_keys:keys(payload),resultset_type:kind(payload?.RESULTSET),
    resultset_length:Array.isArray(payload?.RESULTSET)?payload.RESULTSET.length:null,
    first_entry_keys:keys(first),values_type:kind(values),
    values_keys:keys(values),first_values_type:kind(Array.isArray(values)?values[0]:null),
    first_values_keys:keys(Array.isArray(values)?values[0]:null),
    schema_only:true};
}
export function extractObservedBoj(payload) {
  const diagnostic=observedBojShape(payload);
  if(!payload || payload.STATUS!==200 || payload.DB!==DB ||
      !Array.isArray(payload.RESULTSET))
    return {outcome:'UNRESOLVED',error_category:'invalid_boj_envelope',shape:diagnostic};
  const rows=payload.RESULTSET;
  if(rows.length!==1 || rows[0]?.SERIES_CODE!==SERIES)
    return {outcome:'UNRESOLVED',error_category:'unexpected_series_identity',shape:diagnostic};
  const item=rows[0];
  const title=item.NAME_OF_TIME_SERIES;
  if(typeof title!=='string' || !/uncollateralized|unsecured/i.test(title) ||
      !/overnight/i.test(title) || !/average/i.test(title))
    return {outcome:'UNRESOLVED',error_category:'series_definition_not_proven',shape:diagnostic};
  if(item.FREQUENCY!=='DAILY')
    return {outcome:'UNRESOLVED',error_category:'frequency_not_daily',shape:diagnostic};
  // BOJ's documented JSON has period and numeric arrays within VALUES.
  // If a publisher revision changes nesting, retain a structure receipt rather
  // than guessing or silently accepting another series.
  const observations=item.VALUES;
  const periods=observations?.SURVEY_DATES,values=observations?.VALUES;
  if(!Array.isArray(periods)||!Array.isArray(values)||periods.length!==values.length ||
      periods.length===0 || periods.length>80)
    return {outcome:'UNRESOLVED',error_category:'unexpected_observation_structure',shape:diagnostic};
  const samples=[];
  for(let i=0;i<periods.length;i++) {
    const period=periods[i],value=values[i];
    if(value===null)continue;
    if(typeof period!=='string'|| !/^\d{8}$/.test(period)||
       !(typeof value==='number'||typeof value==='string') ||
       !/^-?\d{1,3}(?:\.\d{1,8})?$/.test(String(value)) ||
       !Number.isFinite(Number(value)))return {
         outcome:'UNRESOLVED',error_category:'invalid_observation',shape:diagnostic};
    samples.push({date:period,value:Number(value)});
  }
  if(!samples.length)return {outcome:'UNRESOLVED',error_category:'no_numeric_samples',shape:diagnostic};
  return {outcome:'RECENT_OBSERVED_RATE_SAMPLE',error_category:null,
    series_id:SERIES,publisher:'Bank of Japan',unit:'percent per annum',
    label:TYPE,frequency:'DAILY',last_observations:samples.slice(-5),
    sample_count:samples.length,policy_target_equivalence:'NOT_ESTABLISHED',
    verification_scope:'RECENT_SAMPLE_ONLY',history_status:'PENDING',
    vintage_status:'PENDING',rights_status:'PENDING',
    production_approval:'NOT_APPROVED'};
}
export async function probeObservedBoj(transport=fetch,delay=async()=>{}) {
  const month=d=>d.getUTCFullYear().toString()+String(d.getUTCMonth()+1).padStart(2,'0');
  const now=new Date(),before=new Date(now);before.setUTCMonth(now.getUTCMonth()-1);
  const url=ENDPOINT+'?format=json&lang=en&db='+DB+'&startDate='+month(before)+
    '&endDate='+month(now)+'&code='+SERIES;
  const base={purpose:'DEVELOPMENT_OBSERVED_MARKET_RATE_ONLY',target_mapping:null,
    publisher:'Bank of Japan',series_id:SERIES,database:DB,url,
    policy_target_equivalence:'NOT_ESTABLISHED',production_approval:'NOT_APPROVED',
    rights_status:'PENDING',history_status:'PENDING',vintage_status:'PENDING'};
  for(let attempt=1;attempt<=3;attempt++){
    await delay(attempt*350);
    let res;
    try {res=await transport(url,{method:'GET',redirect:'error',signal:AbortSignal.timeout(8000),
      headers:{accept:'application/json'}});}
    catch {if(attempt===3)return {...base,outcome:'UNRESOLVED',error_category:'network_or_timeout',http_status:null};continue;}
    const receipt={...base,http_status:res.status,retrieved_utc:new Date().toISOString()};
    if(!res.ok){
      await res.body?.cancel().catch(()=>{});
      if(attempt<3&&(res.status===429||res.status>=500))continue;
      return {...receipt,outcome:'UNRESOLVED',error_category:'http_'+res.status};
    }
    const reader=res.body?.getReader();
    if(!reader)return {...receipt,outcome:'UNRESOLVED',error_category:'empty_body'};
    let byteCount=0,text='',oversized=false;
    const decoder=new TextDecoder();
    try {while(true){const {value,done}=await reader.read();if(done)break;
      byteCount+=value.byteLength;if(byteCount>maxBytes){oversized=true;break;}
      text+=decoder.decode(value,{stream:true});}
      if(oversized)return {...receipt,outcome:'UNRESOLVED',error_category:'oversized_response'};
      text+=decoder.decode();}
    catch{return {...receipt,outcome:'UNRESOLVED',error_category:'body_read_failed'};}
    finally {await reader.cancel().catch(()=>{});}
    let payload;try{payload=JSON.parse(text);}
    catch{return {...receipt,outcome:'UNRESOLVED',error_category:'invalid_json'};}
    return {...receipt,...extractObservedBoj(payload)};
  }
}
