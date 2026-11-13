// Read-only statement-index coverage crosswalk. Dates are not policy values.
import {readFile,writeFile} from 'node:fs/promises';
import {resolve,join} from 'node:path';
import {fileURLToPath} from 'node:url';
const manifest=JSON.parse(await readFile(new URL('./boj-historical-sources.json',import.meta.url)));
export function crosswalk(report,rows=manifest){
 const manifestDates=new Set(rows.map(row=>row[0]));
 const periods=report.periods.map(p=>{
   const listed=[...new Set(p.listed_dates)].sort();
   const selected=listed.filter(d=>manifestDates.has(d));
   const missing=listed.filter(d=>!manifestDates.has(d));
   return {year:p.year,index_status:p.census_status,listed_count:listed.length,
     selected_manifest_count:selected.length,selected_manifest_dates:selected,
     not_in_selected_manifest_count:missing.length,not_in_selected_manifest_dates:missing,
     coverage_status:p.census_status!=='PUBLISHER_INDEX_DATES_EXTRACTED'?'UNRESOLVED':
       missing.length?'SELECTED_MANIFEST_INCOMPLETE':'INDEX_DATES_IN_SELECTED_MANIFEST',
     economic_values_verified_by_crosswalk:false};
 });
 return {scope:'SELECTED_MANIFEST_VS_OFFICIAL_STATEMENT_INDEX',
   full_meeting_census_verified:false,production_approval:'NOT_APPROVED',
   periods,totals:{listed:periods.reduce((a,p)=>a+p.listed_count,0),
     selected:periods.reduce((a,p)=>a+p.selected_manifest_count,0),
     not_selected:periods.reduce((a,p)=>a+p.not_in_selected_manifest_count,0)}};
}
if(process.argv[1]&&resolve(process.argv[1])===fileURLToPath(import.meta.url)){
 if(!process.argv[2])throw Error('Disposable output directory required');
 const dir=process.argv[2];
 const report=JSON.parse(await readFile(join(dir,'boj_historical_census_discovery.json')));
 const result=crosswalk(report);
 await writeFile(join(dir,'boj_historical_manifest_coverage.json'),JSON.stringify(result,null,2)+'\n');
 console.log(JSON.stringify(result.totals));
}
