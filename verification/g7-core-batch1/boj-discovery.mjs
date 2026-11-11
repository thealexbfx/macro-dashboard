// Development-only Bank of Japan discovery. NEVER verifies or approves G7-JP-22.
// Source: https://www.stat-search.boj.or.jp/ssi/docs/info/nme_aphelp_en.html
// Endpoint and db from BOJ API manual. No credentials, no arbitrary URLs.
const URL='https://www.stat-search.boj.or.jp/api/v1/getMetadata?format=json&lang=en&db=FM01';
const MAX_BYTES=2097152;
const keyList=value=>value && typeof value==='object' && !Array.isArray(value)
  ? Object.keys(value).filter(x=>/^[A-Za-z][A-Za-z0-9_]{0,49}$/.test(x)).sort().slice(0,24) : [];
const kind=value=>value===null?'null':Array.isArray(value)?'array':typeof value;
export function bojMetadataShape(value) {
  const first=Array.isArray(value)?value[0]:null;
  return {schema_only:true,root_type:kind(value),root_keys:keyList(value),
    root_array_length:Array.isArray(value)?value.length:null,
    first_entry_type:kind(first),first_entry_keys:keyList(first),
    first_level_types:Object.fromEntries(keyList(value).map(k=>[k,kind(value[k])])),
    // Never persist any publisher string values or individual series codes.
  };
}
export async function probeBojMetadata(transport=fetch,delay=async()=>{}) {
  const receipt={source:'Bank of Japan',database:'FM01',
    target_mapping:'G7-JP-22',purpose:'UNVERIFIED_DISCOVERY_ONLY',
    url:URL,verification_scope:'NONE',production_approval:'NOT_APPROVED',
    rights_status:'PENDING',series_code:null,identity_status:'UNRESOLVED'};
  for(let attempt=1;attempt<=3;attempt++) {
    await delay(attempt*350);
    let response;
    try {
      response=await transport(URL,{method:'GET',redirect:'error',
        signal:AbortSignal.timeout(8000),headers:{accept:'application/json'}});
    } catch {
      if(attempt===3)return {...receipt,error_category:'network_or_timeout',http_status:null,attempt};
      continue;
    }
    const meta={...receipt,http_status:response.status,attempt,retrieved_utc:new Date().toISOString()};
    if(!response.ok){
      await response.body?.cancel().catch(()=>{});
      if(attempt<3&&(response.status===429||response.status>=500))continue;
      return {...meta,error_category:'http_'+response.status};
    }
    const reader=response.body?.getReader();
    if(!reader)return {...meta,error_category:'empty_response'};
    const decoder=new TextDecoder();let text='',size=0,tooLarge=false;
    try {
      while(true){
        const {value,done}=await reader.read();if(done)break;
        size+=value.byteLength;
        if(size>MAX_BYTES){tooLarge=true;break;}
        text+=decoder.decode(value,{stream:true});
      }
      if(tooLarge)return {...meta,error_category:'response_too_large',bytes_at_least:size};
      text+=decoder.decode();
    } catch{return {...meta,error_category:'response_body_failed'};}
    finally {await reader.cancel().catch(()=>{});}
    let json;
    try{json=JSON.parse(text);}catch{return {...meta,error_category:'invalid_json'};}
    return {...meta,error_category:null,shape:bojMetadataShape(json),
      // API response may be valid JSON but be an error or limited response.
      operational_result:'RETRIEVED_METADATA_RESPONSE_NOT_SERIES_VERIFIED'};
  }
}
