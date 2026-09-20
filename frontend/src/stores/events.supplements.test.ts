import { beforeEach, expect, it, vi } from 'vitest';
import * as api from '@/lib/api/events';
import { ApiError } from '@/lib/api/errors';
import type { LiveEvent, StoreStats } from '@/lib/api/eventSchemas';
import { filterSatellites } from '@/lib/satellites';
import { liveEvent, storeStats } from '@/test/fixtures';
import { useEventsStore } from './events';
import { loadCoverageSupplements } from './events.supplements';

const crowded: StoreStats = {
  ...storeStats,
  total: 24_000,
  per_category: (['maritime', 'aviation', 'space', 'disaster'] as const).map((category) => ({
    category,
    count: 6000,
    oldest: null,
    newest: null,
  })),
};
const satellites = ['military', 'skynet'].map((group) =>
  liveEvent({
    id: group,
    category: 'space',
    subtype: 'satellite',
    source_id: `celestrak_${group}`,
    tags: group === 'skynet' ? ['satellite', 'skynet'] : ['satellite'],
    attributes: { norad_id: group, military_public_catalogue: true },
  }),
);

beforeEach(() => useEventsStore.getState().reset());

it('loads military and Skynet catalogues within the two-read server allowance', async () => {
  vi.spyOn(api, 'fetchStats').mockResolvedValue(crowded);
  // One read belongs to another panel. Supplements must leave it headroom.
  let active = 1;
  let peak = active;
  const fetch = vi.spyOn(api, 'fetchEvents').mockImplementation(async (query) => {
    if (active >= 2) throw new ApiError(429, 'rate_limited', 'Too many reads.', {}, 1);
    active += 1;
    peak = Math.max(peak, active);
    try {
      await new Promise<void>((resolve) => queueMicrotask(resolve));
      return query?.sources?.includes('celestrak_skynet') ? satellites : [];
    } finally {
      active -= 1;
    }
  });

  await useEventsStore.getState().load();

  const state = useEventsStore.getState();
  expect(state.error).toBeNull();
  expect(filterSatellites(state.list, 'military')).toHaveLength(2);
  expect(filterSatellites(state.list, 'skynet')).toEqual([satellites[1]]);
  expect(fetch).toHaveBeenCalledTimes(8); // Main snapshot plus all seven supplements.
  expect(peak).toBe(2);
  expect(state.loading).toBe(false);
});

it('waits for each supplement, preserving scope, successes and per-request failures', async () => {
  let release!: (events: LiveEvent[]) => void;
  const first = new Promise<LiveEvent[]>((resolve) => {
    release = resolve;
  });
  const fetch = vi.spyOn(api, 'fetchEvents').mockImplementation(async (query) => {
    if (query?.categories?.includes('maritime') && !query.military) return first;
    if (query?.categories?.includes('aviation')) throw new Error('offline');
    return query?.sources?.includes('celestrak_skynet') ? satellites : [];
  });
  const controller = new AbortController();
  const scope = { bbox: [-10, -20, 30, 40] as const, sampling: 'geographic' as const };
  const loading = loadCoverageSupplements([], crowded, controller.signal, scope);
  expect(fetch).toHaveBeenCalledTimes(1);
  release([]);
  const result = await loading;
  expect(result.events).toEqual(satellites);
  expect(result.error).toContain('aviation coverage unavailable');
  expect(result.error).toContain('military aircraft coverage unavailable');
  expect(result.error).not.toContain('satellite coverage unavailable');
  expect(result.limited).toBe(false);
  for (const [query, signal] of fetch.mock.calls) {
    expect(query).toMatchObject(scope);
    expect(signal).toBe(controller.signal);
  }
});

it('does not start queued supplements or publish late results after logout', async () => {
  vi.spyOn(api, 'fetchStats').mockResolvedValue(crowded);
  let release!: (events: LiveEvent[]) => void;
  const delayed = new Promise<LiveEvent[]>((resolve) => {
    release = resolve;
  });
  const fetch = vi.spyOn(api, 'fetchEvents').mockResolvedValueOnce([]).mockReturnValue(delayed);
  const loading = useEventsStore.getState().load();
  await vi.waitFor(() => expect(fetch).toHaveBeenCalledTimes(2));
  useEventsStore.getState().reset();
  release(satellites);
  await loading;
  expect(fetch).toHaveBeenCalledTimes(2);
  expect(useEventsStore.getState().list).toEqual([]);
  expect(useEventsStore.getState().loaded).toBe(false);
});

it('does not start a coverage request with an already cancelled signal', async () => {
  const controller = new AbortController();
  controller.abort();
  const fetch = vi.spyOn(api, 'fetchEvents').mockResolvedValue([]);
  await expect(loadCoverageSupplements([], crowded, controller.signal)).rejects.toThrow();
  expect(fetch).not.toHaveBeenCalled();
});
