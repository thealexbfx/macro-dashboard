'use client';
import { useEffect, useState } from 'react';
import { Star } from 'lucide-react';
import { request, type Dataset } from '../lib/contracts';
import { DatasetMetadata } from './data-widgets';
import { formatDatasetValue, referenceLabel, freshness } from '../lib/presentation';
import { Button } from './ui/button';

export interface CatalogPage {items:Dataset[];total:number;offset:number;limit:number;next_offset:number|null;facets:Record<string,string[]>}
export function CatalogExplorer({selected,favorites,onFavorite,onToggle,onCompare,onMetadata}:{selected:string[];favorites:string[];onFavorite:(id:string)=>void;onToggle:(id:string)=>void;onCompare:()=>void;onMetadata:(rows:Dataset[])=>void}) {
    const [query,setQuery]=useState(''),[filters,setFilters]=useState<Record<string,string>>({}),[offset,setOffset]=useState(0),[onlyFav,setOnlyFav]=useState(false),[page,setPage]=useState<CatalogPage|null>(null),[rows,setRows]=useState<Dataset[]>([]),[error,setError]=useState(''),[loading,setLoading]=useState(true),[revision,setRevision]=useState(0);
    const favoritesKey=JSON.stringify(favorites);
    useEffect(()=>{
        const controller=new AbortController();setLoading(true);setError('');setRows([]);
        const timer=setTimeout(async()=>{
            try {
                const result=await request<CatalogPage>('catalog/search',{query,...filters,offset,limit:12,...(onlyFav?{ids:JSON.parse(favoritesKey)}:{})},controller.signal);
                if(controller.signal.aborted)return;
                setPage(result);setRows(result.items);onMetadata(result.items);
                // At most three bounded preview requests in flight, for this visible page only.
                let index=0;
                await Promise.all(Array.from({length:3},async()=>{while(index<result.items.length&&!controller.signal.aborted){const item=result.items[index++];try{const p=await request<{dataset:Dataset}>(`observations/${encodeURIComponent(item.id)}?preview=true&limit=24`,undefined,controller.signal);if(!controller.signal.aborted){setRows(current=>current.map(r=>r.id===item.id?p.dataset:r));onMetadata([p.dataset]);}}catch(e){if(!controller.signal.aborted)setRows(current=>current.map(r=>r.id===item.id?{...r,message:(e as Error).message}:r));}}}));
            } catch(e){if(!controller.signal.aborted)setError((e as Error).message);}
            finally{if(!controller.signal.aborted)setLoading(false);}
        },200);
        return()=>{clearTimeout(timer);controller.abort();};
    },[query,filters,offset,onlyFav,favoritesKey,revision,onMetadata]);
    function filter(key:string,value:string){setFilters(f=>({...f,[key]:value}));setOffset(0);}
    return <><div className="toolbar filters"><label className="search"><input aria-label="Search datasets" placeholder="Search datasets or sources…" value={query} onChange={e=>{setQuery(e.target.value);setOffset(0);}}/></label>{(['category','region','provider','frequency'] as const).map(key=><label key={key}>{key==='region'?'Country / region':key[0].toUpperCase()+key.slice(1)}<select aria-label={`Catalog ${key}`} value={filters[key]||''} onChange={e=>filter(key,e.target.value)}><option value="">All {key==='category'?'categories':key==='frequency'?'frequencies':`${key}s`}</option>{page?.facets[key]?.map(v=><option key={v}>{v}</option>)}</select></label>)}<Button variant="outline" onClick={()=>{setOnlyFav(v=>!v);setOffset(0);}}>{onlyFav?'Favourites only':'All datasets'}</Button><Button variant="outline" onClick={()=>setRevision(v=>v+1)}>Refresh</Button></div>
        {loading&&<p role="status">Loading catalog page and bounded previews…</p>}{error&&<div role="alert">{error} <Button onClick={()=>setRevision(v=>v+1)}>Retry catalog</Button></div>}
        <div className="card table-wrap"><table><thead><tr><th>Dataset / source</th><th>Category / region</th><th>Frequency / units</th><th>Latest reference</th><th>Favourite</th><th>Compare</th></tr></thead><tbody>{rows.map(d=><tr key={d.id}><td><b>{d.name}</b><small>{d.source} · {d.provider_id}</small><DatasetMetadata dataset={d}/></td><td>{d.category}<small>{d.region}</small></td><td>{d.frequency}<small>{d.units}</small></td><td>{referenceLabel(d)}<small>{freshness(d)}</small><b>{formatDatasetValue(d)}</b>{d.status==='unavailable'&&<small>{d.message}</small>}</td><td><button aria-label={`Favourite ${d.name}`} aria-pressed={favorites.includes(d.id)} onClick={()=>onFavorite(d.id)}><Star size={17} fill={favorites.includes(d.id)?'#edb867':'none'}/></button></td><td><input type="checkbox" aria-label={`Compare ${d.name}`} checked={selected.includes(d.id)} disabled={!selected.includes(d.id)&&selected.length>=4} onChange={()=>onToggle(d.id)}/></td></tr>)}</tbody></table>{!loading&&!error&&!rows.length&&<p>No public datasets match these filters. Unavailable favourites remain saved.</p>}
        <div className="table-bottom"><span>{page?.total||0} public datasets · Page {Math.floor(offset/12)+1}</span><Button variant="outline" disabled={!offset||loading} onClick={()=>setOffset(Math.max(0,offset-12))}>Previous page</Button><Button variant="outline" disabled={page?.next_offset==null||loading} onClick={()=>setOffset(page!.next_offset!)}>Next page</Button><Button disabled={!selected.length} onClick={onCompare}>Compare selected ({selected.length}/4)</Button></div></div></>;
}
