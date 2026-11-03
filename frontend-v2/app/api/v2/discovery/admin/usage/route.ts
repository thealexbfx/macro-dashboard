import {proxy} from '../../../../../../lib/server-api';
export async function GET(request: Request){return proxy('discovery/admin/usage',{method:'GET',headers:{Authorization:request.headers.get('authorization')||''}});}
