// Read-only candidate registry. Values are separate from code and must be checked
// against original-publisher metadata/observations before any operational pass.
import {readFileSync} from 'node:fs';
const loaded = JSON.parse(readFileSync(new URL('series-registry.json', import.meta.url), 'utf8'));
export const seriesRegistry = Object.freeze(loaded);
export function getSeriesSpec(mappingId) {
  const spec = Object.hasOwn(seriesRegistry, mappingId) ? seriesRegistry[mappingId] : null;
  if (!spec) return null;
  if (!/^G7-(US|GB|DE|FR|IT|CA|JP)-(0[1-9]|[12][0-9]|3[0-5])$/.test(mappingId)) {
    throw new Error('Invalid candidate mapping identifier');
  }
  if (['boc-valet', 'statcan-wds'].includes(spec.adapter) &&
      !/^[a-z0-9 .*-]{1,120}$/i.test(spec.expectedLabel)) {
    throw new Error('Invalid candidate publisher label');
  }
  if (spec.adapter === 'boc-valet') {
    if (!/^[A-Za-z0-9._-]{1,80}$/.test(spec.seriesId)) throw new Error('Invalid Bank of Canada series ID');
  } else if (spec.adapter === 'statcan-wds') {
    if (!Number.isSafeInteger(spec.vectorId) || spec.vectorId <= 0 ||
        !Number.isSafeInteger(spec.productId) || spec.productId <= 0 ||
        !['SA', 'NSA'].includes(spec.expectedAdjustment)) {
      throw new Error('Invalid Statistics Canada candidate metadata');
    }
  } else if (spec.adapter === 'bls-v1') {
    if (!/^[A-Z0-9]{10,24}$/.test(spec.seriesId) ||
        !['SA','NSA'].includes(spec.expectedAdjustment) ||
        !spec.expectedDefinition || !spec.expectedUnit) throw new Error('Invalid BLS mapping');
  } else if (spec.adapter === 'ecb-csv') {
    if (spec.seriesKey !== 'B.U2.EUR.4F.KR.DFR.LEV') throw new Error('Unsupported ECB rate key');
  } else if (spec.adapter === 'ons-timeseries') {
    if (!/^[A-Z0-9]{4}$/.test(spec.seriesId) ||
        !/^(economy|employmentandlabourmarket)$/.test(spec.path.split('/')[0]) ||
        spec.path.split('/').some(s => !/^[a-z0-9]+$/.test(s)) ||
        !spec.path.includes('/timeseries/'+spec.seriesId.toLowerCase()+'/') ||
        typeof spec.expectedLabel !== 'string' || spec.expectedLabel.length > 150 ||
        !['SA','NSA'].includes(spec.expectedAdjustment)) throw new Error('Invalid ONS series configuration');
  } else if (spec.adapter === 'us-treasury-xml') {
    if (spec.seriesId !== 'BC_10YEAR') throw new Error('Unsupported Treasury maturity field');
  } else if (spec.adapter === 'boe-iadb') {
    if (spec.seriesId !== 'IUDBEDR') throw new Error('Unsupported BoE series identifier');
  } else {
    throw new Error('Unsupported adapter: ' + String(spec.adapter));
  }
  return spec;
}
export function validateManifestRegistry(rows) {
  const ids = new Set(rows.map(row => row.mapping_id));
  if (ids.size !== rows.length) throw new Error('Duplicate manifest mapping identifiers');
  for (const id of Object.keys(seriesRegistry)) {
    if (!ids.has(id)) throw new Error('Configured mapping absent from manifest: ' + id);
    getSeriesSpec(id);
  }
  return {manifest_count: rows.length, configured_count: Object.keys(seriesRegistry).length,
    unconfigured_count: rows.length - Object.keys(seriesRegistry).length};
}
