import { boundedCatalogBody, proxy, safeResponseHeaders } from '../../../../../lib/server-api';
export async function POST(request:Request){const body=await boundedCatalogBody(request);if(body===null)return Response.json({detail:'Catalog request exceeds 64 KiB'},{status:413,headers:safeResponseHeaders()});return proxy('catalog/search',{method:'POST',body});}
