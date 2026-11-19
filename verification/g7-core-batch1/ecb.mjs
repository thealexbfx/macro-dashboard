import {publisherRequest, safeNumber, safeText} from './publisher-http.mjs';
// Data source: https://data.ecb.europa.eu/help/api/data
// The key is for the *euro area*, and is reused by DE/FR/IT mappings.
const ROOT='https://data-api.ecb.europa.eu/service/data/';
function csvRows(text) {
  const rows=[],maxRows=35;let row=[],value='',quoted=false;
  for(let i=0;i<text.length;i++){
    const ch=text[i];
    if(ch==='"') {if(quoted&&text[i+1]==='"'){value+='"';i++;}else quoted=!quoted;}
    else if(ch===','&&!quoted){row.push(value);value='';}
    else if((ch==='\n'||ch==='\r')&&!quoted) {
      if(ch==='\r'&&text[i+1]==='\n')i++;
      row.push(value);value='';
      if(row.some(v=>v!==''))rows.push(row);
      if(rows.length>maxRows)throw Error('too_many_csv_rows');
      row=[];
    }else value+=ch;
  }
  if(quoted)throw Error('unclosed_csv_quote');
  if(value||row.length){row.push(value);rows.push(row);}
  return rows;
}
export async function verifyEcb(row, original, spec, transport=fetch, delay=async()=>{}) {
  const url=ROOT+'FM/'+encodeURIComponent(spec.seriesKey)+'?lastNObservations=5&format=csvdata';
  const result={...original,publisher_series_id:spec.seriesKey,
    source_url:url,publisher_discovery_url:spec.discoveryUrl,canonical_series_key:'ECB:'+spec.seriesKey,
    rights_note:'ECB data license and third-party provider attribution must be checked for commercial display and export.',
    error_category:null};
  const response=await publisherRequest(url,{accept:'text/csv',transport,delay});
  result.http_status=response.http_status;
  result.api_receipts=[{url,http_status:response.http_status,retrieved_utc:response.retrieved_utc,
    error:response.error??null}];
  if(response.error){
    const blocked=response.error==='network_or_timeout'||/^http_/.test(response.error);
    return {...result,outcome:blocked?'ACCESS_BLOCKED':'UNRESOLVED',
      access_status:blocked?'BLOCKED':'RETRIEVED',error_category:response.error};
  }
  result.access_status='RETRIEVED';
  let rows;
  try{rows=csvRows(response.text);}catch{return {...result,error_category:'invalid_csv'};}
  if(rows.length<2)return {...result,error_category:'no_csv_rows'};
  const head=rows[0];
  const ix=name=>head.indexOf(name);
  if(ix('TIME_PERIOD')<0||ix('OBS_VALUE')<0 || ix('FREQ')<0 || ix('REF_AREA')<0 ||
     ix('PROVIDER_FM_ID')<0) {
    return {...result,error_category:'missing_required_ecb_dimensions'};
  }
  const keyIndex=ix('KEY');
  const matches=rows.slice(1).filter(values=>values.length===head.length);
  const mismatches=matches.filter(v=>v[ix('REF_AREA')]!=='U2'||v[ix('FREQ')]!=='B'||
    v[ix('PROVIDER_FM_ID')]!=='DFR'||(keyIndex>=0&&v[keyIndex]!=='FM.'+spec.seriesKey));
  if(mismatches.length) return {...result,outcome:'MISMATCH',identity_status:'MISMATCH',
    error_category:'ecb_dimension_conflict',mismatch_notes:'ECB response dimensions differ from requested euro-area deposit facility rate'};
  result.identity_status='PUBLISHER_DIMENSIONS_MATCHED';
  result.definition=spec.expectedDefinition;result.unit='Percent per annum';
  result.frequency='Business daily';result.seasonal_adjustment='Not applicable';
  result.metadata={series_key:spec.seriesKey,reference_area:'U2',instrument:'DFR',
    validation:'Returned ECB response dimensions; independent full history not checked'};
  const samples=matches.flatMap(v=>
    /^\d{4}-\d{2}-\d{2}$/.test(v[ix('TIME_PERIOD')]) && safeNumber(v[ix('OBS_VALUE')])
    ? [{period:v[ix('TIME_PERIOD')],value:v[ix('OBS_VALUE')]}]:[])
    .sort((a,b)=>a.period.localeCompare(b.period));
  if(!samples.length)return {...result,error_category:'no_usable_observations'};
  return {...result,outcome:'VERIFIED',verification_scope:'RECENT_SAMPLE_ONLY',
    first_evidenced:samples[0].period,last_evidenced:samples.at(-1).period,
    observations:samples.slice(-5),history_status:'SAMPLE_ONLY',error_category:null};
}
