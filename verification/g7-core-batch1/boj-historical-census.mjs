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
    let receipt={status:'UNRESOLVED',reason:'network_or_timeout'};
    let dates=null;
    try {
      const response=await transport(url,{method:'GET',redirect:'error',
        signal:AbortSignal.timeout(8000),headers:{accept:'text/html'}});
      const type=response.headers.get('content-type')?.split(';')[0].trim().toLowerCase();
      if(!response.ok || type!=='text/html'){
        await response.body?.cancel().catch(()=>{});
        receipt={status:'UNRESOLVED',http_status:response.status,
          reason:response.ok?'unexpected_content_type':'http_error'};
      } else {
        const reader=response.body?.getReader();
        if(!reader) throw Error('empty_body');
        let size=0; const chunks=[]; let oversized=false;
        try {
          while(true){
            const {done,value}=await reader.read();
            if(done) break;
            size+=value.byteLength;
            if(size>1024*1024){oversized=true;break;}
            chunks.push(Buffer.from(value));
          }
        } finally {await reader.cancel().catch(()=>{});}
        if(oversized) receipt={status:'UNRESOLVED',http_status:response.status,reason:'response_too_large'};
        else if(!size) receipt={status:'UNRESOLVED',http_status:response.status,reason:'empty_body'};
        else {
          const bytes=Buffer.concat(chunks);
          const {createHash}=await import('node:crypto');
          receipt={status:'SOURCE_RETRIEVED',http_status:response.status,
            content_sha256:createHash('sha256').update(bytes).digest('hex')};
          dates=archiveDates(bytes.toString('utf8'),year);
        }
      }
    } catch {receipt={status:'UNRESOLVED',reason:'network_or_timeout'};}
    periods.push({year,url,source_status:receipt.status,http_status:receipt.http_status??null,
      content_sha256:receipt.content_sha256??null,
      census_status:dates?'PUBLISHER_INDEX_DATES_EXTRACTED':'UNRESOLVED',
      listed_dates:dates??[],listed_date_count:dates?.length??0,
      reason:dates?null:receipt.reason??'archive_table_unproven'});
  }
  return {scope:'HISTORICAL_STATEMENT_INDEX_DATES_ONLY',historical_completeness:'PARTIAL',
    meeting_census_verified:false,production_approval:'NOT_APPROVED',periods};
}

if(process.argv[1]&&resolve(process.argv[1])===fileURLToPath(import.meta.url)){
  if(!process.argv[2]) throw Error('Disposable output directory required');
  const report=await historicalCensus();
  await mkdir(process.argv[2],{recursive:true});
  await writeFile(join(process.argv[2],'boj_historical_census_discovery.json'),JSON.stringify(report,null,2)+'\n');
  console.log(JSON.stringify({years:report.periods.length,unresolved:report.periods.filter(p=>p.census_status==='UNRESOLVED').length}));
}
