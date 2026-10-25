import test from 'node:test';
import assert from 'node:assert/strict';
import {availableTypes,changeMode,defaultWorkspace,restoreWorkspace,unitKey,validateAxes,mergeObservations,hoverValues,seriesColor,commonFrequency,shiftUnit,shiftDescription,appendInvestigation} from '../lib/workspace.ts';

const series=(id,units,transformation='level',observations=[])=>({id,name:id,units,transformation,observations,native_frequency:'monthly'});
test('unrelated units and unrelated market index bases cannot share an overlay axis',()=>{
 const w={...defaultWorkspace(),mode:'overlay'};
 assert(validateAxes([series('gold','USD / troy oz'),series('dxy','index points')],w));
 assert(validateAxes([series('sp500','index points'),series('dxy','index points')],w));
 assert.equal(validateAxes([series('cpi','Index 1982–1984=100'),series('core_cpi','Index 1982–1984=100')],w),null);
});
test('only explicit compatible dual-axis groups pass validation',()=>{
 const s=[series('gold','USD / troy oz'),series('dxy','index points')];
 const w={...defaultWorkspace(),mode:'overlay',axes:'dual',axis_assignment:{gold:'left',dxy:'right'}};
 assert.equal(validateAxes(s,w),null);
 assert(validateAxes([...s,series('wti','USD / barrel')],w));
 assert(validateAxes(s,{...w,axis_assignment:{gold:'left',dxy:'left'}}));
});
test('indexed and standardized series have common comparable axes',()=>{
 for(const t of ['indexed','standardized'])assert.equal(validateAxes([series('gold','common',t),series('dxy','common',t)],{...defaultWorkspace(),mode:'overlay'}),null);
 assert.notEqual(unitKey(series('cpi','Percent per observation','percent')),unitKey({...series('gold','Percent per observation','percent'),native_frequency:'daily'}));
});
test('chart types follow visualization mode and switching restores a valid time-series type',()=>{
 assert.deepEqual(availableTypes('scatter'),['scatter']);
 assert.deepEqual(availableTypes('overlay'),['line','area','bar']);
 assert.equal(changeMode({...defaultWorkspace(),chart_type:'bar'},'overlay').chart_type,'bar');
 const scatter=changeMode(defaultWorkspace(),'scatter');assert.equal(scatter.chart_type,'scatter');
 assert.equal(changeMode(scatter,'separate').chart_type,'line');
});
test('merged tooltip grid retains dates, exact values, missing cells and source dates',()=>{
 const s=[{...series('cpi','Percent','yoy',[{date:'2020-01-01',value:1.234567890123},{date:'2020-02-01',value:null}]),source_dates:{'2020-01-01':'2019-07-01'}},series('unemployment','Percent','level',[{date:'2020-02-01',value:4}])];
 const grid=mergeObservations(s);assert.equal(grid.length,2);
 const hover=hoverValues(grid[0],s,[]);assert.equal(hover[0].value,1.234567890123);assert.equal(hover[0].source_date,'2019-07-01');assert.equal(hover[1].value,null);
 assert.equal(hoverValues(grid[1],s,['cpi']).length,1);
 assert.equal(grid[1].values.cpi,null);
});
test('stacked charts use one sorted union without fabricating intervening daily observations',()=>{
 const rows=mergeObservations([series('a','x','level',[{date:'2024-01-08',value:2}]),series('b','y','level',[{date:'2024-01-05',value:1}])]);
 assert.deepEqual(rows.map(r=>r.date),['2024-01-05','2024-01-08']);assert.equal(rows[0].values.a,null);assert.equal(rows[1].values.b,null);
});
test('series colours are distinct and independent of selection order',()=>{
 const ids=['gold','dxy','wti','sp500'];const a=ids.map(seriesColor);assert.equal(new Set(a).size,4);assert.deepEqual([...ids].reverse().map(seriesColor).reverse(),a);
});
test('version two saves reopen with conservative defaults without mutating the saved record',()=>{
 const old={id:'old',version:2,datasets:['cpi','unemployment'],transformations:{cpi:'yoy'},note:'keep me',start:'2020-01-01',end:'2024-12-31'};
 const before=JSON.stringify(old);assert.deepEqual(restoreWorkspace(old),defaultWorkspace());assert.equal(JSON.stringify(old),before);
});
test('version three investigation settings survive JSON storage and reopening',()=>{
 const w={mode:'overlay',chart_type:'area',layout:'grid',axes:'dual',axis_assignment:{cpi:'left',unemployment:'right'},recession:true,lead_lag:{dataset_id:'cpi',periods:6,unit:'months'},hidden:['unemployment']};
 const saved={id:'new',version:3,datasets:['cpi','unemployment'],workspace:w,timeframe:'YTD',start:'2026-01-01',end:'2026-10-23',note:'original note'};
 const read=JSON.parse(JSON.stringify(saved));assert.deepEqual(restoreWorkspace(read),w);assert.equal(read.timeframe,'YTD');assert.equal(read.note,'original note');
});
test('restoration rejects invalid shifts and recovers from all-hidden series',()=>{
 const settings=restoreWorkspace({datasets:['cpi'],workspace:{...defaultWorkspace(),chart_type:'scatter',hidden:['cpi'],lead_lag:{dataset_id:'absent',periods:20,unit:'months'}}});
 assert.equal(settings.chart_type,'line');assert.deepEqual(settings.hidden,[]);assert.equal(settings.lead_lag.periods,0);
});
test('frequency and lead-lag units are explicit and direction is stated',()=>{
 assert.equal(commonFrequency([{frequency:'daily'},{frequency:'monthly'}]),'monthly');assert.equal(shiftUnit('daily'),'calendar_days');assert.equal(shiftUnit('quarterly'),'quarters');
 assert.match(shiftDescription({dataset_id:'cpi',periods:6,unit:'months'},[]),/leads the other series by 6 months/);
 assert.match(shiftDescription({dataset_id:'cpi',periods:-6,unit:'months'},[]),/lags the other series by 6 months/);
});
test('saving appends to the latest storage contents and preserves older research exactly',()=>{
 const previous=[{id:'other-tab',version:3,note:'new from another tab',workspace:defaultWorkspace()},{id:'old',version:2,note:'keep this',transformations:{cpi:'yoy'},custom_legacy_field:'preserve me'}];
 let value=JSON.stringify(previous);const storage={getItem:()=>value,setItem:(_,v)=>{value=v;}};
 const next=appendInvestigation(storage,{id:'new',version:3,note:'new note',workspace:defaultWorkspace()});
 assert.equal(next[0].id,'new');assert.deepEqual(next.slice(1),previous);assert.deepEqual(JSON.parse(value),next);
});
test('unreadable research storage is never replaced by a new save',()=>{
 for(const value of ['{bad json','{"unexpected":"object"}']){
  let writes=0;assert.throws(()=>appendInvestigation({getItem:()=>value,setItem:()=>{writes++;}},{id:'new'}));assert.equal(writes,0);
 }
});
