import { proxy } from '../../../../../lib/server-api';
export async function GET(request:Request){const params=new URL(request.url).searchParams;return proxy(`context/recessions?${params.toString()}`);}
