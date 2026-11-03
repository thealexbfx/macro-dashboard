import {proxy} from '../../../../../../lib/server-api';
export async function POST(request: Request){return proxy('discovery/admin/generate',{method:'POST',headers:{Authorization:request.headers.get('authorization')||''}});}
