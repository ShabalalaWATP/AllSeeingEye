import { act, renderHook } from '@testing-library/react';
import { expect, it, vi } from 'vitest';
import type { LiveEvent } from '@/lib/api/eventSchemas';
import { countSatelliteGroups, filterSatellites, isSatellite } from '@/lib/satellites';
import { liveEvent } from '@/test/fixtures';
import { useSatelliteFilters } from './useSatelliteFilters';

const now = '2026-10-05T12:00:00Z';
function satellite(id: string, overrides: Partial<LiveEvent> = {}): LiveEvent {
  return liveEvent({
    id,
    category: 'space',
    subtype: 'satellite',
    source_id: 'celestrak_active',
    published_at: now,
    attributes: { norad_id: id, position_at: now },
    ...overrides,
  });
}

function reference(events: LiveEvent[]) {
  return Object.fromEntries(
    (['all', 'crewed', 'military', 'skynet'] as const).map((group) => [
      group,
      filterSatellites(events, group).filter(isSatellite).length,
    ]),
  );
}

it('does not repeatedly classify unrelated rows to count satellite groups', () => {
  let categoryReads = 0;
  const events = Array.from({ length: 5000 }, (_, index) => {
    const event = liveEvent({ id: String(index), category: 'news' });
    Object.defineProperty(event, 'category', {
      get: () => {
        categoryReads += 1;
        return 'news';
      },
    });
    return event;
  });
  const { result, unmount } = renderHook(() => useSatelliteFilters(events));
  try {
    expect(result.current.counts).toEqual({ all: 0, crewed: 0, military: 0, skynet: 0 });
    // Membership, map output, result rows and counts may each inspect the population once.
    expect(categoryReads).toBeLessThanOrEqual(events.length * 4);
  } finally {
    unmount();
  }
});

it('classifies each row once in the counts-only pass without copying or modifying it', () => {
  let categoryReads = 0;
  const events = Array.from({ length: 5000 }, (_, index) => {
    const event = satellite(String(index));
    Object.defineProperty(event, 'category', {
      get: () => {
        categoryReads += 1;
        return 'space';
      },
    });
    Object.freeze(event.attributes);
    Object.freeze(event.tags);
    return Object.freeze(event);
  });
  expect(countSatelliteGroups(Object.freeze(events))).toEqual({
    all: 5000,
    crewed: 0,
    military: 0,
    skynet: 0,
  });
  expect(categoryReads).toBe(5000);
});

it.each([false, true])('deduplicates within each matching group, reversed=%s', (reversed) => {
  const events = [
    satellite('active', { attributes: { norad_id: 42 } }),
    satellite('station', { source_id: 'celestrak_stations', attributes: { norad_id: '42' } }),
    satellite('military', { attributes: { norad_id: 42, military_public_catalogue: true } }),
    satellite('skynet', {
      source_id: 'celestrak_skynet',
      tags: ['skynet'],
      attributes: { norad_id: 42 },
    }),
    satellite('all-groups', {
      source_id: 'celestrak_stations',
      tags: ['skynet'],
      attributes: { norad_id: '99', military_public_catalogue: true },
    }),
    satellite('newer', { observed_at: 'invalid', attributes: { norad_id: 99 } }),
    liveEvent({ id: 'plane', category: 'aviation' }),
    liveEvent({ id: 'launch', category: 'space', subtype: 'launch' }),
  ];
  if (reversed) events.reverse();
  expect(countSatelliteGroups(events)).toEqual(reference(events));
  expect(countSatelliteGroups(events)).toEqual({ all: 2, crewed: 2, military: 2, skynet: 2 });
});

it.each([undefined, null, true, {}, [], 0, -0, '', '__proto__', NaN, Infinity])(
  'preserves fallback and numeric/string key behaviour for %j',
  (norad) => {
    const attributes: LiveEvent['attributes'] = {};
    // Exercise malformed in-memory fields as well as the scalar API contract.
    if (norad !== undefined)
      Object.defineProperty(attributes, 'norad_id', { value: norad, enumerable: true });
    const stringKey =
      typeof norad === 'string' || typeof norad === 'number' ? String(norad) : 'other';
    const events = [
      satellite('fallback', { attributes }),
      satellite('fallback', { source_id: 'celestrak_stations', attributes }),
      satellite('other', { attributes: { norad_id: stringKey }, tags: ['skynet'] }),
      satellite('fallback-collision', { attributes: { norad_id: 'fallback' } }),
    ];
    expect(countSatelliteGroups(events)).toEqual(reference(events));
  },
);

it('reads corrected fields from the same objects on every call without a cache', () => {
  const event = satellite('changing');
  const events = [event, satellite('other')];
  const compare = () => expect(countSatelliteGroups(events)).toEqual(reference(events));
  compare();
  event.source_id = 'celestrak_stations';
  event.tags.push('skynet');
  event.attributes.military_public_catalogue = true;
  compare();
  expect(countSatelliteGroups(events)).toEqual({ all: 2, crewed: 1, military: 1, skynet: 1 });
  event.attributes.norad_id = 'other';
  compare();
  expect(countSatelliteGroups(events).all).toBe(1);
  event.category = 'aviation';
  compare();
  expect(countSatelliteGroups(events).crewed).toBe(0);
  event.category = 'space';
  event.subtype = 'launch';
  compare();
  event.subtype = 'satellite';
  event.source_id = 'celestrak_active';
  event.tags.length = 0;
  event.attributes.military_public_catalogue = false;
  compare();
  expect(countSatelliteGroups(events)).toEqual({ all: 1, crewed: 0, military: 0, skynet: 0 });
});

it('uses the hook current-position scope and follows expiry, corrections and removal', () => {
  vi.useFakeTimers();
  vi.setSystemTime(now);
  const current = satellite('edge', {
    point: null,
    attributes: { norad_id: 42, position_at: '2026-10-05T11:50:00Z' },
  });
  const rows = [
    current,
    satellite('missing', { published_at: null, attributes: {} }),
    satellite('invalid', { attributes: { position_at: 'invalid' } }),
    satellite('future', { attributes: { position_at: '2026-10-05T12:02:00Z' } }),
    liveEvent({ id: 'plane', category: 'aviation' }),
  ];
  const { result, rerender, unmount } = renderHook(({ events }) => useSatelliteFilters(events), {
    initialProps: { events: rows },
  });
  try {
    expect(result.current.counts).toEqual({ all: 1, crewed: 0, military: 0, skynet: 0 });
    expect(result.current.results[0]).toBe(current);
    act(() => result.current.setQuery('no-match'));
    expect(result.current.results).toEqual([]);
    expect(result.current.counts.all).toBe(1);
    act(() => {
      vi.advanceTimersByTime(30_000);
    });
    expect(result.current.counts.all).toBe(0);
    current.attributes.position_at = '2026-10-05T12:00:30Z';
    current.source_id = 'celestrak_stations';
    rerender({ events: [...rows] });
    expect(result.current.counts).toEqual({ all: 1, crewed: 1, military: 0, skynet: 0 });
    act(() => result.current.setQuery(''));
    expect(result.current.results[0]).toBe(current);
    rerender({ events: [] });
    expect(result.current.counts).toEqual({ all: 0, crewed: 0, military: 0, skynet: 0 });
  } finally {
    unmount();
    vi.useRealTimers();
  }
});
