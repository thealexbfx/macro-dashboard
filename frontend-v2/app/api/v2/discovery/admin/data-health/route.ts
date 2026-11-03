import { proxy } from '../../../../../../lib/server-api';

export async function GET(request: Request) {
  const input = new URL(request.url).searchParams;
  const query = new URLSearchParams();
  for (const key of ['offset', 'limit']) {
    const value = input.get(key);
    if (value !== null) query.set(key, value);
  }
  return proxy(`discovery/admin/data-health?${query}`, {
    headers: { Authorization: request.headers.get('authorization') || '' },
  });
}
