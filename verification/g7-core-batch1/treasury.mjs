// Original US Treasury 10-year nominal par curve, read-only sample verification.
// See: https://home.treasury.gov/treasury-daily-interest-rate-xml-feed
import {publisherRequest,safeNumber} from './publisher-http.mjs';

export function parseTreasuryAtom(xml, field='BC_10YEAR') {
  if (typeof xml!=='string' || !xml.startsWith('<?xml') && !xml.includes('<feed')) return null;
  // Parse bounded, fixed-schema Atom entry contents. No general-purpose XML
  // entity expansion, external resources, dynamic selectors, or HTML fallback.
  if (!/^BC_(10YEAR)$/.test(field) || /<!DOCTYPE|<!ENTITY/i.test(xml)) return null;
  const entries=[...xml.matchAll(/<(?:[a-z]+:)?entry(?:\s[^>]*)?>([\s\S]*?)<\/(?:[a-z]+:)?entry>/gi)];
  if(entries.length>60)return null;
  const get=(body,key)=>{
    const match=body.match(new RegExp('<(?:[a-z]+:)?'+key+'(?:\\s[^>]*)?>([^<]+)<\\/(?:[a-z]+:)?'+key+'>','i'));
    return match?.[1]?.trim() ?? null;
  };
  return entries.flatMap(([,entry])=>{
    const d=get(entry,'NEW_DATE')?.slice(0,10),v=get(entry,field);
    if(!/^\d{4}-\d{2}-\d{2}$/.test(d??'') || !safeNumber(v))return [];
    return [{period:d,value:v}];
  }).sort((a,b)=>a.period.localeCompare(b.period));
}

export async function verifyTreasury(row,original,spec,transport=fetch,delay=async()=>{}) {
  const now=new Date();
  const month=String(now.getUTCFullYear())+String(now.getUTCMonth()+1).padStart(2,'0');
  const url='https://home.treasury.gov/resource-center/data-chart-center/interest-rates/pages/xml?data=daily_treasury_yield_curve&field_tdr_date_value_month='+month;
  const result={...original,source_url:url,publisher_series_id:spec.seriesId,
    publisher_discovery_url:spec.discoveryUrl,
    rights_note:'Treasury nominal benchmark curve may incorporate third-party quotations; review attribution, commercial display and export rights separately.',
    error_category:null};
  const response=await publisherRequest(url,{transport,delay,accept:'application/xml',maxBytes:524288});
  result.http_status=response.http_status;
  result.api_receipts=[{url,http_status:response.http_status,retrieved_utc:response.retrieved_utc,error:response.error??null}];
  if(response.error){
    const blocked=response.error==='network_or_timeout'||/^http_/.test(response.error);
    return {...result,outcome:blocked?'ACCESS_BLOCKED':'UNRESOLVED',
      access_status:blocked?'BLOCKED':'RETRIEVED',error_category:response.error};
  }
  result.access_status='RETRIEVED';
  const points=parseTreasuryAtom(response.text,spec.seriesId);
  if(!points)return {...result,error_category:'unexpected_xml_structure'};
  if(!points.length)return {...result,error_category:'no_usable_observations'};
  result.identity_status='PUBLISHER_FEED_FIELD_MATCHED';
  result.definition='Daily Treasury par yield curve, 10-year nominal constant maturity';
  result.frequency='Daily (business days)';result.unit='Percent per annum';
  result.seasonal_adjustment='Not applicable';
  return {...result,outcome:'VERIFIED',verification_scope:'RECENT_SAMPLE_ONLY',
    observations:points.slice(-5),first_evidenced:points.at(-5)?.period??points[0].period,
    last_evidenced:points.at(-1).period,history_status:'SAMPLE_ONLY'};
}
