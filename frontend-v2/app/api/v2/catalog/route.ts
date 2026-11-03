import { proxy } from '../../../../lib/server-api';
export async function GET(request:Request){return proxy(`catalog${new URL(request.url).search}`);}
