export interface Dataset { id:string; name:string; category:string; source:string; region:string; value:string; change:string; }
export interface Investigation {id:string; title:string; datasets:string[]; note:string; collection:string;}
export const datasets:Dataset[]=[
{id:'cpi',name:'US Consumer Price Index',category:'Inflation',source:'FRED',region:'United States',value:'2.4%',change:'−0.1 pp'},
{id:'rate',name:'Federal Funds Rate',category:'Monetary policy',source:'Federal Reserve',region:'United States',value:'4.75%',change:'−25 bps'},
{id:'jobs',name:'Nonfarm Payrolls',category:'Labour',source:'BLS',region:'United States',value:'+182K',change:'+14K'},
{id:'gdp',name:'Real GDP Growth',category:'Growth',source:'BEA',region:'United States',value:'2.8%',change:'+0.3 pp'},
{id:'yield',name:'US 10-Year Treasury Yield',category:'Rates',source:'FRED',region:'United States',value:'4.24%',change:'+3 bps'},
{id:'uk',name:'UK Consumer Price Index',category:'Inflation',source:'ONS',region:'United Kingdom',value:'2.6%',change:'+0.2 pp'},
{id:'eu',name:'Euro Area Manufacturing PMI',category:'Growth',source:'Eurostat',region:'Euro Area',value:'46.2',change:'−0.4'}];
export const series=Array.from({length:60},(_,i)=>({date:`${2020+Math.floor(i/12)}-${String(i%12+1).padStart(2,'0')}`,cpi:100+i*.36+Math.sin(i*.32)*7,rate:100+i*.22+Math.cos(i*.24)*5,jobs:100+i*.5+Math.sin(i*.4)*3,gdp:100+i*.3+Math.cos(i*.3)*4,yield:100+i*.2+Math.sin(i*.27)*9,uk:100+i*.3+Math.cos(i*.3)*6,eu:100+i*.12+Math.sin(i*.4)*4}));
