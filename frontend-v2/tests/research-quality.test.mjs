import test from 'node:test';
import assert from 'node:assert/strict';
import { researchUseNotes } from '../lib/research-quality.ts';

test('gold disclosure distinguishes futures, spot and announcement timing', () => {
    const text = researchUseNotes('gold').join(' ');
    assert.match(text, /not spot gold/);
    assert.match(text, /roll adjustment are unverified/);
    assert.match(text, /precede a typical 14:00 ET/);
});

test('monthly effective rate is not a policy-event calendar', () => {
    const text = researchUseNotes('fed_funds').join(' ');
    assert.match(text, /calendar month/);
    assert.match(text, /cannot identify the date/);
    assert.match(text, /mean to a median/);
});

test('notes neither disclose private datasets nor grant access by identifier', () => {
    for (const id of ['wb_brent_monthly', 'wb_copper_monthly', 'wb_iron_ore_monthly', '__proto__', 'unknown']) {
        assert.deepEqual(researchUseNotes(id), []);
    }
});
