const origin = process.env.MACROLENS_V2_API_URL || 'http://127.0.0.1:8016';
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
