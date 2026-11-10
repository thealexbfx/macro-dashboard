// Read-only candidate configuration. Adding an entry does not approve a series.
// All values must be independently confirmed against publisher metadata at runtime.
export const seriesRegistry = Object.freeze({
  'G7-CA-07': {adapter: 'statcan-wds', vectorId: 41690973, productId: 18100004,
    expectedLabel: 'all.items', expectedAdjustment: 'NSA',
    discoveryUrl: 'https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=1810000401'},
  'G7-CA-11': {adapter: 'statcan-wds', vectorId: 2062815, productId: 14100287,
    expectedLabel: 'unemployment rate', expectedAdjustment: 'SA',
    discoveryUrl: 'https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=1410028701'},
  'G7-CA-22': {adapter: 'boc-valet', seriesId: 'V39079',
    expectedLabel: 'target for the overnight rate',
    discoveryUrl: 'https://www.bankofcanada.ca/valet/series/V39079/json'},
  'G7-CA-23': {adapter: 'boc-valet', seriesId: 'BD.CDN.10YR.DQ.YLD',
    expectedLabel: 'benchmark bond yield.*10.year',
    discoveryUrl: 'https://www.bankofcanada.ca/valet/series/BD.CDN.10YR.DQ.YLD/json'},
});

export function getSeriesSpec(mappingId) {
  const spec = Object.hasOwn(seriesRegistry, mappingId) ? seriesRegistry[mappingId] : null;
  if (!spec) return null;
  if (spec.adapter === 'boc-valet') {
    if (!/^[A-Za-z0-9._-]{1,80}$/.test(spec.seriesId)) throw new Error('Invalid Bank of Canada series ID');
  } else if (spec.adapter === 'statcan-wds') {
    if (!Number.isSafeInteger(spec.vectorId) || spec.vectorId <= 0 ||
        !Number.isSafeInteger(spec.productId) || spec.productId <= 0) {
      throw new Error('Invalid Statistics Canada vector or product ID');
    }
  } else {
    throw new Error('Unrecognized adapter: ' + spec.adapter);
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
