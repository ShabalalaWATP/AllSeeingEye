import { describe, expect, it } from 'vitest';

import type { LiveEvent } from '@/lib/api/eventSchemas';
import { isSatellite, satellitePriority } from '@/lib/satellites';
import { isMilitaryAircraft, isMilitaryVessel } from '@/lib/traffic';
import { liveEvent } from '@/test/fixtures';

import { boundedEvents } from './events.coverage';
import { geographicOrder } from './events.geography';

const at = (sequence: number) => new Date(Date.UTC(2026, 8, 1) + sequence * 1000).toISOString();
const records = (events: readonly LiveEvent[]) =>
  Object.fromEntries(events.map((event) => [event.id, event]));

/** Uncached full-sort reference, retaining the pre-optimisation reservation pipeline. */
function reference(input: Record<string, LiveEvent>, limit: number, selected?: string) {
  const events = Object.values(input);
  if (events.length <= limit) return input;
  const sorted = [...events].sort(
    (a, b) =>
      Date.parse(b.observed_at) - Date.parse(a.observed_at) ||
      Date.parse(b.published_at ?? b.observed_at) - Date.parse(a.published_at ?? a.observed_at) ||
      a.id.localeCompare(b.id),
  );
  const fair = geographicOrder(sorted);
  const reserved = fair
    .filter((event) => event.category === 'maritime' && event.subtype === 'vessel_position')
    .sort((a, b) => Number(isMilitaryVessel(b)) - Number(isMilitaryVessel(a)))
    .slice(0, Math.min(1500, limit));
  reserved.push(
    ...fair
      .filter((event) => event.category === 'aviation')
      .sort((a, b) => Number(isMilitaryAircraft(b)) - Number(isMilitaryAircraft(a)))
      .slice(0, Math.min(1500, limit - reserved.length)),
  );
  reserved.push(
    ...fair
      .filter(isSatellite)
      .sort((a, b) => satellitePriority(b) - satellitePriority(a))
      .slice(0, Math.min(1000, limit - reserved.length)),
  );
  reserved.push(
    ...fair
      .filter(
        (event) =>
          event.category === 'disaster' &&
          event.subtype === 'thermal_detection' &&
          (event.source_id === 'firms' || event.source_id.startsWith('firms_')),
      )
      .slice(0, Math.min(500, limit - reserved.length)),
  );
  const ids = new Set(reserved.map((event) => event.id));
  const retained = [
    ...reserved,
    ...fair.filter((event) => !ids.has(event.id)).slice(0, limit - reserved.length),
  ];
  if (selected && input[selected] && retained.length && !retained.includes(input[selected]))
    retained[retained.length - 1] = input[selected];
  return records(retained);
}

function expectEquivalent(input: Record<string, LiveEvent>, limit: number, selected?: string) {
  const expected = reference(input, limit, selected);
  const actual = boundedEvents(input, limit, selected);
  expect(Object.keys(actual)).toEqual(Object.keys(expected));
  expect(Object.values(actual).every((event) => event === input[event.id])).toBe(true);
  return actual;
}

const kinds = [
  { count: 1700, category: 'maritime', subtype: 'vessel_position', source_id: 'aisstream' },
  { count: 1700, category: 'aviation', subtype: 'aircraft_position', source_id: 'opensky' },
  { count: 1200, category: 'space', subtype: 'satellite', source_id: 'celestrak_active' },
  { count: 700, category: 'disaster', subtype: 'thermal_detection', source_id: 'firms_noaa' },
  { count: 1000, category: 'news', subtype: 'article', source_id: 'rss' },
] as const;
const fixture = Object.freeze(
  records(
    kinds.flatMap(({ count, ...kind }, group) =>
      Array.from({ length: count }, (_, index) =>
        Object.freeze(
          liveEvent({
            ...kind,
            id: `g${group}-${index}`,
            observed_at: at(Math.floor(index / 3)),
            published_at: index % 7 ? at(Math.floor(index / 5)) : null,
            point: index % 11 ? { lon: (index % 12) * 30 - 179, lat: (index % 6) * 30 - 89 } : null,
            attributes: { military: index % 5 === 0 },
            source_id: group === 2 && index % 3 === 0 ? 'celestrak_skynet' : kind.source_id,
          }),
        ),
      ),
    ),
  ),
);

describe('retention equivalence', () => {
  it.each([0, 1, 499, 500, 999, 1000, 1499, 1500, 2999, 3000, 4499, 4500, 5000])(
    'preserves ordered source reservations and object identities at limit %s',
    (limit) => {
      const actual = expectEquivalent(fixture, limit);
      expect(Object.keys(actual)).toHaveLength(limit);
    },
  );

  it('retains the original input under the cap and after all records expire', () => {
    const input = records([liveEvent({ id: 'only' })]);
    expect(boundedEvents(input, 1)).toBe(input);
    expect(boundedEvents(input, 5000)).toBe(input);
    const empty = {};
    expect(boundedEvents(empty, 0)).toBe(empty);
  });

  it.each([NaN, -1, 2.5])('preserves prior numeric-limit behaviour for %s', (limit) => {
    expectEquivalent(fixture, limit);
  });

  it('keeps selected records as the same final-slot exception, including zero capacity', () => {
    expectEquivalent(fixture, 5000, 'g4-1');
    const actual = expectEquivalent(fixture, 1, 'g4-1');
    expect(Object.keys(actual)).toEqual(['g4-1']);
    expectEquivalent(fixture, 0, 'g4-1');
    expectEquivalent(fixture, 5000, 'not-retained');
  });

  it('preserves ordering after replacements, expiry and a new burst over a full mirror', () => {
    const mirror = boundedEvents(fixture, 5000);
    const next = { ...mirror };
    const ids = Object.keys(next);
    for (const id of ids.slice(-50)) Reflect.deleteProperty(next, id);
    for (const id of ids.slice(0, 50))
      next[id] = { ...next[id]!, observed_at: at(5000), published_at: at(4999) };
    for (let index = 0; index < 250; index++)
      next[`new-${index}`] = liveEvent({ id: `new-${index}`, observed_at: at(5000 + index) });
    expectEquivalent(next, 5000, ids[0]);
    expect(Object.keys(mirror)).toHaveLength(5000);
    expect(mirror[ids[0]!]!.observed_at).not.toBe(next[ids[0]!]!.observed_at);
  });

  it('retains the existing NaN fallback ordering for schema-admitted invalid timestamps', () => {
    const input = records([
      liveEvent({ id: 'a', observed_at: 'invalid', published_at: at(3) }),
      liveEvent({ id: 'b', observed_at: at(2), published_at: 'invalid' }),
      liveEvent({ id: 'c', observed_at: at(1), published_at: null }),
      liveEvent({ id: 'd', observed_at: 'invalid', published_at: 'invalid' }),
    ]);
    expectEquivalent(input, 2);
  });

  it('reorders an existing object after its observed timestamp is corrected', () => {
    const a = liveEvent({ id: 'a', observed_at: at(0), point: null });
    const b = liveEvent({ id: 'b', observed_at: at(1), point: null });
    const input = records([a, b]);
    expect(Object.keys(boundedEvents(input, 1))).toEqual(['b']);
    a.observed_at = at(2);
    expect(Object.keys(expectEquivalent(input, 1))).toEqual(['a']);
    a.observed_at = at(-1);
    expect(Object.keys(expectEquivalent(input, 1))).toEqual(['b']);
  });

  it('rechecks publication corrections and null fallback even at a tied observation time', () => {
    const a = liveEvent({ id: 'a', observed_at: at(1), published_at: null, point: null });
    const b = liveEvent({ id: 'b', observed_at: at(1), published_at: at(2), point: null });
    const input = records([a, b]);
    expect(Object.keys(boundedEvents(input, 1))).toEqual(['b']);
    a.published_at = at(3);
    expect(Object.keys(expectEquivalent(input, 1))).toEqual(['a']);
    a.published_at = null;
    expect(Object.keys(expectEquivalent(input, 1))).toEqual(['b']);
  });

  it('recomputes geography, category, military status and catalogue priority from current fields', () => {
    const a = liveEvent({ id: 'a', observed_at: at(0), point: { lon: 0, lat: 0 } });
    const b = liveEvent({ id: 'b', observed_at: at(1), point: { lon: 0, lat: 0 } });
    const c = liveEvent({ id: 'c', observed_at: at(2), point: { lon: 0, lat: 0 } });
    const input = records([a, b, c]);
    expect(Object.keys(boundedEvents(input, 2))).toEqual(['c', 'b']);
    a.point!.lon = 90;
    expect(Object.keys(expectEquivalent(input, 2))).toEqual(['c', 'a']);
    a.category = 'aviation';
    expect(Object.keys(expectEquivalent(input, 1))).toEqual(['a']);
    b.category = 'aviation';
    expect(Object.keys(expectEquivalent(input, 1))).toEqual(['b']);
    a.attributes.military = true;
    expect(Object.keys(expectEquivalent(input, 1))).toEqual(['a']);
    a.category = b.category = 'space';
    a.subtype = b.subtype = 'satellite';
    a.source_id = b.source_id = 'celestrak_active';
    expect(Object.keys(expectEquivalent(input, 1))).toEqual(['b']);
    a.source_id = 'celestrak_skynet';
    expect(Object.keys(expectEquivalent(input, 1))).toEqual(['a']);
  });
});
