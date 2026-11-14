// Development-only historical meeting-date census. No numeric economic observations.
import {readFile,mkdir,writeFile} from 'node:fs/promises';
import {join,resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
import {archiveDates} from './boj-historical-policy.mjs';
import {probeSource} from './boj-historical-gap-sources.mjs';

export function classifyStatementTitle(title) {
 const t=title.replace(/<[^>]*>/g,' ').replace(/&nbsp;|&#160;/gi,' ').replace(/\s+/g,' ').toLowerCase();
 if(/policy unchanged|unchanged|no change/.test(t))return 'TITLE_SAYS_UNCHANGED_NOT_DOCUMENT_VERIFIED';
 if(/change in the guideline|on monetary policy decisions|monetary easing|yield curve control/.test(t))
   return 'REQUIRES_ORIGINAL_DOCUMENT_REVIEW';
 return 'UNCLASSIFIED';
}
export const censusYears=[2006,2007,2008,2016,2017,2018,2019,2020,2021,2022,2023];
export async function historicalCensus({transport=fetch}={}) {
  const periods=[];
  for(const year of censusYears) {
    const url='https://www.boj.or.jp/en/mopo/mpmdeci/state_'+year+'/index.htm';
    let receipt={status:'UNRESOLVED',reason:'network_or_timeout'};
    let dates=null;
    let statement_links=[];
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
          const html=bytes.toString('utf8');
          dates=archiveDates(html,year);
          // Extract linked documents only within the annual statement table.
          const tables=[...html.matchAll(/<table\b[^>]*>[\s\S]*?<\/table>/gi)].map(x=>x[0]);
          const table=tables.find(t=>/<th\b[^>]*>\s*Date\s*<\/th>/i.test(t)&&/<th\b[^>]*>\s*Title\s*<\/th>/i.test(t))??'';
          const rows=[...table.matchAll(/<tr\b[^>]*>([\s\S]*?)<\/tr>/gi)];
          for(const row of rows){
            const cells=[...row[1].matchAll(/<td\b[^>]*>([\s\S]*?)<\/td>/gi)].map(x=>x[1]);
            if(cells.length<2)continue;
            const dateText=cells[0].replace(/<[^>]*>/g,' ').replace(/&nbsp;|&#160;|&#x[a-f0-9]+;/gi,' ').replace(/\s+/g,' ').trim();
            const match=dateText.match(/([A-Za-z]+)\.?\s+(\d{1,2}),?\s+(\d{4})/);
            if(!match)continue;
            const month=['jan','feb','mar','apr','may','jun','jul','aug','sep','oct','nov','dec'].indexOf(match[1].slice(0,3).toLowerCase())+1;
            if(!month||Number(match[3])!==year)continue;
            const date=match[3]+'-'+String(month).padStart(2,'0')+'-'+match[2].padStart(2,'0');
            if(!dates?.includes(date))continue;
            for(const link of cells[1].matchAll(/<a\b[^>]*href=["']([^"'#]+)["'][^>]*>([\s\S]*?)<\/a>/gi)){
              let absolute;
              try { absolute=new URL(link[1],url); } catch { continue; }
              if(absolute.protocol!=='https:'||absolute.hostname!=='www.boj.or.jp')continue;
              const title=link[2].replace(/<[^>]*>/g,' ').replace(/&nbsp;|&#160;|&#x[a-f0-9]+;/gi,' ').replace(/\s+/g,' ').trim();
              statement_links.push({date,url:absolute.href,title,title_classification:classifyStatementTitle(title),
                document_verified:false});
            }
          }
        }
      }
    } catch {receipt={status:'UNRESOLVED',reason:'network_or_timeout'};}
    periods.push({year,url,source_status:receipt.status,http_status:receipt.http_status??null,
      content_sha256:receipt.content_sha256??null,
      census_status:dates?'PUBLISHER_INDEX_DATES_EXTRACTED':'UNRESOLVED',
      listed_dates:dates??[],listed_date_count:dates?.length??0,
      statement_links,statement_link_count:statement_links.length,
      dates_without_statement_links:(dates??[]).filter(d=>!statement_links.some(l=>l.date===d)),
      document_link_coverage_status:!dates?'UNRESOLVED':(dates.every(d=>statement_links.some(l=>l.date===d))?'ALL_INDEX_DATES_LINKED':'LINKS_MISSING'),
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
  console.log(JSON.stringify({years:report.periods.length,unresolved:report.periods.filter(p=>p.census_status==='UNRESOLVED').length,
    statement_links:report.periods.reduce((n,p)=>n+p.statement_link_count,0),
    unlinked_dates:report.periods.reduce((n,p)=>n+p.dates_without_statement_links.length,0)}));
}
