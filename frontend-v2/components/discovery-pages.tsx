'use client';
import {useEffect,useState} from 'react';
import {request} from '../lib/contracts';
import type {DiscoveryFinding,DiscoveryPage,DiscoverySummary} from '../lib/discovery';
import {Button} from './ui/button';
import {dateLabel} from '../lib/presentation';

export function DiscoveryPages({state,category='all',start=0,renderFinding}:{state:'archived'|'following';category?:string;start?:number;renderFinding:(f:DiscoveryFinding)=>React.ReactNode}){
 const [offset,setOffset]=useState(start),[page,setPage]=useState<DiscoveryPage<DiscoverySummary>|null>(null),[details,setDetails]=useState<Record<string,DiscoveryFinding>>({}),[pending,setPending]=useState(''),[error,setError]=useState(''),[reload,setReload]=useState(0);
 useEffect(()=>{setOffset(start);setDetails({});},[start,state,category]);
 useEffect(()=>{const c=new AbortController();setError('');setPage(null);request<DiscoveryPage<DiscoverySummary>>(`discovery/stories?state=${state}&kind=${encodeURIComponent(category)}&limit=20&offset=${offset}`,undefined,c.signal).then(setPage).catch(e=>{if(e.name!=='AbortError')setError(e.message);});return()=>c.abort();},[state,category,offset,reload]);
 async function load(id:string){setPending(id);setError('');try{const f=await request<DiscoveryFinding>('discovery/stories/'+encodeURIComponent(id));setDetails(v=>({...v,[id]:f}));}catch(e){setError((e as Error).message);}finally{setPending('');}}
 return <>{error&&<p role="alert" className="notice">{error}<Button variant="outline" onClick={()=>{setOffset(start);setReload(v=>v+1);}}>Retry loading</Button></p>}{!page&&!error&&<p role="status" className="quiet">Loading discovery summaries…</p>}<div className="discovery-grid">{page?.items.map(s=>details[s.id]?<div key={s.id}>{renderFinding(details[s.id])}</div>:<article className="card discovery-story" key={s.id}><span className="lifecycle">{s.status==='Ongoing'?'Following':s.status}</span><h3>{s.headline}</h3><p className="quiet">{dateLabel(s.observation_date)} · {s.frequency} · evidence version {s.evidence_version}</p><Button variant="outline" disabled={!!pending} onClick={()=>load(s.id)}>{pending===s.id?'Loading evidence…':'Open evidence'}</Button></article>)}</div>{page&&<div className="discovery-actions"><Button variant="outline" disabled={offset<=start} onClick={()=>{setDetails({});setOffset(Math.max(start,offset-20));}}>Previous</Button><span className="quiet">{page.items.length?offset+1:0}–{offset+page.items.length} of {page.total}</span><Button variant="outline" disabled={page.next_offset===null} onClick={()=>{setDetails({});setOffset(page.next_offset!);}}>Next</Button></div>}</>;
}
