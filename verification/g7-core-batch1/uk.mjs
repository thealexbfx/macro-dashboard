// First-party UK candidate checks. All verification remains recent-sample-only.
import {publisherRequest,safeNumber,safeText} from './publisher-http.mjs';
const months={JAN:'01',FEB:'02',MAR:'03',APR:'04',MAY:'05',JUN:'06',
  JUL:'07',AUG:'08',SEP:'09',OCT:'10',NOV:'11',DEC:'12'};
const blocked = e => e==='network_or_timeout'||/^http_/.test(e);

// Diagnostic intentionally records field names and JSON types only: never
// response bodies, observation values, descriptions, access tokens or cookies.
// The exact publisher payload stays out of public workflow artifacts.
export function onsShapeDiagnostic(payload) {
  const fields = value => value && typeof value === 'object' && !Array.isArray(value)
    ? Object.keys(value).filter(key => /^[a-zA-Z][a-zA-Z0-9_]{0,49}$/.test(key))
      .slice(0, 24).sort() : [];
  const kind = value => Array.isArray(value) ? 'array' : value===null ? 'null' : typeof value;
  const detail = payload && typeof payload === 'object' && !Array.isArray(payload)
    ? payload.description : null;
  return {
    schema_only: true,
    root_type: kind(payload),
    root_keys: fields(payload),
    description_type: kind(detail),
    description_keys: fields(detail),
    cdid_type: kind(payload?.cdid),
    nested_cdid_type: kind(detail?.cdid),
    nested_title_type: kind(detail?.description),
    root_title_type: kind(payload?.description),
    months_type: kind(payload?.months),
    months_count: Array.isArray(payload?.months) ? payload.months.length : null,
    first_month_keys: Array.isArray(payload?.months) ? fields(payload.months[0]) : [],
  };
}

export async function verifyOns(row, original, spec, transport=fetch, delay=async()=>{}) {
  const url='https://www.ons.gov.uk/'+spec.path+'/data';
  const result={...original,source_url:url,publisher_series_id:spec.seriesId,
    publisher_discovery_url:'https://www.ons.gov.uk/'+spec.path,
    rights_note:'ONS Open Government Licence applicability, attribution, exceptions and commercial export remain pending.',
    error_category:null};
  const receipt=await publisherRequest(url,{transport,delay,maxBytes:2097152});
  result.http_status=receipt.http_status;
  result.api_receipts=[{url,http_status:receipt.http_status,retrieved_utc:receipt.retrieved_utc,error:receipt.error??null}];
  if(receipt.error)return {...result,outcome:blocked(receipt.error)?'ACCESS_BLOCKED':'UNRESOLVED',
    access_status:blocked(receipt.error)?'BLOCKED':'RETRIEVED',error_category:receipt.error};
  result.access_status='RETRIEVED';
  let obj;try{obj=JSON.parse(receipt.text);}catch{return {...result,error_category:'invalid_json'};}
  if(!obj||typeof obj!=='object'||Array.isArray(obj))
    return {...result,error_category:'missing_series_metadata',ons_response_shape:onsShapeDiagnostic(obj)};
  // ONS time-series responses may contain the descriptive fields in a
  // nested description object, while test/legacy payloads expose flat fields.
  const detail=typeof obj.description==='object' && obj.description!==null &&
    !Array.isArray(obj.description) ? obj.description : obj;
  const title=typeof detail.description==='string' ? detail.description : null;
  const cdid=detail.cdid ?? obj.cdid;
  const dataset=detail.datasetId ?? detail.dataset ?? obj.dataset;
  if(!title || typeof cdid!=='string' || !cdid.trim())
    return {...result,error_category:'missing_series_metadata',ons_response_shape:onsShapeDiagnostic(obj)};
  result.definition=safeText(title);
  result.metadata={description:safeText(title),cdid:safeText(cdid),dataset:safeText(dataset),
    unit:safeText(detail.unit ?? obj.unit)};
  if(cdid.toUpperCase()!==spec.seriesId)
    return {...result,outcome:'MISMATCH',identity_status:'MISMATCH',error_category:'cdid_conflict'};
  if(!new RegExp(spec.expectedLabel,'i').test(title))
    return {...result,outcome:'MISMATCH',identity_status:'MISMATCH',error_category:'title_conflict'};
  result.identity_status='PUBLISHER_ID_AND_LABEL_MATCHED';
  // ONS MGSX is a rolling three-month labour-market estimate; do not call it a single-month measure.
  const entries=Array.isArray(obj.months)?obj.months:[];
  const samples=entries.flatMap(p=>{
    const match=/^(\d{4})\s+([A-Za-z]{3})$/.exec(p?.date??'');
    if(!match||!months[match[2].toUpperCase()]||!safeNumber(p?.value))return [];
    return [{period:match[1]+'-'+months[match[2].toUpperCase()],value:String(p.value)}];
  }).sort((a,b)=>a.period.localeCompare(b.period));
  if(!samples.length)return {...result,error_category:'no_usable_monthly_observations'};
  return {...result,outcome:'VERIFIED',verification_scope:'RECENT_SAMPLE_ONLY',
    frequency:spec.frequency,unit:spec.expectedUnit,seasonal_adjustment:spec.expectedAdjustment,
    observations:samples.slice(-5),first_evidenced:samples.at(-5)?.period??samples[0].period,
    last_evidenced:samples.at(-1).period,history_status:'SAMPLE_ONLY'};
}

export async function verifyBoe(row, original, spec, transport=fetch, delay=async()=>{}) {
  const now=new Date();
  const start=new Date(now);start.setUTCDate(start.getUTCDate()-120);
  const fmt=d=>String(d.getUTCDate()).padStart(2,'0')+'/'+
    Object.keys(months)[d.getUTCMonth()][0]+Object.keys(months)[d.getUTCMonth()].slice(1).toLowerCase()+'/'+d.getUTCFullYear();
  const args=new URLSearchParams({'csv.x':'yes',Datefrom:fmt(start),Dateto:fmt(now),
    SeriesCodes:spec.seriesId,CSVF:'TN',UsingCodes:'Y',VPD:'Y',VFD:'N'});
  const url='https://www.bankofengland.co.uk/boeapps/database/_iadb-fromshowcolumns.asp?'+args;
  const result={...original,source_url:url,publisher_series_id:spec.seriesId,
    publisher_discovery_url:spec.discoveryUrl,
    rights_note:'BoE IADB terms, publication/licensing exceptions, attribution and commercial export require explicit review.',
    error_category:null};
  const receipt=await publisherRequest(url,{transport,delay,maxBytes:131072,accept:'text/csv'});
  result.http_status=receipt.http_status;
  result.api_receipts=[{url,http_status:receipt.http_status,retrieved_utc:receipt.retrieved_utc,error:receipt.error??null}];
  if(receipt.error)return {...result,outcome:blocked(receipt.error)?'ACCESS_BLOCKED':'UNRESOLVED',
    access_status:blocked(receipt.error)?'BLOCKED':'RETRIEVED',error_category:receipt.error};
  result.access_status='RETRIEVED';
  const lines=receipt.text.trim().split(/\r?\n/);
  if(lines.length<2)return {...result,error_category:'empty_csv'};
  const header=lines[0].replace(/^\uFEFF/,'').split(',').map(s=>s.replace(/^"|"$/g,'').trim().toUpperCase());
  const dateIndex=header.indexOf('DATE'),rateIndex=header.indexOf(spec.seriesId);
  if(dateIndex<0||rateIndex<0)return {...result,error_category:'missing_boe_csv_header'};
  result.identity_status='PUBLISHER_SERIES_COLUMN_MATCHED';
  const samples=lines.slice(1).flatMap(line=>{
    const cells=line.split(',').map(s=>s.trim().replace(/^"|"$/g,''));
    const m=/^(\d{1,2})\s+([A-Za-z]{3})\s+(\d{4})$/.exec(cells[dateIndex]??'');
    if(!m||!months[m[2].toUpperCase()]||!safeNumber(cells[rateIndex]))return [];
    return [{period:m[3]+'-'+months[m[2].toUpperCase()]+'-'+m[1].padStart(2,'0'),value:cells[rateIndex]}];
  }).sort((a,b)=>a.period.localeCompare(b.period));
  if(!samples.length)return {...result,error_category:'no_usable_rate_observations'};
  return {...result,outcome:'VERIFIED',verification_scope:'RECENT_SAMPLE_ONLY',
    definition:'Bank of England Official Bank Rate',frequency:'Daily observations of policy rate',
    unit:'Percent',seasonal_adjustment:'Not applicable',history_status:'SAMPLE_ONLY',
    observations:samples.slice(-5),first_evidenced:samples.at(-5)?.period??samples[0].period,
    last_evidenced:samples.at(-1).period};
}
