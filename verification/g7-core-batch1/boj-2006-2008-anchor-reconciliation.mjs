import {readFile,writeFile,mkdir} from 'node:fs/promises';
import {join,resolve} from 'node:path';
import {fileURLToPath} from 'node:url';

export function reconcileReviewQueue(queue,anchorData){
 const anchorByDate=new Map(anchorData.anchors.map(a=>[a.date,a]));
 const reviewed=queue.statement_dates.map(row=>{
  const anchor=anchorByDate.get(row.decision_date);
  const matching=anchor?.decision_url?[anchor.decision_url,anchor.source_url]:anchor?[anchor.source_url]:[];
  const source_match=!!anchor&&row.documents.some(d=>matching.includes(d.source_url));
  return {...row,anchor_candidate:anchor?{
   target_percent:anchor.target_percent,target_label:anchor.target_label,
   event:anchor.event,anchor_source_url:anchor.source_url,
   decision_document_linked:source_match,
   anchor_status:anchor.status
  }:null,policy_value_verified:false,
  verification_status:anchor?(source_match?'ANCHOR_LINK_MATCHED_DOCUMENT_CONTENT_REVIEW_PENDING':'ANCHOR_SOURCE_LINK_UNMATCHED'):'DOCUMENT_CONTENT_REVIEW_PENDING'};
 });
 return {scope:'BOJ_2006_2008_ANCHOR_TO_PUBLISHER_INDEX_RECONCILIATION',
  production_approval:'NOT_APPROVED',commercial_rights:'PENDING',
  full_history_verified:false,reviewed_statement_dates:reviewed.length,
  anchors_with_publisher_index_links:reviewed.filter(r=>r.anchor_candidate?.decision_document_linked).length,
  unmatched_anchors:anchorData.anchors.filter(a=>!reviewed.some(r=>r.decision_date===a.date&&r.anchor_candidate?.decision_document_linked)).map(a=>a.date),
  statement_dates:reviewed};
}
if(process.argv[1]&&resolve(process.argv[1])===fileURLToPath(import.meta.url)){
 if(!process.argv[2])throw Error('Disposable output directory required');
 const dir=process.argv[2];
 const queue=JSON.parse(await readFile(join(dir,'boj_2006_2008_document_review_queue.json'),'utf8'));
 const anchors=JSON.parse(await readFile(new URL('./boj-2006-2008-rate-regime-anchors.json',import.meta.url),'utf8'));
 const report=reconcileReviewQueue(queue,anchors);
 await mkdir(dir,{recursive:true});
 await writeFile(join(dir,'boj_2006_2008_anchor_index_reconciliation.json'),JSON.stringify(report,null,2)+'\n');
 console.log(JSON.stringify({statement_dates:report.reviewed_statement_dates,matched_anchors:report.anchors_with_publisher_index_links,unmatched_anchors:report.unmatched_anchors,production_approval:report.production_approval}));
}
