import {proxy} from '../../../../../lib/server-api';
export async function POST(){return proxy('discovery/refresh',{method:'POST'});}
