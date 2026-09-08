import { beforeEach, expect, it, vi } from 'vitest';
import * as api from '@/lib/api/events';
import type { LiveEvent } from '@/lib/api/eventSchemas';
import { liveEvent, storeStats } from '@/test/fixtures';
import { MAX_CLIENT_EVENTS, useEventsStore } from './events';
import { boundedEvents, mergeSnapshots, RESERVED_VESSELS } from './events.coverage';

const vessel = (id: string) => liveEvent({ id, category: 'maritime', subtype: 'vessel_position' });
const crowded = {
  ...storeStats,
  total: 6000,
  per_category: [{ category: 'maritime' as const, count: 1000, oldest: null, newest: null }],
};

beforeEach(() => {
  useEventsStore.getState().reset();
  vi.spyOn(api, 'fetchStats').mockResolvedValue(crowded);
});

it('adds a category-specific maritime snapshot when general events crowd it out', async () => {
  const fetch = vi
    .spyOn(api, 'fetchEvents')
    .mockResolvedValueOnce([liveEvent({ id: 'news' })])
    .mockResolvedValueOnce([vessel('ship')]);
  await useEventsStore.getState().load();
  expect(fetch.mock.calls[1]?.[0]).toEqual({ categories: ['maritime'], limit: 1500 });
  expect(fetch.mock.calls[1]?.[1]).toBe(fetch.mock.calls[0]?.[1]);
  expect(useEventsStore.getState().byId.ship).toBeDefined();
  expect(useEventsStore.getState().snapshotCount).toBe(2);
  expect(useEventsStore.getState().snapshotLimited).toBe(true);
});

it('does not make a second request when maritime coverage is already complete', async () => {
  vi.mocked(api.fetchStats).mockResolvedValue({
    ...crowded,
    per_category: [{ ...crowded.per_category[0]!, count: 1 }],
  });
  const fetch = vi.spyOn(api, 'fetchEvents').mockResolvedValue([vessel('ship')]);
  await useEventsStore.getState().load();
  expect(fetch).toHaveBeenCalledTimes(1);
});

it('keeps newer duplicate positions and lets later responses resolve exact timestamp ties', () => {
  const old = vessel('ship');
  const newer = { ...old, observed_at: '2026-09-06T00:00:00Z', title: 'new' };
  expect(mergeSnapshots([newer], [old]).get('ship')?.title).toBe('new');
  expect(mergeSnapshots([old], [newer]).get('ship')?.title).toBe('new');
  expect(mergeSnapshots([old], [{ ...old, title: 'tie' }]).get('ship')?.title).toBe('tie');
});

it('retains ships when newer aircraft fill the mirror, without exceeding its cap', () => {
  const ships = Array.from({ length: RESERVED_VESSELS + 1 }, (_, i) => vessel(`ship-${i}`));
  const aircraft = Array.from({ length: MAX_CLIENT_EVENTS }, (_, i) =>
    liveEvent({ id: `plane-${i}`, category: 'aviation', observed_at: '2026-09-06T00:00:00Z' }),
  );
  const bounded = boundedEvents(
    Object.fromEntries([...ships, ...aircraft].map((event) => [event.id, event])),
    MAX_CLIENT_EVENTS,
  );
  expect(Object.keys(bounded)).toHaveLength(MAX_CLIENT_EVENTS);
  expect(
    Object.values(bounded).filter((event) => event.subtype === 'vessel_position'),
  ).toHaveLength(RESERVED_VESSELS);
  const allAircraft = boundedEvents(
    Object.fromEntries(aircraft.map((event) => [event.id, event])),
    MAX_CLIENT_EVENTS,
  );
  expect(Object.keys(allAircraft)).toHaveLength(MAX_CLIENT_EVENTS);
});

function pendingMaritime() {
  let resolve!: (events: LiveEvent[]) => void;
  const promise = new Promise<LiveEvent[]>((done) => {
    resolve = done;
  });
  const fetch = vi.spyOn(api, 'fetchEvents').mockResolvedValueOnce([]).mockReturnValueOnce(promise);
  return { resolve, fetch };
}

it('applies live updates and tombstones after a delayed maritime snapshot', async () => {
  const pending = pendingMaritime();
  const loading = useEventsStore.getState().load();
  await vi.waitFor(() => expect(pending.fetch).toHaveBeenCalledTimes(2));
  useEventsStore.getState().applyExpire(['gone']);
  useEventsStore.getState().applyUpsert([{ ...vessel('ship'), title: 'live' }]);
  pending.resolve([vessel('gone'), vessel('ship')]);
  await loading;
  expect(useEventsStore.getState().byId.gone).toBeUndefined();
  expect(useEventsStore.getState().byId.ship?.title).toBe('live');
});

it('cannot restore a logged-out session while the maritime request is pending', async () => {
  const pending = pendingMaritime();
  const loading = useEventsStore.getState().load();
  await vi.waitFor(() => expect(pending.fetch).toHaveBeenCalledTimes(2));
  useEventsStore.getState().reset();
  pending.resolve([vessel('ship')]);
  await loading;
  expect(useEventsStore.getState().list).toEqual([]);
  expect(useEventsStore.getState().loaded).toBe(false);
});

it('publishes the successful main snapshot and reports a failed maritime supplement', async () => {
  vi.spyOn(api, 'fetchEvents')
    .mockResolvedValueOnce([vessel('main')])
    .mockRejectedValueOnce(new Error('offline'));
  useEventsStore.getState().applyUpsert([vessel('live')]);
  await useEventsStore.getState().load();
  expect(useEventsStore.getState().byId.main).toBeDefined();
  expect(useEventsStore.getState().byId.live).toBeUndefined();
  expect(useEventsStore.getState().error).toBeTruthy();
});

it('keeps a replacement snapshot when the older maritime request finishes late', async () => {
  const pending = pendingMaritime();
  const old = useEventsStore.getState().load();
  await vi.waitFor(() => expect(pending.fetch).toHaveBeenCalledTimes(2));
  vi.mocked(api.fetchStats).mockResolvedValue(storeStats);
  pending.fetch.mockResolvedValueOnce([liveEvent({ id: 'replacement' })]);
  await useEventsStore.getState().load();
  pending.resolve([vessel('old')]);
  await old;
  expect(useEventsStore.getState().list.map((event) => event.id)).toEqual(['replacement']);
});

it('discards a maritime snapshot when its pending update journal overflowed', async () => {
  const pending = pendingMaritime();
  const loading = useEventsStore.getState().load();
  await vi.waitFor(() => expect(pending.fetch).toHaveBeenCalledTimes(2));
  useEventsStore
    .getState()
    .applyExpire(Array.from({ length: MAX_CLIENT_EVENTS + 1 }, (_, index) => `gone-${index}`));
  pending.resolve([vessel('gone-0')]);
  await loading;
  expect(useEventsStore.getState().list).toEqual([]);
  expect(useEventsStore.getState().error).toContain('reconciliation limit');
});
