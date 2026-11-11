// Bounded, read-only first-party publisher transport for disposable verification only.
import {setTimeout as sleep} from 'node:timers/promises';

export async function publisherRequest(url, {method = 'GET', body = undefined, accept = 'application/json',
  transport = fetch, delay = sleep, maxBytes = 131072} = {}) {
  if (!/^https:\/\/(api\.bls\.gov|data-api\.ecb\.europa\.eu|www\.ons\.gov\.uk|www\.bankofengland\.co\.uk|home\.treasury\.gov)\//.test(url)) throw new Error('Publisher URL not allowlisted');
  if (!['GET','POST'].includes(method)) throw new Error('Unsafe method');
  for (let attempt=1; attempt<=3; attempt++) {
    await delay(attempt * 350);
    let response;
    try {
      response = await transport(url, {method, redirect:'error', signal: AbortSignal.timeout(8000),
        headers:{accept, ...(body ? {'content-type':'application/json'} : {})}, body});
    } catch {
      if (attempt===3) return {http_status:null, retrieved_utc:new Date().toISOString(), error:'network_or_timeout', attempt};
      continue;
    }
    const receipt = {http_status:response.status, retrieved_utc:new Date().toISOString(), attempt};
    if (!response.ok) {
      await response.body?.cancel().catch(()=>{});
      if (attempt<3 && (response.status===429 || response.status>=500)) continue;
      return {...receipt,error:'http_'+response.status};
    }
    try {
      const reader = response.body?.getReader();
      if (!reader) return {...receipt,error:'empty_response'};
      const decoder=new TextDecoder();let data='',size=0;
      try {
        while(true) {
          const {value,done}=await reader.read();
          if(done) break;
          size+=value.byteLength;
          if(size>maxBytes) return {...receipt,error:'response_too_large'};
          data+=decoder.decode(value,{stream:true});
        }
        data+=decoder.decode();
      } finally {await reader.cancel().catch(()=>{});}
      return {...receipt,text:data};
    } catch {
      if(attempt===3) return {...receipt,error:'body_read_failed'};
    }
  }
}
export const safeText = input => typeof input==='string' ? input.replace(/[\x00-\x1f\x7f]/g,' ').slice(0,280) : null;
export const safeNumber = value => (typeof value==='string' || typeof value==='number') &&
  /^-?\d+(\.\d+)?$/.test(String(value)) && String(value).length<=32;
