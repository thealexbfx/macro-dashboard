import {publisherRequest, safeNumber} from './publisher-http.mjs';
const ENDPOINT='https://api.bls.gov/publicAPI/v1/timeseries/data/';
export async function verifyBls(row, original, spec, transport=fetch, delay=async()=>{}) {
  const result={...original,publisher_series_id:spec.seriesId,source_url:ENDPOINT,
    publisher_discovery_url:spec.discoveryUrl, evidence_method:'BLS public API v1 POST (no registration key)',
    observation_source_url:ENDPOINT, verification_scope:'NONE', error_category:null,
    rights_note:'BLS publisher content generally public domain with stated exceptions; precise commercial display/export conditions still pending.'};
  const body=JSON.stringify({seriesid:[spec.seriesId]});
  const response=await publisherRequest(ENDPOINT,{method:'POST',body,transport,delay});
  result.http_status=response.http_status;result.api_receipts=[{url:ENDPOINT,
    http_status:response.http_status,retrieved_utc:response.retrieved_utc,
    error:response.error??null}];
  if(response.error){
    const inaccessible=response.error==='network_or_timeout'||/^http_/.test(response.error);
    return {...result,outcome:inaccessible?'ACCESS_BLOCKED':'UNRESOLVED',
      access_status:inaccessible?'BLOCKED':'RETRIEVED',error_category:response.error};
  }
  result.access_status='RETRIEVED';
  let payload;try{payload=JSON.parse(response.text);}catch{
    return {...result,error_category:'invalid_json'};
  }
  if(payload?.status!=='REQUEST_SUCCEEDED') {
    return {...result,error_category:'publisher_api_rejected',api_messages:Array.isArray(payload?.message)?
      payload.message.slice(0,3).map(s=>String(s).slice(0,160)):[]};
  }
  const matches=payload?.Results?.series;
  if(!Array.isArray(matches) || matches.length!==1 || typeof matches[0]?.seriesID!=='string'){
    return {...result,error_category:'missing_series_evidence'};
  }
  if(matches[0].seriesID!==spec.seriesId){
    return {...result,outcome:'MISMATCH',identity_status:'MISMATCH',
      error_category:'publisher_series_id_conflict',mismatch_notes:'Returned ID differs from requested publisher identifier.'};
  }
  result.identity_status='PUBLISHER_ID_MATCHED';
  result.definition=spec.expectedDefinition;
  result.seasonal_adjustment=spec.expectedAdjustment;
  result.unit=spec.expectedUnit;
  result.metadata={publisher_series_id:matches[0].seriesID,
    expected_definition_from_publisher_documentation:spec.expectedDefinition,
    note:'API v1 does not supply independently validated title/base period; those remain pending publisher metadata check'};
  if(!Array.isArray(matches[0].data)) return {...result,error_category:'missing_observations'};
  const samples=matches[0].data.flatMap(p=>{
    if(!/^\d{4}$/.test(p?.year??'') || !/^M(0[1-9]|1[0-2])$/.test(p?.period??'') || !safeNumber(p?.value))return [];
    return [{period:p.year+'-'+p.period.slice(1),value:String(p.value)}];
  }).sort((a,b)=>a.period.localeCompare(b.period));
  if(!samples.length)return {...result,error_category:'no_usable_observations'};
  return {...result,outcome:'VERIFIED',verification_scope:'RECENT_SAMPLE_ONLY',
    first_evidenced:samples[0].period,last_evidenced:samples.at(-1).period,
    observations:samples.slice(-5),frequency:'Monthly',history_status:'SAMPLE_ONLY',
    error_category:null};
}
