import test from 'node:test';
import assert from 'node:assert/strict';
import {boundedCatalogBody} from '../lib/server-api.ts';

test('bounded catalog body preserves valid Unicode JSON at the exact byte limit',async()=>{
 const base=Buffer.byteLength(JSON.stringify({query:'é',padding:''}));const data=JSON.stringify({query:'é',padding:'x'.repeat(65536-base)});assert.equal(Buffer.byteLength(data),65536);const r=new Request('http://localhost/api/v2/catalog/search',{method:'POST',body:data});assert.equal(await boundedCatalogBody(r),data);
});
test('oversized declared catalog requests are rejected before buffering',async()=>{
 const r=new Request('http://localhost/api/v2/catalog/search',{method:'POST',body:'{}',headers:{'Content-Length':'1000000000'}});assert.equal(await boundedCatalogBody(r),null);
});
test('oversized chunked catalog requests cancel after the bounded byte budget',async()=>{
 let cancelled=false;const stream=new ReadableStream({start(c){c.enqueue(new Uint8Array(40000));c.enqueue(new Uint8Array(40000));},cancel(){cancelled=true;}});
 const r=new Request('http://localhost/api/v2/catalog/search',{method:'POST',body:stream,duplex:'half'});assert.equal(await boundedCatalogBody(r),null);assert(cancelled);
});
