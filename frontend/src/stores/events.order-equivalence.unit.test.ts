import { describe, expect, it, vi } from 'vitest';

import type { LiveEvent } from '@/lib/api/eventSchemas';
import { liveEvent } from '@/test/fixtures';
import { streamEvent } from '@/test/streamFixture';

import { mergeMirrorBatch, toList } from './events.batch';

const BASE = Date.UTC(2026, 8, 1);
const records = (events: readonly LiveEvent[]) =>
  Object.fromEntries(events.map((event) => [event.id, event]));
const reference = (input: Record<string, LiveEvent>) =>
  Object.values(input).sort(
    (a, b) =>
      (b.published_at ?? '').localeCompare(a.published_at ?? '') || a.id.localeCompare(b.id),
  );

function expectEquivalent(input: Record<string, LiveEvent>, previous: readonly LiveEvent[]) {
  const expected = reference(input);
  const actual = toList(input, previous);
  expect(actual.map((event) => event.id)).toEqual(expected.map((event) => event.id));
  expect(actual).toHaveLength(expected.length);
  actual.forEach((event, index) => expect(event).toBe(expected[index]));
  return actual;
}

describe('current event identities in the sorted mirror', () => {
  it('does not compare unchanged sort positions again when only record content changes', () => {
    const input = records(Array.from({ length: 5_000 }, (_, index) => streamEvent(index, BASE)));
    const previous = Object.freeze(reference(input).map((event) => Object.freeze(event)));
    const next = { ...input };
    for (let index = 0; index < 250; index++) {
      const old = previous[index]!;
      next[old.id] = Object.freeze({ ...old, title: 'Corrected title', severity: 4 });
    }
    Object.freeze(next);
    const compare = vi.spyOn(String.prototype, 'localeCompare');
    let actual: LiveEvent[];
    let comparisons: number;
    try {
      actual = toList(next, previous);
      comparisons = compare.mock.calls.length;
    } finally {
      compare.mockRestore();
    }
    const expected = reference(next);
    expect(actual).toHaveLength(expected.length);
    actual.forEach((event, index) => expect(event).toBe(expected[index]));
    expect(comparisons).toBeLessThanOrEqual(previous.length);
    expect(previous[0]!.title).not.toBe('Corrected title');
  });

  it('retains current replacements and exact order with equal dates and different IDs', () => {
    const input = records(['b', 'a', 'c'].map((id) => liveEvent({ id })));
    const previous = reference(input);
    const replacement = { ...input.b! };
    const actual = expectEquivalent({ ...input, b: replacement }, previous);
    expect(actual.find((event) => event.id === 'b')).toBe(replacement);
    expect(actual.find((event) => event.id === 'b')).not.toBe(input.b);
  });

  it.each([
    ['2026-09-01T00:00:00Z', '2026-10-01T00:00:00Z'],
    ['2026-09-01T00:00:00Z', null],
    [null, '2026-09-01T00:00:00Z'],
    ['invalid-a', 'invalid-z'],
    ['invalid-z', '2026-09-01T00:00:00Z'],
    ['2026-09-01T00:00:00Z', 'invalid-z'],
  ])('reorders a replacement after publication changes from %s to %s', (before, after) => {
    const input = records([
      liveEvent({ id: 'a', published_at: before }),
      liveEvent({ id: 'b', published_at: '2026-09-05T00:00:00Z' }),
      liveEvent({ id: 'c', published_at: null }),
    ]);
    const previous = reference(input);
    expectEquivalent({ ...input, a: { ...input.a!, published_at: after } }, previous);
  });

  it('validates actual order after a caller changes a retained object in place', () => {
    const input = records([streamEvent(0, BASE), streamEvent(1, BASE), streamEvent(2, BASE)]);
    const previous = reference(input);
    input.s0!.published_at = '2027-01-01T00:00:00Z';
    expect(expectEquivalent(input, previous)[0]).toBe(input.s0);
  });

  it('does not discard new IDs when old records keep their sort positions', () => {
    const input = records([streamEvent(0, BASE), streamEvent(2, BASE)]);
    const previous = Object.freeze(reference(input));
    const next = {
      ...input,
      s0: { ...input.s0!, title: 'Updated' },
      s1: streamEvent(1, BASE),
      s3: streamEvent(3, BASE),
    };
    expect(expectEquivalent(next, previous).map((event) => event.id)).toEqual([
      's3',
      's2',
      's1',
      's0',
    ]);
  });

  it('handles expiry-only and empty mirrors without retaining old objects', () => {
    const input = records([streamEvent(0, BASE), streamEvent(1, BASE), streamEvent(2, BASE)]);
    const previous = reference(input);
    expectEquivalent({ s2: input.s2!, s0: input.s0! }, previous);
    expect(expectEquivalent({}, previous)).toEqual([]);
    expectEquivalent(input, []);
  });

  it('falls back for reversed, duplicate and comparator-equivalent previous records', () => {
    const input = records([streamEvent(0, BASE), streamEvent(1, BASE), streamEvent(2, BASE)]);
    const previous = reference(input);
    expectEquivalent(input, [...previous].reverse());
    expectEquivalent(input, [previous[0]!, previous[0]!, ...previous.slice(1)]);
    // Canonically equivalent text can collate equally despite different dictionary keys.
    const tied = records([liveEvent({ id: '\u00e9' }), liveEvent({ id: 'e\u0301' })]);
    expectEquivalent(tied, Object.values(tied).reverse());
  });

  it.each([false, true])(
    'preserves dictionary order across an equal-collation replacement/new boundary (reversed: %s)',
    (reversed) => {
      const old = Object.freeze(liveEvent({ id: 'e\u0301' }));
      const replacement = Object.freeze({ ...old, title: 'Replacement' });
      const added = Object.freeze(liveEvent({ id: '\u00e9' }));
      expect(added.id.localeCompare(replacement.id)).toBe(0);
      const current = reversed ? [replacement, added] : [added, replacement];
      const actual = expectEquivalent(Object.freeze(records(current)), Object.freeze([old]));
      expect(actual.map((event) => event.id)).toEqual(current.map((event) => event.id));
    },
  );

  it.each([false, true])(
    'keeps multiple merge-boundary ties stable alongside earlier and later records (reversed: %s)',
    (reversed) => {
      const old = Object.freeze(liveEvent({ id: 'A\u030a' }));
      const before = Object.freeze(liveEvent({ id: 'before', published_at: '2027-01-01' }));
      const after = Object.freeze(liveEvent({ id: 'after', published_at: '2025-01-01' }));
      const replacement = Object.freeze({ ...old, title: 'Current identity' });
      const added = ['\u212b', '\u00c5'].map((id) => Object.freeze(liveEvent({ id })));
      added.forEach((event) => expect(event.id.localeCompare(old.id)).toBe(0));
      const ties = [...added, replacement];
      if (reversed) ties.reverse();
      const actual = expectEquivalent(
        Object.freeze(records([after, ...ties, before])),
        Object.freeze([before, old, after]),
      );
      [before, ...ties, after].forEach((event, index) => expect(actual[index]).toBe(event));
    },
  );

  it('does not trust a replacement dictionary key whose event has a different ID', () => {
    const input = records([streamEvent(0, BASE), streamEvent(1, BASE)]);
    const next = { ...input, s0: { ...input.s0!, id: 'different' } };
    expectEquivalent(next, reference(input));
  });

  it('uses the final re-added version and preserves the expiry/upsert change journal', () => {
    const input = records([streamEvent(0, BASE), streamEvent(1, BASE), streamEvent(2, BASE)]);
    const previous = reference(input);
    const intermediate = { ...input.s1!, title: 'Intermediate' };
    const final = { ...input.s1!, title: 'Final' };
    const journal = vi.fn();
    const merged = mergeMirrorBatch(input, null, ['s0', 's1'], [intermediate, final], journal)!;
    const actual = expectEquivalent(merged, previous);
    expect(actual.find((event) => event.id === 's1')).toBe(final);
    expect(actual.some((event) => event.id === 's0')).toBe(false);
    expect(journal.mock.calls).toEqual([
      ['s0', null],
      ['s1', null],
      ['s1', intermediate],
      ['s1', final],
    ]);
  });
});
