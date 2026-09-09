import { beforeEach, expect, it, vi } from 'vitest';
import { liveEvent, storeStats } from '@/test/fixtures';
import * as api from '@/lib/api/events';
import { geographicOrder, insideCoverage } from './events.geography';
import { useEventsStore } from './events';
import type { LiveEvent } from '@/lib/api/eventSchemas';

beforeEach(() => {
  useEventsStore.getState().reset();
  vi.restoreAllMocks();
});

it('cancels stale viewport responses and reconciles a position leaving during its snapshot', async () => {
  const pending: ((events: LiveEvent[]) => void)[] = [];
  const fetch = vi
    .spyOn(api, 'fetchEvents')
    .mockImplementation(() => new Promise((resolve) => pending.push(resolve)));
  vi.spyOn(api, 'fetchStats').mockResolvedValue({ ...storeStats, total: 0, per_category: [] });
  const store = useEventsStore.getState();
  store.setCoverageBounds([-20, -50, 20, 50]);
  const first = store.load();
  store.setCoverageBounds([100, -50, 160, 50]);
  const second = store.load();
  expect(fetch.mock.calls[0]?.[1]?.aborted).toBe(true);
  const inside = liveEvent({ id: 'moving', point: { lon: 130, lat: 20 } });
  store.applyUpsert([{ ...inside, point: { lon: 0, lat: 20 } }]);
  pending[1]?.([inside]);
  await second;
  expect(useEventsStore.getState().list).toHaveLength(0);
  pending[0]?.([liveEvent({ id: 'stale', point: { lon: 0, lat: 20 } })]);
  await first;
  expect(useEventsStore.getState().list).toHaveLength(0);
  expect(useEventsStore.getState().coverageBounds).toEqual([100, -50, 160, 50]);
});

it('gives distant regions space before a dense recent region consumes the mirror', () => {
  const dense = Array.from({ length: 5000 }, (_, i) =>
    liveEvent({ id: `dense${i}`, point: { lon: 0, lat: 50 } }),
  );
  const distant = liveEvent({ id: 'distant', point: { lon: 130, lat: -30 } });
  expect(
    geographicOrder([...dense, distant])
      .slice(0, 2)
      .map((e) => e.id),
  ).toEqual(['dense0', 'distant']);
});

it('handles antimeridian bounds and excludes unlocated records only in scoped views', () => {
  const east = liveEvent({ point: { lon: 175, lat: 20 } });
  const west = liveEvent({ point: { lon: -175, lat: 20 } });
  const unknown = liveEvent({ point: null });
  expect(insideCoverage(east, [170, -30, -170, 30])).toBe(true);
  expect(insideCoverage(west, [170, -30, -170, 30])).toBe(true);
  expect(insideCoverage(east, [-20, -30, 20, 30])).toBe(false);
  expect(insideCoverage(unknown, null)).toBe(true);
  expect(insideCoverage(unknown, [170, -30, -170, 30])).toBe(false);
});

it('passes geographic viewport scope to main and supplemental queries and rejects remote updates', async () => {
  const fetch = vi.spyOn(api, 'fetchEvents').mockResolvedValue([]);
  vi.spyOn(api, 'fetchStats').mockResolvedValue({
    ...storeStats,
    per_category: [{ category: 'aviation', count: 6000, oldest: null, newest: null }],
  });
  const store = useEventsStore.getState();
  store.setCoverageBounds([100, -50, 160, 50]);
  await store.load();
  expect(fetch.mock.calls.length).toBeGreaterThan(1);
  for (const [query] of fetch.mock.calls)
    expect(query).toMatchObject({ bbox: [100, -50, 160, 50], sampling: 'geographic' });
  store.applyUpsert([
    liveEvent({ id: 'asia', point: { lon: 130, lat: 20 } }),
    liveEvent({ id: 'europe', point: { lon: 0, lat: 50 } }),
  ]);
  expect(useEventsStore.getState().list.map((e) => e.id)).toEqual(['asia']);
  store.select('asia');
  store.applyUpsert([liveEvent({ id: 'asia', point: { lon: 0, lat: 50 } })]);
  expect(useEventsStore.getState().selectedId).toBeNull();
  expect(useEventsStore.getState().list).toHaveLength(0);
});
