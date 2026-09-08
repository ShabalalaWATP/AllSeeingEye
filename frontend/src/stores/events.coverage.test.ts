import { beforeEach, expect, it, vi } from 'vitest';
import * as api from '@/lib/api/events';
import type { LiveEvent } from '@/lib/api/eventSchemas';
import { liveEvent, storeStats } from '@/test/fixtures';
import { MAX_CLIENT_EVENTS, useEventsStore } from './events';
import {
  boundedEvents,
  mergeSnapshots,
  RESERVED_VESSELS,
  RESERVED_SATELLITES,
  RESERVED_FIRMS,
} from './events.coverage';

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
  vi.mocked(api.fetchStats).mockResolvedValue({ ...storeStats, per_category: [] });
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

it('reserves satellites and ships while favouring a specific military catalogue', () => {
  const ships = Array.from({ length: 1500 }, (_, i) => vessel(`ship-${i}`));
  const satellites = Array.from({ length: 2000 }, (_, i) =>
    liveEvent({
      id: `sat-${i}`,
      category: 'space',
      subtype: 'satellite',
      source_id: 'celestrak_active',
    }),
  );
  const skynet = liveEvent({
    id: 'skynet',
    category: 'space',
    subtype: 'satellite',
    source_id: 'celestrak_skynet',
    observed_at: '2026-09-01T00:00:00Z',
  });
  const news = Array.from({ length: 5000 }, (_, i) =>
    liveEvent({ id: `news-${i}`, observed_at: '2026-09-08T00:00:00Z' }),
  );
  const bounded = boundedEvents(
    Object.fromEntries([...ships, ...satellites, skynet, ...news].map((e) => [e.id, e])),
    5000,
  );
  expect(Object.values(bounded).filter((event) => event.category === 'space')).toHaveLength(
    RESERVED_SATELLITES,
  );
  expect(Object.values(bounded).filter((event) => event.category === 'maritime')).toHaveLength(
    1500,
  );
  expect(bounded.skynet).toBeDefined();
  expect(Object.keys(bounded)).toHaveLength(5000);
});

it('requests public military and crewed catalogues separately from the busy active catalogue', async () => {
  vi.mocked(api.fetchStats).mockResolvedValue({
    ...storeStats,
    total: 17000,
    per_category: [{ category: 'space', count: 17000, oldest: null, newest: null }],
  });
  const satellite = liveEvent({ id: 'skynet', category: 'space', subtype: 'satellite' });
  const fetch = vi
    .spyOn(api, 'fetchEvents')
    .mockResolvedValueOnce([])
    .mockResolvedValueOnce([])
    .mockResolvedValueOnce([satellite]);
  await useEventsStore.getState().load();
  expect(fetch.mock.calls[1]?.[0]).toEqual({ categories: ['space'], limit: 1500 });
  expect(fetch.mock.calls[2]?.[0]).toEqual({
    sources: ['celestrak_skynet', 'celestrak_military', 'celestrak_stations'],
    limit: 1500,
  });
  expect(useEventsStore.getState().byId.skynet).toBeDefined();
});

it('reserves thermal detections alongside ships and satellites when feeds are crowded', () => {
  const ships = Array.from({ length: 1500 }, (_, i) => vessel(`ship-${i}`));
  const satellites = Array.from({ length: 1500 }, (_, i) =>
    liveEvent({ id: `sat-${i}`, category: 'space', subtype: 'satellite' }),
  );
  const fires = Array.from({ length: 1100 }, (_, i) =>
    liveEvent({
      id: `fire-${i}`,
      category: 'disaster',
      subtype: 'thermal_detection',
      source_id: 'firms_public_noaa20',
    }),
  );
  const news = Array.from({ length: 3000 }, (_, i) =>
    liveEvent({ id: `news-${i}`, observed_at: '2026-09-08T00:00:00Z' }),
  );
  const bounded = Object.values(
    boundedEvents(
      Object.fromEntries(
        [...ships, ...satellites, ...fires, ...news].map((event) => [event.id, event]),
      ),
      5000,
    ),
  );
  expect(bounded.filter((event) => event.subtype === 'thermal_detection')).toHaveLength(
    RESERVED_FIRMS,
  );
  expect(bounded.filter((event) => event.subtype === 'vessel_position')).toHaveLength(1500);
  expect(bounded.filter((event) => event.subtype === 'satellite')).toHaveLength(
    RESERVED_SATELLITES,
  );
  expect(bounded).toHaveLength(5000);
});

it('loads both keyed and public FIRMS sources when disaster records exist', async () => {
  vi.mocked(api.fetchStats).mockResolvedValue({
    ...storeStats,
    per_category: [{ category: 'disaster', count: 1000, oldest: null, newest: null }],
  });
  const fire = liveEvent({
    id: 'fire',
    category: 'disaster',
    subtype: 'thermal_detection',
    source_id: 'firms_public_noaa20',
  });
  const fetch = vi
    .spyOn(api, 'fetchEvents')
    .mockResolvedValueOnce([])
    .mockResolvedValueOnce([fire]);
  await useEventsStore.getState().load();
  expect(fetch.mock.calls[1]?.[0]).toEqual({
    sources: ['firms_viirs_noaa20', 'firms_public_noaa20'],
    limit: 1000,
  });
  expect(useEventsStore.getState().byId.fire).toBeDefined();
});
