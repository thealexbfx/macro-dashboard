import test from 'node:test';
import assert from 'node:assert/strict';
import { displayTime, healthLabel } from '../lib/data-health.ts';
test('Source lag and pipeline failure remain distinct', () => {
  assert.notEqual(healthLabel('source_failure'), healthLabel('source_lag_review'));
  assert.equal(healthLabel('never_verified'), 'Awaiting first successful check');
  assert.equal(healthLabel('unknown'), 'Needs review');
});
test('Absent or invalid timestamps never appear current', () => {
  assert.equal(displayTime(null), 'Not recorded');
  assert.equal(displayTime('invalid'), 'Unknown');
  assert.match(displayTime('2026-11-02T12:00:00+00:00'), /2026-11-02 12:00:00 UTC/);
});
