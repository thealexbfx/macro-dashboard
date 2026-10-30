import {proxy} from '../../../../../lib/server-api';
export async function GET(request:Request){const input=new URL(request.url).searchParams;const query=new URLSearchParams();for(const name of ['limit','offset'])if(input.has(name))query.set(name,input.get(name)!);return proxy('discovery/historical?'+query.toString());}
