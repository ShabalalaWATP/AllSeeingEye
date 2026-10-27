import { beforeEach, expect, it, vi } from 'vitest';
import * as api from '@/lib/api/events';
import type { LiveEvent } from '@/lib/api/eventSchemas';
import { liveEvent, storeStats } from '@/test/fixtures';
import { useEventsStore } from './events';
import { SNAPSHOT_LIMIT } from './events.limits';

const vessel = (id: string, title?: string) =>
  liveEvent({ id, category: 'maritime', subtype: 'vessel_position', ...(title ? { title } : {}) });

beforeEach(() => {
  useEventsStore.getState().reset();
  vi.spyOn(api, 'fetchStats').mockResolvedValue({
    ...storeStats,
    total: 6000,
    per_category: [{ category: 'maritime', count: 1000, oldest: null, newest: null }],
  });
});

it('publishes the primary snapshot while a maritime supplement is pending', async () => {
  const primary = liveEvent({ id: 'main' });
  let resolve!: (events: LiveEvent[]) => void;
  const fetch = vi
    .spyOn(api, 'fetchEvents')
    .mockResolvedValueOnce([primary])
    .mockImplementationOnce(() => new Promise<LiveEvent[]>((done) => (resolve = done)));

  const loading = useEventsStore.getState().load();
  await vi.waitFor(() => expect(fetch).toHaveBeenCalledTimes(2));
  expect(useEventsStore.getState()).toMatchObject({
    loaded: true,
    loading: true,
    snapshotCount: 1,
  });
  expect(useEventsStore.getState().byId.main).toBe(primary);
  expect(useEventsStore.getState().byId.ship).toBeUndefined();

  resolve([vessel('ship')]);
  await loading;
  expect(useEventsStore.getState()).toMatchObject({
    loaded: true,
    loading: false,
    snapshotCount: 2,
  });
  expect(useEventsStore.getState().byId.ship).toBeDefined();
});

it('keeps post-primary stream updates and tombstones through a delayed supplement', async () => {
  let resolve!: (events: LiveEvent[]) => void;
  const fetch = vi
    .spyOn(api, 'fetchEvents')
    .mockResolvedValueOnce([vessel('gone'), vessel('ship', 'Primary position')])
    .mockImplementationOnce(() => new Promise<LiveEvent[]>((done) => (resolve = done)));
  const loading = useEventsStore.getState().load();
  await vi.waitFor(() => expect(fetch).toHaveBeenCalledTimes(2));
  expect(useEventsStore.getState().byId.gone).toBeDefined();

  useEventsStore.getState().applyExpire(['gone']);
  useEventsStore.getState().applyUpsert([vessel('ship', 'Live position')]);
  resolve([vessel('gone'), vessel('ship', 'Stale position'), vessel('extra')]);
  await loading;
  expect(useEventsStore.getState().byId.gone).toBeUndefined();
  expect(useEventsStore.getState().byId.ship?.title).toBe('Live position');
  expect(useEventsStore.getState().byId.extra).toBeDefined();
  expect(useEventsStore.getState().snapshotCount).toBe(3);
});

it('keeps a selected vessel pending until its supplement can restore the record', async () => {
  useEventsStore.getState().applyUpsert([vessel('selected', 'Earlier position')]);
  useEventsStore.getState().select('selected');
  let resolve!: (events: LiveEvent[]) => void;
  const fetch = vi
    .spyOn(api, 'fetchEvents')
    .mockResolvedValueOnce([liveEvent({ id: 'main' })])
    .mockImplementationOnce(() => new Promise<LiveEvent[]>((done) => (resolve = done)));
  const loading = useEventsStore.getState().load();
  await vi.waitFor(() => expect(fetch).toHaveBeenCalledTimes(2));
  expect(useEventsStore.getState().selectedId).toBe('selected');
  expect(useEventsStore.getState().byId.selected?.title).toBe('Earlier position');

  resolve([vessel('selected', 'Fresh position')]);
  await loading;
  expect(useEventsStore.getState().selectedId).toBe('selected');
  expect(useEventsStore.getState().byId.selected?.title).toBe('Fresh position');
});

it.each([0, 1])(
  'treats a %i-row bounded snapshot as complete despite crowded global statistics',
  async (count) => {
    const store = useEventsStore.getState();
    store.setCoverageBounds([-20, 40, 20, 60]);
    const fetch = vi
      .spyOn(api, 'fetchEvents')
      .mockResolvedValue(count === 0 ? [] : [liveEvent({ id: 'inside' })]);

    await store.load();
    expect(fetch).toHaveBeenCalledOnce();
    expect(fetch.mock.calls[0]?.[0]).toMatchObject({
      bbox: [-20, 40, 20, 60],
      sampling: 'geographic',
      limit: SNAPSHOT_LIMIT,
    });
    expect(useEventsStore.getState().snapshotCount).toBe(count);
    expect(useEventsStore.getState().snapshotLimited).toBe(false);
  },
);

it('continues scoped supplements and delta reconciliation for an exact-limit viewport page', async () => {
  useEventsStore.getState().setCoverageBounds([-20, 40, 20, 60]);
  const primary = Array.from({ length: SNAPSHOT_LIMIT }, (_, index) =>
    liveEvent({ id: `primary-${index}` }),
  );
  let resolve!: (events: LiveEvent[]) => void;
  const fetch = vi
    .spyOn(api, 'fetchEvents')
    .mockResolvedValueOnce(primary)
    .mockImplementationOnce(() => new Promise<LiveEvent[]>((done) => (resolve = done)));

  const loading = useEventsStore.getState().load();
  await vi.waitFor(() => expect(fetch).toHaveBeenCalledTimes(2));
  expect(useEventsStore.getState().snapshotCount).toBe(SNAPSHOT_LIMIT);
  expect(useEventsStore.getState().snapshotLimited).toBe(true);
  useEventsStore.getState().applyExpire(['primary-0']);
  resolve([vessel('ship')]);
  await loading;
  expect(useEventsStore.getState().byId['primary-0']).toBeUndefined();
  expect(useEventsStore.getState().byId.ship).toBeDefined();
  expect(useEventsStore.getState().snapshotCount).toBe(SNAPSHOT_LIMIT + 1);
  expect(fetch).toHaveBeenCalledTimes(2);
  for (const [query] of fetch.mock.calls)
    expect(query).toMatchObject({ bbox: [-20, 40, 20, 60], sampling: 'geographic' });
});
