import { proxy } from '../../../../../lib/server-api';
export async function GET(request:Request,context:{params:Promise<{id:string}>}){const {id}=await context.params;return proxy(`observations/${encodeURIComponent(id)}${new URL(request.url).search}`);}
