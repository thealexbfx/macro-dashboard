const origin = process.env.MACROLENS_V2_API_URL || 'http://127.0.0.1:8016';
export async function proxy(path: string, init?: RequestInit) {
    try {
        const response = await fetch(`${origin}/api/v2/${path}`, { ...init, cache: 'no-store', signal: AbortSignal.timeout(45000), headers: { 'Content-Type': 'application/json' } });
        return new Response(await response.text(), { status: response.status, headers: { 'Content-Type': 'application/json' } });
    }
    catch {
        return Response.json({ detail: 'Research backend unavailable. Start the V2 FastAPI service and retry.' }, { status: 503 });
    }
}
