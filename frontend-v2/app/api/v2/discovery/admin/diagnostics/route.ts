import {proxy} from '../../../../../../lib/server-api';
export async function GET(request:Request){return proxy('discovery/admin/diagnostics',{headers:{Authorization:request.headers.get('authorization')||''}});}
