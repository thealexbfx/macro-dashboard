'use client';
import {useEffect, useState} from 'react';
import Header from '@/components/Header';
import AnswerView from '@/components/AnswerView';
import {askMacroLens, getRelationship, getRelationshipSeries} from '@/lib/api';

export default function Relationships() {
  const [series,setSeries]=useState([]), [target,setTarget]=useState('gold'), [driver,setDriver]=useState('us10y_real');
  const [timeframe,setTimeframe]=useState('5_years'), [economy,setEconomy]=useState('usa');
  const [result,setResult]=useState(null), [error,setError]=useState(''), [busy,setBusy]=useState(false);
  function choose(setter,value){setter(value);setResult(null);setError('');}
  useEffect(()=>{
    const query=new URLSearchParams(window.location.search);
    if(query.get('target')) setTarget(query.get('target'));
    if(query.get('driver')) setDriver(query.get('driver'));
    getRelationshipSeries().then(setSeries).catch(e=>setError(e.message));
  },[]);
  async function run(event) {
    event.preventDefault(); setBusy(true); setError(''); setResult(null);
    try {setResult(await getRelationship(target,driver,timeframe,economy));}
    catch(e){setError(e.message);} finally {setBusy(false);}
  }
  return <><Header/><main className="subpage"><h1>Historical relationships</h1>
    <p>Compare changes, scan leads and lags, and inspect sample stability. Historical association is exploratory evidence.</p>
    <form onSubmit={run} className="section researchForm">
      <label>Left indicator <select disabled={busy} value={target} onChange={e=>choose(setTarget,e.target.value)}>{series.map(s=><option key={s.key} value={s.key}>{s.name}</option>)}</select></label>
      <label>Right indicator <select disabled={busy} value={driver} onChange={e=>choose(setDriver,e.target.value)}>{series.map(s=><option key={s.key} value={s.key}>{s.name}</option>)}</select></label>
      <label>History <select disabled={busy} value={timeframe} onChange={e=>choose(setTimeframe,e.target.value)}>{[['1_year','1 year'],['3_years','3 years'],['5_years','5 years'],['10_years','10 years']].map(([value,label])=><option key={value} value={value}>{label}</option>)}</select></label>
      <label>Regime economy <select disabled={busy} value={economy} onChange={e=>choose(setEconomy,e.target.value)}>{[['usa','United States'],['uk','United Kingdom'],['euro','Euro Area'],['japan','Japan']].map(([value,label])=><option key={value} value={value}>{label}</option>)}</select></label>
      <button disabled={busy||!series.length||target===driver}>{busy?'Calculating…':'Investigate'}</button>
    </form>
    {error&&<p role="alert">{error}</p>}
    {result&&<AnswerView result={result} onAsk={async q=>{setBusy(true);setError('');try{setResult(await askMacroLens(q));}catch(e){setError(e.message);}finally{setBusy(false);}}}/>}
  </main></>;
}
