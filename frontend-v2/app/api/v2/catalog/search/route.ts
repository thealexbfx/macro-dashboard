import { proxy } from '../../../../../lib/server-api';
export async function POST(request:Request){return proxy('catalog/search',{method:'POST',body:await request.text()});}
