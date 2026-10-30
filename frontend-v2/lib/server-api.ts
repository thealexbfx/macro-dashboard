const origin = process.env.MACROLENS_V2_API_URL || 'http://127.0.0.1:8016';
// Bound the new catalog POST before buffering it in the 512 MiB frontend service.
export async function boundedCatalogBody(request:Request):Promise<string|null> {
    const maximum=65536;
    if(Number(request.headers.get('content-length'))>maximum){await request.body?.cancel();return null;}
    const reader=request.body?.getReader();if(!reader)return '';
    const decoder=new TextDecoder();let bytes=0,body='';
    try{for(;;){const {done,value}=await reader.read();if(done)break;bytes+=value.byteLength;if(bytes>maximum){await reader.cancel();return null;}body+=decoder.decode(value,{stream:true});}return body+decoder.decode();}
    finally{reader.releaseLock();}
}
// Request credentials go upstream only. Upstream/request headers are never copied wholesale.
export function safeResponseHeaders(upstream?: Headers): Headers {
    const result = new Headers({'Content-Type':'application/json','Cache-Control':'no-store','X-Content-Type-Options':'nosniff'});
    for (const name of ['content-type','retry-after']) {
        const value=upstream?.get(name);
        if(value)result.set(name,value);
    }
    return result;
}
export async function proxy(path: string, init?: RequestInit) {
    try {
        const headers=new Headers(init?.headers);headers.set('Content-Type','application/json');
        const response = await fetch(`${origin}/api/v2/${path}`, { ...init, cache:'no-store', signal:AbortSignal.timeout(45000), headers });
        return new Response(await response.text(), {status:response.status,headers:safeResponseHeaders(response.headers)});
    } catch {
        return Response.json({detail:'Research backend unavailable. Start the V2 FastAPI service and retry.'},{status:503,headers:safeResponseHeaders()});
    }
}
