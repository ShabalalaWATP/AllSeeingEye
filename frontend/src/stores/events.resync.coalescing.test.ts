import { afterEach, expect, it, vi } from 'vitest';
import { liveEvent } from '@/test/fixtures';
import * as api from '@/lib/api/events';
import { useEventsStore } from './events';

afterEach(() => useEventsStore.getState().reset());

it('preserves markers and selection during a normal bulk refresh', async () => {
  let release!: (events: ReturnType<typeof liveEvent>[]) => void;
  vi.spyOn(api, 'fetchEvents').mockImplementationOnce(
    () =>
      new Promise((resolve) => {
        release = resolve;
      }),
  );
  vi.spyOn(api, 'fetchStats').mockResolvedValue({
    total: 1,
    estimated_bytes: 1,
    budget_bytes: 10,
    per_category: [],
  });
  const store = useEventsStore.getState();
  store.applyUpsert([liveEvent({ id: 'selected' })]);
  store.select('selected');
  store.handleStreamMessage({
    event: 'event.resync',
    data: '{"reason":"snapshot_required"}',
    id: null,
  });
  expect(useEventsStore.getState().selectedId).toBe('selected');
  expect(useEventsStore.getState().list).toHaveLength(1);
  release([liveEvent({ id: 'selected', title: 'Refreshed' })]);
  await vi.waitFor(() => expect(useEventsStore.getState().loading).toBe(false));
  expect(useEventsStore.getState().selectedId).toBe('selected');
  expect(useEventsStore.getState().byId.selected?.title).toBe('Refreshed');
});

it('finishes an in-flight snapshot then reconciles one time for a burst of resync markers', async () => {
  let release!: (events: ReturnType<typeof liveEvent>[]) => void;
  const fetch = vi
    .spyOn(api, 'fetchEvents')
    .mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          release = resolve;
        }),
    )
    .mockResolvedValue([liveEvent({ id: 'new' })]);
  vi.spyOn(api, 'fetchStats').mockResolvedValue({
    total: 1,
    estimated_bytes: 1,
    budget_bytes: 10,
    per_category: [],
  });
  const loading = useEventsStore.getState().load();
  for (let i = 0; i < 50; i++)
    useEventsStore.getState().handleStreamMessage({
      event: 'event.resync',
      data: JSON.stringify({ reason: 'stream_gap' }),
      id: null,
    });
  expect(fetch).toHaveBeenCalledOnce();
  expect(fetch.mock.calls[0]?.[1]?.aborted).toBe(false);
  release([liveEvent({ id: 'old' })]);
  await loading;
  await vi.waitFor(() => expect(useEventsStore.getState().loading).toBe(false));
  expect(fetch).toHaveBeenCalledTimes(2);
  expect(useEventsStore.getState().list.map((event) => event.id)).toEqual(['new']);
});

it('cancels a queued resync when the operator leaves the map', async () => {
  let release!: (events: ReturnType<typeof liveEvent>[]) => void;
  const fetch = vi.spyOn(api, 'fetchEvents').mockImplementationOnce(
    () =>
      new Promise((resolve) => {
        release = resolve;
      }),
  );
  vi.spyOn(api, 'fetchStats').mockResolvedValue({
    total: 0,
    estimated_bytes: 0,
    budget_bytes: 10,
    per_category: [],
  });
  const loading = useEventsStore.getState().load();
  useEventsStore
    .getState()
    .handleStreamMessage({ event: 'event.resync', data: '{"reason":"stream_gap"}', id: null });
  useEventsStore.getState().cancelLoad();
  release([]);
  await loading;
  expect(fetch).toHaveBeenCalledOnce();
  expect(useEventsStore.getState().loading).toBe(false);
});
