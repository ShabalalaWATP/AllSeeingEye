import { describe, expect, it } from 'vitest';
import type { LiveEvent } from '@/lib/api/eventSchemas';
import { streamEvent } from '@/test/streamFixture';
import { mergeFreshnessHint } from './events.freshness';
import { records } from '@/test/freshnessSortReference';

const base = Date.UTC(2026, 8, 1);
const event = (sequence: number) => streamEvent(sequence, base);
function timed(events: readonly LiveEvent[]) {
  return events.map((value) => ({
    event: value,
    times: [
      Date.parse(value.observed_at),
      Date.parse(value.published_at ?? value.observed_at),
    ] as const,
  }));
}

describe('current-record hint validation', () => {
  it('resolves current replacements, ignores normal removals and keeps its input pristine', () => {
    const old = event(1);
    const current = { ...old, title: 'Replacement' };
    const missing = event(3);
    const input = records([event(0), current, event(2)]);
    const keyed = Object.freeze(timed(Object.values(input)));
    const before = [...keyed];
    const result = mergeFreshnessHint(input, keyed, [missing, old]);
    expect(result?.map((item) => item.event.id)).toEqual(['s2', 's1', 's0']);
    expect(result?.[1]?.event).toBe(current);
    expect(keyed).toEqual(before);
  });

  it('declines empty or fully expired hints without changing keyed order', () => {
    const input = records([event(0), event(1)]);
    const keyed = Object.freeze(timed(Object.values(input)));
    expect(mergeFreshnessHint(input, keyed, [])).toBeNull();
    expect(mergeFreshnessHint(input, keyed, [event(9)])).toBeNull();
    expect(keyed.map((item) => item.event.id)).toEqual(['s0', 's1']);
  });

  it('rejects current-order mismatch, rather than trusting stale prior timestamp fields', () => {
    const previous = [event(2), event(1), event(0)];
    const promoted = { ...previous[2]!, observed_at: event(10).observed_at };
    const input = records([promoted, previous[1]!, previous[0]!]);
    const keyed = Object.freeze(timed(Object.values(input)));
    expect(mergeFreshnessHint(input, keyed, previous)).toBeNull();
    expect(keyed[0]?.event).toBe(promoted);
  });

  it('uses the current publication fallback and final ID tie-break after equal observations', () => {
    const a = { ...event(0), id: 'a', observed_at: event(4).observed_at };
    const b = { ...a, id: 'b' };
    const c = { ...a, id: 'c', published_at: event(2).published_at };
    const d = { ...a, id: 'd', published_at: null };
    const input = records([b, d, a, c]);
    const keyed = Object.freeze(timed(Object.values(input)));
    const result = mergeFreshnessHint(input, keyed, [c, b]);
    expect(result?.map((item) => item.event.id)).toEqual(['d', 'c', 'a', 'b']);
    expect(result?.[0]?.event).toBe(d);
  });

  it.each(['observed_at', 'published_at'] as const)('rejects nonfinite %s', (field) => {
    const item = { ...event(2), [field]: 'invalid-date' };
    const input = records([event(0), item]);
    expect(mergeFreshnessHint(input, timed(Object.values(input)), [event(0)])).toBeNull();
  });

  it('rejects duplicate or non-string prior identities', () => {
    const a = event(0);
    const input = records([a, event(1)]);
    const keyed = timed(Object.values(input));
    expect(mergeFreshnessHint(input, keyed, [a, a])).toBeNull();
    expect(mergeFreshnessHint(input, keyed, [{ ...a, id: 0 } as unknown as LiveEvent])).toBeNull();
  });

  it('requires own matching dictionary keys and distinct current identities', () => {
    const a = event(0);
    const b = event(1);
    const input = { alias: a, [b.id]: b };
    expect(mergeFreshnessHint(input, timed(Object.values(input)), [b])).toBeNull();
    Object.setPrototypeOf(input, { [a.id]: a });
    expect(mergeFreshnessHint(input, timed(Object.values(input)), [b])).toBeNull();
    const duplicates = { [a.id]: a, alias: a, [b.id]: b };
    expect(mergeFreshnessHint(duplicates, timed(Object.values(duplicates)), [b])).toBeNull();
    const malformed = { ...a, id: 42 } as unknown as LiveEvent;
    expect(mergeFreshnessHint({ '42': malformed }, timed([malformed]), [a])).toBeNull();
    const hiddenAlias = { alias: a, [b.id]: b };
    Object.defineProperty(hiddenAlias, a.id, { value: a, enumerable: false });
    expect(mergeFreshnessHint(hiddenAlias, timed(Object.values(hiddenAlias)), [b])).toBeNull();
    const valid = records([a, b]);
    expect(mergeFreshnessHint(valid, timed([a]), [a])).toBeNull();
  });

  it.each(['retained', 'added', 'cross'] as const)(
    'rejects %s equal collation before returning any reordered sequence',
    (location) => {
      const a = { ...event(0), id: '\u00e9' };
      const b = { ...a, id: 'e\u0301' };
      const c = event(1);
      expect(a.id.localeCompare(b.id)).toBe(0);
      const input = records([b, a, c]);
      const keyed = Object.freeze(timed(Object.values(input)));
      const previous = location === 'retained' ? [a, b] : location === 'added' ? [c] : [a];
      expect(mergeFreshnessHint(input, keyed, previous)).toBeNull();
      expect(keyed.map((item) => item.event.id)).toEqual([b.id, a.id, c.id]);
    },
  );
});
