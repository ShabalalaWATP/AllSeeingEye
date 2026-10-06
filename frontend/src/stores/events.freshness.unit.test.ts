import { describe, expect, it, vi } from 'vitest';

import type { LiveEvent } from '@/lib/api/eventSchemas';
import { liveEvent } from '@/test/fixtures';
import { streamEvent } from '@/test/streamFixture';
import { mergeMirrorBatch, toList } from './events.batch';
import { boundedEvents } from './events.coverage';
import { fullSortReference, records } from '@/test/freshnessSortReference';

function sameRecords(actual: Record<string, LiveEvent>, expected: Record<string, LiveEvent>) {
  expect(Object.keys(actual)).toEqual(Object.keys(expected));
  for (const id of Object.keys(expected)) expect(actual[id]).toBe(expected[id]);
}

function equivalent(
  input: Record<string, LiveEvent>,
  previous: readonly LiveEvent[],
  limit = 5000,
  selectedId?: string | null,
) {
  const expected = fullSortReference(input, limit, selectedId);
  const actual = boundedEvents(input, limit, selectedId, previous);
  sameRecords(actual, expected);
  return actual;
}

const base = Date.UTC(2026, 8, 1);
const seeded = (count: number, offset = 0) =>
  Array.from({ length: count }, (_, index) => streamEvent(offset + index, base));

describe('validated eviction freshness hint', () => {
  it.each(['new', 'mixed'] as const)(
    'sorts only additions for a 5000-record mirror and a canonical %s batch',
    (scenario) => {
      // Build the geographically reordered dictionary produced by a real prior eviction.
      const initial = fullSortReference(records(seeded(5250)), 5000);
      const previous = toList(initial);
      const expired = scenario === 'mixed' ? previous.slice(-50).map((event) => event.id) : [];
      const incoming = seeded(scenario === 'mixed' ? 200 : 250, 5250);
      const merged = mergeMirrorBatch(initial, null, expired, incoming, () => undefined)!;
      expect(Object.keys(merged)).toHaveLength(scenario === 'mixed' ? 5150 : 5250);
      const expected = fullSortReference(merged, 5000);
      // Transparent unit-only operation budget, never installed in the stream benchmark.
      const sort = vi.spyOn(Array.prototype, 'sort');
      let actual: Record<string, LiveEvent>;
      try {
        actual = boundedEvents(merged, 5000, null, previous);
        const sizes = sort.mock.contexts.map((value: unknown) =>
          Array.isArray(value) ? value.length : 0,
        );
        expect(Math.max(0, ...sizes)).toBeLessThanOrEqual(incoming.length);
      } finally {
        sort.mockRestore();
      }
      sameRecords(actual, expected);
    },
  );

  it('preserves the under-cap dictionary reference without examining the hint', () => {
    const input = records(seeded(3));
    const duplicate = [input.s0!, input.s0!];
    expect(boundedEvents(input, 3, 's0', duplicate)).toBe(input);
    expect(boundedEvents(input, Infinity, null, duplicate)).toBe(input);
  });

  it('resolves replacements and skips expiry while retaining a re-added selected record', () => {
    const initial = fullSortReference(records(seeded(5250)), 5000);
    const previous = toList(initial);
    const expired = previous.slice(-50).map((event) => event.id);
    const readded = { ...initial[expired[0]!]!, title: 'Current re-added record' };
    const replacement = { ...previous[20]!, summary: 'Corrected current content' };
    const merged = mergeMirrorBatch(
      initial,
      null,
      expired,
      [...seeded(200, 5250), readded, replacement],
      () => undefined,
    )!;
    const actual = equivalent(merged, previous, 5000, readded.id);
    expect(actual[readded.id]).toBe(readded);
    expect(actual[replacement.id]).toBe(replacement);
    for (const id of expired.slice(1)) expect(actual[id]).toBeUndefined();
  });

  it('uses full fallback for publication order that disagrees with observation order', () => {
    const events = seeded(30);
    events[0]!.observed_at = new Date(base + 100_000).toISOString();
    const input = records(events);
    equivalent(input, toList(input), 20, 's0');
    // No hint, as used by initial snapshot callers, retains the original full-sort result.
    sameRecords(boundedEvents(input, 20, 's0'), fullSortReference(input, 20, 's0'));
  });

  it('witnesses same-object raw-time corrections and never retains stale classifications', () => {
    const events = seeded(35);
    const input = records(events);
    const previous = toList(input);
    equivalent(input, previous, 20);
    const current = events[0]!;
    current.observed_at = new Date(base + 150_000).toISOString();
    current.published_at = null;
    equivalent(input, previous, 20, current.id);
    current.category = 'maritime';
    current.subtype = 'vessel_position';
    current.attributes.ship_type_code = 35;
    current.tags.push('military');
    current.point = { lon: -179, lat: -89 };
    equivalent(input, previous, 20, current.id);
    current.category = 'space';
    current.subtype = 'satellite';
    current.source_id = 'celestrak_skynet';
    current.point = null;
    equivalent(input, previous, 20, current.id);
    current.observed_at = events[34]!.observed_at;
    current.published_at = new Date(base - 100_000).toISOString();
    equivalent(input, previous, 20, current.id);
  });

  it.each(['observed_at', 'published_at'] as const)(
    'preserves the original result for schema-admitted invalid %s dates',
    (field) => {
      const events = seeded(20);
      const previous = toList(records(events));
      events[7]![field] = 'invalid-date';
      equivalent(records(events), previous, 12);
    },
  );

  it.each(['retained', 'added', 'cross'] as const)(
    'preserves dictionary precedence for %s collation ties',
    (location) => {
      const a = liveEvent({ id: '\u00e9', category: 'news', point: null });
      const b = liveEvent({ ...a, id: 'e\u0301' });
      const newest = liveEvent({ ...a, id: 'newest', observed_at: '2099-01-01T00:00:00Z' });
      expect(a.id.localeCompare(b.id)).toBe(0);
      const previous = location === 'retained' ? [a, b] : location === 'cross' ? [a] : [newest];
      for (const order of [
        [b, newest, a],
        [a, newest, b],
      ]) {
        equivalent(records(order), previous, 2);
      }
    },
  );

  it('preserves numeric and prototype-like own keys without reading inherited records', () => {
    const events = ['10', '2', '__proto__', 'constructor', 'toString'].map((id, index) =>
      liveEvent({ ...streamEvent(index, base), id }),
    );
    const input = records(events);
    Object.setPrototypeOf(input, { inherited: liveEvent({ id: 'inherited' }) });
    equivalent(input, toList(input), 3, '__proto__');
    expect(Object.hasOwn(input, '__proto__')).toBe(true);
  });

  it('falls back for key/id aliases, duplicate current identities and duplicate prior IDs', () => {
    const a = liveEvent({ id: 'a', category: 'news' });
    const b = liveEvent({ id: 'b', category: 'news' });
    equivalent({ wrongKey: a, b }, [a, b], 1);
    equivalent({ a, alias: a, b }, [a, b], 1);
    equivalent({ a, b }, [a, a, b], 1);
    // Distinct observation times let the original comparator order this malformed
    // identity without requiring a localeCompare method on a number.
    const malformed = {
      ...a,
      id: 42,
      observed_at: '2099-01-01T00:00:00Z',
    } as unknown as LiveEvent;
    equivalent({ '42': malformed, b }, [malformed, b], 1);
  });
});

describe('freshness hint keeps every reservation and limit boundary', () => {
  const kinds = [
    { count: 1700, category: 'maritime', subtype: 'vessel_position', source_id: 'aisstream' },
    { count: 1700, category: 'aviation', subtype: 'aircraft_position', source_id: 'opensky' },
    { count: 1100, category: 'space', subtype: 'satellite', source_id: 'celestrak_skynet' },
    { count: 600, category: 'disaster', subtype: 'thermal_detection', source_id: 'firms_noaa' },
    { count: 250, category: 'news', subtype: 'article', source_id: 'rss' },
  ] as const;
  const input = records(
    kinds.flatMap(({ count, ...kind }, group) =>
      Array.from({ length: count }, (_, index) =>
        liveEvent({
          ...streamEvent(group * 2000 + index, base),
          ...kind,
          attributes: { military: index % 7 === 0, ship_type_code: index % 11 === 0 ? 35 : 70 },
          tags: index % 5 ? [] : ['military'],
        }),
      ),
    ),
  );
  const previous = toList(input);
  it.each([
    -Infinity,
    -2.5,
    -1,
    -0,
    0.5,
    1,
    1499,
    1500,
    1501,
    2999,
    3000,
    4499,
    4500,
    5000,
    NaN,
    Infinity,
  ])('matches the original exact dictionary order at cap %s', (limit) => {
    equivalent(input, previous, limit, 's8000');
    equivalent(input, previous, limit, 'missing');
  });
});
