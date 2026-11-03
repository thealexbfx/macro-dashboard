import { proxy } from '../../../../lib/server-api';
export async function GET() { return proxy('discovery'); }
