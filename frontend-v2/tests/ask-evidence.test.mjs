import test from 'node:test';
import assert from 'node:assert/strict';
import {relativeChange, summarizeObservations} from '../lib/ask-evidence.ts';

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

test('relative change uses the earlier positive level as the denominator', () => {
    const rows = [{date:'2026-01-01', value:80}, {date:'2026-02-01', value:100}];
    assert.equal(relativeChange(summarizeObservations(rows)), 25);
    for (const value of [0, -80]) {
        assert.equal(relativeChange(summarizeObservations([{...rows[0], value}, rows[1]])), null);
        assert.equal(relativeChange(summarizeObservations([rows[0], {...rows[1], value}])), null);
    }
});

test('impossible calendar dates are excluded without excluding leap days', () => {
    const rows = [
        {date:'2024-02-28', value:2}, {date:'2024-02-29', value:3},
        {date:'2024-02-30', value:9}, {date:'2026-13-01', value:10},
    ];
    assert.equal(summarizeObservations(rows).latest.date, '2024-02-29');
});
