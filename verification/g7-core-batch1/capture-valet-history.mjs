import {createHash} from 'node:crypto';
import {mkdir, readFile, writeFile} from 'node:fs/promises';
import {join} from 'node:path';
import {parseManifest, verify} from './verify.mjs';

const output = process.argv[2];
if (!output) throw new Error('Usage: node capture-valet-history.mjs <new-output-directory>');
const manifest = parseManifest(await readFile(new URL('./manifest.csv', import.meta.url), 'utf8'));
await mkdir(output);
const summaries = [];
for (const id of ['G7-CA-22', 'G7-CA-23']) {
  const result = await verify(manifest.find(row => row.mapping_id === id), undefined, undefined, {valetHistory: true});
  const payload = JSON.stringify(result, null, 2) + '\n';
  await writeFile(join(output, id + '.json'), payload, {flag: 'wx'});
  summaries.push({
    id, source_url: result.source_url, outcome: result.outcome,
    error_category: result.error_category, first: result.first_evidenced, last: result.last_evidenced,
    observations: result.observations.filter(point => point.value !== null).length,
    publisher_nulls: result.observations.filter(point => point.value === null).length,
    receipt_sha256: createHash('sha256').update(payload).digest('hex'),
    rights_status: result.rights_status, production_approval: result.production_approval,
  });
}
console.log(JSON.stringify(summaries, null, 2));
if (summaries.some(summary => summary.outcome !== 'VERIFIED')) process.exitCode = 1;
