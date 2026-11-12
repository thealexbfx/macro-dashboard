// Official Statistics Canada WDS verification, strictly recent-sample only.
// Documentation: https://www.statcan.gc.ca/en/developers/wds/user-guide
const ROOT = 'https://www150.statcan.gc.ca/t1/wds/rest/';
const specs = {
  'G7-CA-07': {vectorId: 41690973, productId: 18100004, label: /all.items/i, table: '18-10-0004-01', expectedAdjustment: 'Not seasonally adjusted'},
  'G7-CA-11': {vectorId: 2062815, productId: 14100287, label: /unemployment rate/i, table: '14-10-0287-01', expectedAdjustment: 'Seasonally adjusted'},
};
const safe = value => typeof value === 'string' ? value.replace(/[\x00-\x1f\x7f]/g, ' ').slice(0, 240) : null;

async function postWds(method, vectorId, transport, delay) {
  const url = ROOT + method;
  const options = {
    method: 'POST', redirect: 'error', signal: AbortSignal.timeout(8000),
    headers: {'content-type': 'application/json', accept: 'application/json'},
    body: JSON.stringify([method === 'getSeriesInfoFromVector' ? {vectorId} : {vectorId, latestN: 5}]),
  };
  for (let attempt = 1; attempt <= 3; attempt++) {
    await delay(attempt * 350);
    let response;
    try { response = await transport(url, options); }
    catch {
      if (attempt < 3) continue;
      return {url, http_status: null, error: 'network_or_timeout', attempt};
    }
    const receipt = {url, http_status: response.status, retrieved_utc: new Date().toISOString(), attempt};
    if (!response.ok) {
      await response.body?.cancel().catch(() => {});
      if (attempt < 3 && (response.status === 429 || response.status === 409 || response.status >= 500)) continue;
      return {...receipt, error: 'http_' + response.status};
    }
    try {
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let text = '', size = 0;
      try {
        while (true) {
          const {value, done} = await reader.read();
          if (done) break;
          size += value.byteLength;
          if (size > 65536) return {...receipt, error: 'response_too_large'};
          text += decoder.decode(value, {stream: true});
        }
        text += decoder.decode();
      } finally { await reader.cancel().catch(() => {}); }
      return {...receipt, payload: JSON.parse(text)};
    } catch { return {...receipt, error: 'invalid_json_or_body'}; }
  }
}

function successfulObject(payload, vectorId) {
  const entries = Array.isArray(payload) ? payload : [];
  const record = entries.find(v => Number(v?.object?.vectorId) === vectorId);
  if (!record || record.status !== 'SUCCESS' || Number(record.object?.responseStatusCode) !== 0) return null;
  return record.object;
}

export async function verifyStatcan(row, original, transport = fetch, delay = async () => {}) {
  const spec = specs[row.mapping_id];
  if (!spec) return original;
  const source_url = ROOT + 'getSeriesInfoFromVector';
  const result = {...original, publisher_series_id: 'v' + spec.vectorId,
    source_url, publisher_discovery_url: 'https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=' + spec.productId + '01',
    metadata_url: source_url, observations_url: ROOT + 'getDataFromVectorsAndLatestNPeriods',
    error_category: null, api_receipts: [],
    rights_note: 'Statistics Canada Open Licence applicability to exact series, commercial display, export and attribution requires review.'};
  const meta = await postWds('getSeriesInfoFromVector', spec.vectorId, transport, delay);
  result.api_receipts.push({url: meta.url, http_status: meta.http_status, retrieved_utc: meta.retrieved_utc ?? null, error: meta.error ?? null});
  result.http_status = meta.http_status;
  if (meta.error) {
    const transportFailure = meta.error === 'network_or_timeout' || /^http_/.test(meta.error);
    return {...result, outcome: transportFailure ? 'ACCESS_BLOCKED' : 'UNRESOLVED',
      access_status: transportFailure ? 'BLOCKED' : 'RETRIEVED', error_category: meta.error};
  }
  result.access_status = 'RETRIEVED';
  const item = successfulObject(meta.payload, spec.vectorId);
  if (!item || typeof item.SeriesTitleEn !== 'string') return {...result, error_category: 'unusable_series_metadata'};
  result.metadata = {title: safe(item.SeriesTitleEn), product_id: item.productId,
    frequency_code: item.frequencyCode, unit_code: item.memberUomCode,
    terminated: item.terminated};
  result.definition = result.metadata.title;
  // MISMATCH is reserved for clearly contradictory publisher metadata.
  if (Number(item.productId) !== spec.productId || !spec.label.test(item.SeriesTitleEn) ||
      (row.mapping_id === 'G7-CA-07' && /seasonally adjusted/i.test(item.SeriesTitleEn)) ||
      (row.mapping_id === 'G7-CA-11' && /not seasonally adjusted/i.test(item.SeriesTitleEn))) {
    return {...result, outcome: 'MISMATCH', identity_status: 'MISMATCH',
      error_category: 'publisher_metadata_conflict',
      mismatch_notes: 'Official vector metadata contradicts the specified table, item or seasonal adjustment.'};
  }
  result.identity_status = 'MATCHED';
  result.seasonal_adjustment = /not seasonally adjusted/i.test(item.SeriesTitleEn) ? 'Not seasonally adjusted' :
    /seasonally adjusted/i.test(item.SeriesTitleEn) ? 'Seasonally adjusted' : null;
  result.frequency = Number(item.frequencyCode) === 6 ? 'Monthly' : null;
  const obs = await postWds('getDataFromVectorsAndLatestNPeriods', spec.vectorId, transport, delay);
  result.api_receipts.push({url: obs.url, http_status: obs.http_status, retrieved_utc: obs.retrieved_utc ?? null, error: obs.error ?? null});
  result.http_status = obs.http_status;
  if (obs.error) {
    const transportFailure = obs.error === 'network_or_timeout' || /^http_/.test(obs.error);
    return {...result, outcome: transportFailure ? 'ACCESS_BLOCKED' : 'UNRESOLVED',
      error_category: obs.error, access_status: transportFailure ? 'BLOCKED' : 'RETRIEVED'};
  }
  const data = successfulObject(obs.payload, spec.vectorId);
  if (!data || !Array.isArray(data.vectorDataPoint)) return {...result, error_category: 'unusable_observation_response'};
  const points = data.vectorDataPoint.flatMap(p => {
    const value = p?.value;
    const date = p?.refPer;
    return typeof date === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(date) &&
      (typeof value === 'string' || typeof value === 'number') && /^-?\d+(\.\d+)?$/.test(String(value))
      ? [{period: date, value: String(value)}] : [];
  }).sort((a,b)=>a.period.localeCompare(b.period));
  if (!points.length) return {...result, error_category: 'no_usable_observations'};
  return {...result, outcome: 'VERIFIED', verification_scope: 'RECENT_SAMPLE_ONLY',
    observations: points.slice(-5), first_evidenced: points[0].period, last_evidenced: points.at(-1).period,
    frequency: result.frequency, history_status: 'SAMPLE_ONLY', error_category: null};
}
