import test from 'node:test';
import assert from 'node:assert/strict';
import {request} from '../lib/contracts.ts';

for(const path of ['datasets','compare'])test(`busy ${path} retries a bounded rejected operation`,async()=>{
 const original=globalThis.fetch;let calls=0;
 try{globalThis.fetch=async()=>{calls++;return calls===1?Response.json({detail:'busy'},{status:503,headers:{'Retry-After':'0'}}):Response.json({ok:true});};
 assert.deepEqual(await request(path,path==='compare'?{datasets:['cpi']}:undefined),{ok:true});assert.equal(calls,2);
 }finally{globalThis.fetch=original;}
});
test('sustained overload stops after three attempts',async()=>{
 const original=globalThis.fetch;let calls=0;
 try{globalThis.fetch=async()=>{calls++;return Response.json({detail:'busy'},{status:429,headers:{'Retry-After':'0'}});};
 await assert.rejects(request('datasets'),/busy/);assert.equal(calls,3);
 }finally{globalThis.fetch=original;}
});
test('refresh and administrative actions are never retried',async()=>{
 const original=globalThis.fetch;let calls=0;
 try{globalThis.fetch=async()=>{calls++;return Response.json({detail:'busy'},{status:503,headers:{'Retry-After':'0'}});};
 for(const path of ['discovery/refresh','discovery/admin/usage'])await assert.rejects(request(path,path.endsWith('refresh')?{}:undefined),/busy/);
 assert.equal(calls,2);
 }finally{globalThis.fetch=original;}
});
test('abort during retry prevents another request',async()=>{
 const original=globalThis.fetch;const controller=new AbortController();let calls=0;
 try{globalThis.fetch=async()=>{calls++;queueMicrotask(()=>controller.abort());return Response.json({detail:'busy'},{status:503,headers:{'Retry-After':'2'}});};
 await assert.rejects(request('datasets',undefined,controller.signal),{name:'AbortError'});assert.equal(calls,1);
 }finally{globalThis.fetch=original;}
});
