import { describe, expect, it } from 'vitest';

import type { LiveEvent } from '@/lib/api/eventSchemas';
import { isSatellite, satellitePriority } from '@/lib/satellites';
import { isMilitaryAircraft, isMilitaryVessel } from '@/lib/traffic';
import { liveEvent } from '@/test/fixtures';

import { mergeMirrorBatch } from './events.batch';
import { boundedEvents, isFirms } from './events.coverage';
import { geographicOrder } from './events.geography';

const records = (events: readonly LiveEvent[]) =>
  Object.fromEntries(events.map((event) => [event.id, event]));

/** Preserve the original stable-sort reservation algorithm as an independent oracle. */
function reference(input: Record<string, LiveEvent>, limit: number, selectedId?: string) {
  const events = Object.values(input);
  if (events.length <= limit) return input;
  const fair = geographicOrder(
    events.sort(
      (a, b) =>
        Date.parse(b.observed_at) - Date.parse(a.observed_at) ||
        Date.parse(b.published_at ?? b.observed_at) - Date.parse(a.published_at ?? a.observed_at) ||
        a.id.localeCompare(b.id),
    ),
  );
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
  reserved.push(...fair.filter(isFirms).slice(0, Math.min(500, limit - reserved.length)));
  const ids = new Set(reserved.map((event) => event.id));
  const retained = [
    ...reserved,
    ...fair.filter((event) => !ids.has(event.id)).slice(0, limit - reserved.length),
  ];
  const selected = selectedId ? input[selectedId] : undefined;
  if (selected && retained.length && !retained.some((event) => event.id === selected.id))
    retained[retained.length - 1] = selected;
  return records(retained);
}

function equivalent(input: Record<string, LiveEvent>, limit: number, selectedId?: string) {
  const expected = reference(input, limit, selectedId);
  const actual = boundedEvents(input, limit, selectedId);
  expect(Object.keys(actual)).toEqual(Object.keys(expected));
  for (const id of Object.keys(expected)) expect(actual[id]).toBe(expected[id]);
  return actual;
}

const kinds = [
  { count: 1700, category: 'maritime', subtype: 'vessel_position', source_id: 'aisstream' },
  { count: 1700, category: 'aviation', subtype: 'aircraft_position', source_id: 'opensky' },
  { count: 1100, category: 'space', subtype: 'satellite', source_id: 'celestrak_skynet' },
  { count: 500, category: 'disaster', subtype: 'thermal_detection', source_id: 'firms_noaa' },
  { count: 250, category: 'news', subtype: 'article', source_id: 'rss' },
] as const;
const saturated = Object.freeze(
  records(
    kinds.flatMap(({ count, ...kind }, group) =>
      Array.from({ length: count }, (_, index) =>
        Object.freeze(
          liveEvent({
            ...kind,
            id: `${group}-${index}`,
            observed_at: new Date(
              Date.UTC(2026, 8, 1) + Math.floor(index / 3) * 1000,
            ).toISOString(),
            published_at: null,
            point: index % 9 ? { lon: (index % 12) * 30 - 179, lat: (index % 6) * 30 - 89 } : null,
            attributes: { military: index % 7 === 0, ship_type_code: index % 11 === 0 ? 35 : 70 },
            tags: index % 5 === 0 ? ['military'] : [],
          }),
        ),
      ),
    ),
  ),
);

describe('stable priority reservations', () => {
  it.each([
    -Infinity,
    -2.5,
    -2,
    -1,
    -0,
    0,
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
    2.5,
    Infinity,
  ])('retains original ordered references and slice semantics at budget %s', (limit) => {
    equivalent(saturated, limit, '4-0');
    equivalent(saturated, limit, 'missing');
  });

  it.each(['civilian', 'military', 'mixed'] as const)(
    'retains freshness/cell/insertion ties for %s traffic',
    (priority) => {
      const input = records(
        Array.from({ length: 30 }, (_, index) =>
          liveEvent({
            id: `${index % 2 ? 'e\u0301' : '\u00e9'}-${Math.floor(index / 2)}`,
            category: index % 3 ? 'aviation' : 'maritime',
            subtype: index % 3 ? 'aircraft_position' : 'vessel_position',
            point: index % 4 ? { lon: (index % 3) * 60, lat: 0 } : null,
            attributes: {
              military: priority === 'military' || (priority === 'mixed' && index % 2 === 0),
            },
          }),
        ),
      );
      equivalent(input, 20);
      equivalent(records(Object.values(input).reverse()), 20);
    },
  );

  it('reads current priority, category and position after same-object corrections', () => {
    const a = liveEvent({ id: 'a', category: 'aviation' });
    const b = liveEvent({ id: 'b', category: 'aviation' });
    const c = liveEvent({ id: 'c', category: 'maritime', subtype: 'vessel_position' });
    const input = records([a, b, c]);
    equivalent(input, 2);
    a.tags.push('military');
    c.attributes.ship_type_code = 35;
    equivalent(input, 2);
    a.tags.length = 0;
    b.attributes.military = true;
    c.attributes.ship_type_code = 70;
    c.attributes.military = true;
    equivalent(input, 2);
    c.attributes.military = false;
    b.attributes.military = false;
    a.subtype = 'military_aircraft';
    c.category = 'aviation';
    a.point = null;
    b.point = { lon: -179, lat: -89 };
    equivalent(input, 2);
    a.subtype = 'aircraft_position';
    equivalent(input, 2);
  });

  it('preserves expiry/re-add order and selection at a reservation boundary', () => {
    const initial = boundedEvents(saturated, 5000);
    const expired = Object.keys(initial).slice(0, 50);
    const original = initial[expired[0]!]!;
    const replacement = { ...original, attributes: { military: !original.attributes.military } };
    const added = Array.from({ length: 200 }, (_, index) =>
      liveEvent({ id: `new-${index}`, category: 'aviation', attributes: { military: true } }),
    );
    const merged = mergeMirrorBatch(
      initial,
      null,
      expired,
      [replacement, ...added],
      () => undefined,
    );
    expect(merged).not.toBeNull();
    const result = equivalent(merged!, 5000, '4-0');
    expect(result[replacement.id]).toBe(replacement);
    for (const id of expired.slice(1)) expect(result[id]).toBeUndefined();
  });

  it('reads each current traffic priority once while rebuilding a full mirror', () => {
    let reads = 0;
    const input = records(
      Array.from({ length: 5250 }, (_, index) =>
        liveEvent({
          id: `traffic-${index}`,
          category: index % 2 ? 'aviation' : 'maritime',
          subtype: index % 2 ? 'aircraft_position' : 'vessel_position',
          attributes: {
            // Constant output observes classifier work without changing the priority decision.
            get military() {
              reads++;
              return false;
            },
          },
        }),
      ),
    );
    const expected = reference(input, 5000);
    reads = 0;
    const actual = boundedEvents(input, 5000);
    expect(Object.keys(actual)).toEqual(Object.keys(expected));
    expect(reads).toBeLessThanOrEqual(Object.keys(input).length);
  });
});
