// Development-only historical meeting-date census. No numeric economic observations.
import {readFile,mkdir,writeFile} from 'node:fs/promises';
import {join,resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
import {archiveDates} from './boj-historical-policy.mjs';
import {probeSource} from './boj-historical-gap-sources.mjs';

export const censusYears=[2006,2007,2008,2016,2017,2018,2019,2020,2021,2022,2023];
export async function historicalCensus({transport=fetch}={}) {
  const periods=[];
  for(const year of censusYears) {
    const url='https://www.boj.or.jp/en/mopo/mpmdeci/state_'+year+'/index.htm';
    const receipt=await probeSource(url,transport);
    // Connectivity receipts alone do not include original HTML. The census
    // remains unresolved until a bounded publisher-body parser is integrated.
    periods.push({year,url,source_status:receipt.status,content_sha256:receipt.content_sha256??null,
      census_status:'UNRESOLVED',listed_dates:[],reason:receipt.status==='SOURCE_RETRIEVED_NOT_ECONOMICALLY_VERIFIED'?
        'publisher_body_not_yet_parsed':'source_not_retrieved'});
  }
  return {scope:'HISTORICAL_MEETING_CENSUS_DISCOVERY',historical_completeness:'PARTIAL',
    production_approval:'NOT_APPROVED',periods};
}
if(process.argv[1]&&resolve(process.argv[1])===fileURLToPath(import.meta.url)){
  if(!process.argv[2]) throw Error('Disposable output directory required');
  const report=await historicalCensus();
  await mkdir(process.argv[2],{recursive:true});
  await writeFile(join(process.argv[2],'boj_historical_census_discovery.json'),JSON.stringify(report,null,2)+'\n');
  console.log(JSON.stringify({years:report.periods.length,unresolved:report.periods.filter(p=>p.census_status==='UNRESOLVED').length}));
}
