import {historicalCensus} from './boj-historical-census.mjs';
import {mkdir,writeFile} from 'node:fs/promises';
import {join} from 'node:path';
import {resolve} from 'node:path';
import {fileURLToPath} from 'node:url';

export function buildDecisionReviewQueue(census){
 const years=[2006,2007,2008];
 const periods=census.periods.filter(p=>years.includes(p.year));
 const decisions=periods.flatMap(p=>p.statement_links
  .filter(link=>/Announcement of the Monetary Policy Meeting Decisions|Statement on Monetary Policy|On Monetary Policy Decisions/i.test(link.title))
  .map(link=>({
   decision_date:link.date,source_url:link.url,source_title:link.title,
   source_index_year:p.year,
   title_classification:link.title_classification,
   original_document_verified:false,
   target_instrument:null,target_value_percent:null,
   effective_date:null,verification_status:'ORIGINAL_DOCUMENT_REVIEW_REQUIRED'
  })));
 const unique=new Map();
 for(const d of decisions){
  const existing=unique.get(d.decision_date);
  if(!existing||(/Change in|On Monetary Policy Decisions/i.test(d.source_title)&&!/Change in|On Monetary Policy Decisions/i.test(existing.source_title)))unique.set(d.decision_date,d);
 }
 return {
  scope:'2006_2008_BOJ_DECISION_DOCUMENT_REVIEW_QUEUE',
  source:'ORIGINAL_BOJ_ANNUAL_STATEMENT_INDEX',
  complete_economic_series:false,
  historical_census_complete:false,
  production_approval:'NOT_APPROVED',
  commercial_rights:'PENDING',
  years_covered:years,
  statement_dates: [...unique.values()].sort((a,b)=>a.decision_date.localeCompare(b.decision_date)),
  missing_document_links:periods.flatMap(p=>p.dates_without_statement_links.map(date=>({year:p.year,date})))
 };
}
if(process.argv[1]&&resolve(process.argv[1])===fileURLToPath(import.meta.url)){
 if(!process.argv[2])throw Error('Disposable output directory required');
 const report=buildDecisionReviewQueue(await historicalCensus());
 await mkdir(process.argv[2],{recursive:true});
 await writeFile(join(process.argv[2],'boj_2006_2008_document_review_queue.json'),JSON.stringify(report,null,2)+'\n');
 console.log(JSON.stringify({years:report.years_covered,decision_dates:report.statement_dates.length,unlinked:report.missing_document_links.length,production_approval:report.production_approval}));
}
