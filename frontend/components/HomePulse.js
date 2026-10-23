'use client';
import {useEffect,useState} from 'react';
import {getHomeSnapshot} from '@/lib/api';

function changeText(m){if(m.change==null)return '—';return `${m.change>0?'+':''}${m.change.toFixed(2)}${m.unit==='bp'?' bp':'%'}`}
export default function HomePulse({onAsk}){
 const[data,setData]=useState(null);const[failed,setFailed]=useState(false);
 useEffect(()=>{getHomeSnapshot().then(setData).catch(()=>setFailed(true))},[]);
 if(failed)return <section className="pulse"><div className="pulseTitle"><div><span className="eyebrow">LIVE RESEARCH ENTRY POINTS</span><h2>Start with the question.</h2></div><p>Live homepage data is temporarily unavailable. Ask MacroLens directly — research services remain separate from this homepage snapshot.</p></div></section>;
 if(!data)return <section className="pulse"><div className="pulseTitle"><div><span className="eyebrow">WHAT’S MOVING</span><h2>Loading the market picture…</h2></div></div><div className="moverGrid">{[1,2,3,4,5].map(x=><div className="mover skeleton" key={x}/>)}</div></section>;
 return <>
  {data.moves?.length>0&&<section className="pulse"><div className="pulseTitle"><div><span className="eyebrow">WHAT’S MOVING</span><h2>See the move. Investigate the why.</h2></div><p>Latest available daily observations. A move is evidence — not an explanation.</p></div><div className="moverGrid">{data.moves.map(m=><button className="mover" key={m.key} onClick={()=>onAsk(m.question)}><div><span>{m.name}</span><small>As of {m.as_of_date}</small></div><strong className={m.change>0?'up':m.change<0?'down':''}>{changeText(m)}</strong><i>Investigate →</i></button>)}</div></section>}
  {data.macro&&<section className="now"><div><span className="eyebrow">WHAT MATTERS RIGHT NOW</span><h2>{data.macro.environment_label||'The current US macro picture'}</h2><p>MacroLens’ latest US environment classification. Use it as context for market questions, not as a standalone trading signal.</p><button onClick={()=>onAsk('What is the current US macro picture?')}>Investigate the US economy →</button></div><div className="nowMetrics"><div><small>Activity</small><b>{data.macro.activity_label||'—'}</b></div><div><small>Inflation impulse</small><b>{data.macro.inflation_impulse_label||'—'}</b></div><div><small>Financial impulse</small><b>{data.macro.financial_impulse_label||'—'}</b></div><span>MacroLens · {data.macro.as_of_date||'latest cached environment'}</span></div></section>}
 </>
}
