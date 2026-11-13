import test from 'node:test';
import assert from 'node:assert/strict';
import {summarizeObservations} from '../lib/ask-evidence.ts';

test('grounded evidence uses distinct dated values, retaining zero and skipping nulls', () => {
    const result = summarizeObservations([
        {date:'2026-01-01', value:3}, {date:'2026-01-03', value:0},
        {date:'2026-01-04', value:null}, {date:'2026-01-03', value:0}
    ]);
    assert.equal(result.change, -3);
    assert.equal(result.latest.date, '2026-01-03');
    assert.equal(result.previous.date, '2026-01-01');
});

test('insufficient or conflicting evidence yields no calculation', () => {
    const row = {date:'2026-01-01', value:1};
    assert.equal(summarizeObservations([row]), null);
    assert.equal(summarizeObservations([row, {...row,value:2}]), null);
});
