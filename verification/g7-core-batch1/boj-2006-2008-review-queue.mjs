import {historicalCensus} from './boj-historical-census.mjs';
import {mkdir,writeFile} from 'node:fs/promises';
import {join} from 'node:path';
import {resolve} from 'node:path';
import {fileURLToPath} from 'node:url';

export function buildDecisionReviewQueue(census){
 const years=[2006,2007,2008];
 const periods=years.map(year=>census.periods.find(p=>p.year===year));
 const missing_years=years.filter((year,i)=>!periods[i]||periods[i].census_status==='UNRESOLVED');
 const indexed=periods.filter(Boolean);
 const allDates=new Set(indexed.flatMap(p=>p.listed_dates??[]));
 const byDate=new Map();
 for(const p of indexed){
  for(const link of p.statement_links??[]){
   if(!allDates.has(link.date))continue;
   const documents=byDate.get(link.date)??[];
   if(!documents.some(d=>d.source_url===link.url))documents.push({
    source_url:link.url,source_title:link.title,
    title_classification:link.title_classification,
    original_document_verified:false,
    target_instrument:null,target_value_percent:null,
    verification_status:'ORIGINAL_DOCUMENT_REVIEW_REQUIRED'
   });
   byDate.set(link.date,documents);
  }
 }
 const statement_dates=[...allDates].sort().map(date=>({
  decision_date:date,source_index_year:Number(date.slice(0,4)),
  documents:byDate.get(date)??[],
  date_verification_status:(byDate.get(date)?.length??0)>0?'INDEX_LINKS_DISCOVERED':'MISSING_DOCUMENT_LINKS',
  policy_value_verified:false,target_instrument:null,target_value_percent:null,
  effective_date:null
 }));
 return {
  scope:'2006_2008_BOJ_STATEMENT_DOCUMENT_REVIEW_QUEUE',
  source:'ORIGINAL_BOJ_ANNUAL_STATEMENT_INDEX',
  complete_economic_series:false,historical_census_complete:false,
  production_approval:'NOT_APPROVED',commercial_rights:'PENDING',
  years_covered:years,missing_years,
  statement_dates,
  missing_document_links:statement_dates.filter(d=>d.documents.length===0).map(d=>d.decision_date),
  note:'Publisher statement index is not independently proven to enumerate all policy meetings; all linked documents retained without inferring values.'
 };
}
if(process.argv[1]&&resolve(process.argv[1])===fileURLToPath(import.meta.url)){
 if(!process.argv[2])throw Error('Disposable output directory required');
 const report=buildDecisionReviewQueue(await historicalCensus());
 await mkdir(process.argv[2],{recursive:true});
 await writeFile(join(process.argv[2],'boj_2006_2008_document_review_queue.json'),JSON.stringify(report,null,2)+'\n');
 console.log(JSON.stringify({years:report.years_covered,decision_dates:report.statement_dates.length,unlinked:report.missing_document_links.length,missing_years:report.missing_years,production_approval:report.production_approval}));
}
