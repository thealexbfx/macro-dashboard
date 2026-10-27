import {proxy} from '../../../../../../lib/server-api';
export async function GET(_request:Request,context:{params:Promise<{id:string}>}){const {id}=await context.params;return proxy('discovery/stories/'+encodeURIComponent(id));}
