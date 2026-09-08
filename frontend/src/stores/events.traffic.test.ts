import { beforeEach, expect, it, vi } from 'vitest';
import * as api from '@/lib/api/events';
import { liveEvent } from '@/test/fixtures';
import { useEventsStore, MAX_CLIENT_EVENTS } from './events';
import {
  boundedEvents,
  RESERVED_AIRCRAFT,
  RESERVED_FIRMS,
  RESERVED_SATELLITES,
  RESERVED_VESSELS,
} from './events.coverage';

beforeEach(() => useEventsStore.getState().reset());

it('keeps military traffic in cross-layer guarantees while preserving the selected record and5kbound', () => {
  const groups = [
    ...Array.from({ length: 2100 }, (_, i) => liveEvent({ id: `air-${i}`, category: 'aviation' })),
    ...Array.from({ length: 2100 }, (_, i) =>
      liveEvent({ id: `ship-${i}`, category: 'maritime', subtype: 'vessel_position' }),
    ),
    ...Array.from({ length: 1800 }, (_, i) =>
      liveEvent({ id: `sat-${i}`, category: 'space', subtype: 'satellite' }),
    ),
    ...Array.from({ length: 1500 }, (_, i) =>
      liveEvent({
        id: `fire-${i}`,
        category: 'disaster',
        subtype: 'thermal_detection',
        source_id: 'firms_viirs_noaa20',
      }),
    ),
    ...Array.from({ length: 1500 }, (_, i) => liveEvent({ id: `news-${i}`, category: 'news' })),
    liveEvent({
      id: 'mil-air',
      category: 'aviation',
      subtype: 'military_aircraft',
      observed_at: '2026-01-01T00:00:00Z',
    }),
    liveEvent({
      id: 'mil-ship',
      category: 'maritime',
      subtype: 'vessel_position',
      attributes: { military: true },
      observed_at: '2026-01-01T00:00:00Z',
    }),
    liveEvent({ id: 'selected', category: 'news', observed_at: '2025-01-01T00:00:00Z' }),
  ];
  const retained = boundedEvents(
    Object.fromEntries(groups.map((event) => [event.id, event])),
    MAX_CLIENT_EVENTS,
    'selected',
  );
  const items = Object.values(retained);
  expect(items).toHaveLength(MAX_CLIENT_EVENTS);
  expect(retained['mil-air']).toBeDefined();
  expect(retained['mil-ship']).toBeDefined();
  expect(retained.selected).toBeDefined();
  expect(items.filter((event) => event.category === 'aviation').length).toBeGreaterThanOrEqual(
    RESERVED_AIRCRAFT,
  );
  expect(items.filter((event) => event.category === 'maritime').length).toBeGreaterThanOrEqual(
    RESERVED_VESSELS,
  );
  expect(items.filter((event) => event.category === 'space').length).toBeGreaterThanOrEqual(
    RESERVED_SATELLITES,
  );
  expect(
    items.filter((event) => event.source_id === 'firms_viirs_noaa20').length,
  ).toBeGreaterThanOrEqual(RESERVED_FIRMS);
});

it('fetches military aircraft before API limiting so newer civilian rows cannot hide them', async () => {
  vi.spyOn(api, 'fetchStats').mockResolvedValue({
    total: 7000,
    estimated_bytes: 1,
    budget_bytes: 10,
    per_category: [{ category: 'aviation', count: 7000, oldest: null, newest: null }],
  });
  const military = liveEvent({
    id: 'military',
    category: 'aviation',
    subtype: 'military_aircraft',
  });
  const fetch = vi
    .spyOn(api, 'fetchEvents')
    .mockImplementation((query) =>
      Promise.resolve(
        query?.military ? [military] : [liveEvent({ id: 'civil', category: 'aviation' })],
      ),
    );
  await useEventsStore.getState().load();
  expect(fetch).toHaveBeenCalledWith(
    { categories: ['aviation'], military: true, limit: 1500 },
    expect.any(AbortSignal),
  );
  expect(useEventsStore.getState().byId.military).toBeDefined();
  expect(useEventsStore.getState().snapshotLimited).toBe(true);
});

it('keeps general coverage when the military supplement fails without claiming completeness', async () => {
  vi.spyOn(api, 'fetchStats').mockResolvedValue({
    total: 5000,
    estimated_bytes: 1,
    budget_bytes: 10,
    per_category: [{ category: 'aviation', count: 5000, oldest: null, newest: null }],
  });
  vi.spyOn(api, 'fetchEvents').mockImplementation((query) =>
    query?.military
      ? Promise.reject(new Error('Unavailable'))
      : Promise.resolve([liveEvent({ id: 'civil', category: 'aviation' })]),
  );
  await useEventsStore.getState().load();
  expect(useEventsStore.getState().byId.civil).toBeDefined();
  expect(useEventsStore.getState().error).toContain('military aircraft coverage unavailable');
  expect(useEventsStore.getState().snapshotLimited).toBe(true);
});

it('serialises military filters and offset without changing the request row limit', () => {
  expect(
    api.eventsQueryString({ categories: ['aviation'], military: true, offset: 2000, limit: 2000 }),
  ).toContain('military=true');
  expect(api.eventsQueryString({ military: false, offset: 2000 })).toContain('offset=2000');
});

it('aborts an in-flight military supplement when the mirror is reset', async () => {
  vi.spyOn(api, 'fetchStats').mockResolvedValue({
    total: 1,
    estimated_bytes: 1,
    budget_bytes: 10,
    per_category: [{ category: 'aviation', count: 1, oldest: null, newest: null }],
  });
  let signal: AbortSignal | undefined;
  let resolve: ((events: ReturnType<typeof liveEvent>[]) => void) | undefined;
  vi.spyOn(api, 'fetchEvents').mockImplementation((query, requestSignal) => {
    if (!query?.military) return Promise.resolve([liveEvent({ category: 'aviation' })]);
    signal = requestSignal;
    return new Promise((done) => {
      resolve = done;
    });
  });
  const loading = useEventsStore.getState().load();
  await vi.waitFor(() => expect(resolve).toBeDefined());
  useEventsStore.getState().reset();
  expect(signal?.aborted).toBe(true);
  resolve?.([liveEvent({ id: 'late-military', category: 'aviation', tags: ['military'] })]);
  await loading;
  expect(useEventsStore.getState().byId).toEqual({});
});
