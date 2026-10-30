import test from 'node:test';
import assert from 'node:assert/strict';
import {proxy,safeResponseHeaders} from '../lib/server-api.ts';
const fake='Bearer synthetic-hardening-test-not-a-real-secret';
for(const status of [200,403,503])test(`admin proxy never returns request or upstream credentials (${status})`,async t=>{
 let sent;
 t.mock.method(globalThis,'fetch',async(_url,init)=>{sent=new Headers(init.headers);return new Response('{"ok":true}',{status,headers:{Authorization:fake,'X-Admin-Token':fake,'Set-Cookie':'fixture=not-real','Content-Type':'application/json','Retry-After':'2','Cache-Control':'public,max-age=3600'}});});
 const r=await proxy('discovery/admin/usage',{headers:new Headers({Authorization:fake})});
 assert.equal(sent.get('authorization'),fake);assert.equal(r.status,status);assert.equal(r.headers.get('cache-control'),'no-store');assert.equal(r.headers.get('retry-after'),'2');
 for(const [k,v] of r.headers){assert(!v.includes(fake));assert(['cache-control','content-type','retry-after','x-content-type-options'].includes(k));}
 assert.equal(r.headers.get('authorization'),null);assert.equal(r.headers.get('set-cookie'),null);
});
test('proxy transport failures do not expose credentials and remain non-cacheable',async t=>{
 t.mock.method(globalThis,'fetch',async()=>{throw Error(fake);});const r=await proxy('discovery/admin/generate',{method:'POST',headers:{Authorization:fake}});assert.equal(r.status,503);assert.equal(r.headers.get('cache-control'),'no-store');assert(!(await r.text()).includes(fake));
});
test('safe header allowlist drops unrelated upstream values',()=>{
 const h=safeResponseHeaders(new Headers({'X-Token':fake,'Access-Control-Allow-Origin':'*','Content-Type':'application/json'}));assert.equal(h.get('x-token'),null);assert.equal(h.get('access-control-allow-origin'),null);assert.equal(h.get('x-content-type-options'),'nosniff');
});
