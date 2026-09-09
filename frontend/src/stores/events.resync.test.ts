import { beforeEach, expect, it, vi } from 'vitest';
import * as api from '@/lib/api/events';
import type { LiveEvent } from '@/lib/api/eventSchemas';
import { liveEvent, storeStats } from '@/test/fixtures';
import { useEventsStore } from './events';

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((done) => {
    resolve = done;
  });
  return { promise, resolve };
}

function resync(reason = 'expiry_overflow') {
  useEventsStore.getState().handleStreamMessage({
    event: 'event.resync',
    data: JSON.stringify({ reason }),
    id: null,
  });
}

beforeEach(() => {
  useEventsStore.getState().reset();
  vi.spyOn(api, 'fetchStats').mockResolvedValue({ ...storeStats, per_category: [] });
});

it('clears stale records immediately, preserves filters and reconciles new deltas', async () => {
  useEventsStore.setState({ hidden: [] });
  const snapshot = deferred<LiveEvent[]>();
  vi.spyOn(api, 'fetchEvents').mockReturnValue(snapshot.promise);
  const store = useEventsStore.getState();
  store.applyUpsert([liveEvent({ id: 'stale' })]);
  store.select('stale');
  store.setCountry('FI');
  store.setWindow(2);
  store.toggleCategory('news');
  resync();
  expect(useEventsStore.getState()).toMatchObject({
    list: [],
    selectedId: null,
    stats: null,
    loading: true,
    snapshotCount: null,
    country: 'FI',
    windowHours: 2,
    hidden: ['news'],
  });
  store.applyUpsert([liveEvent({ id: 'fresh', title: 'Newest' })]);
  store.applyExpire(['gone']);
  snapshot.resolve([liveEvent({ id: 'fresh', title: 'Older' }), liveEvent({ id: 'gone' })]);
  await vi.waitFor(() => expect(useEventsStore.getState().loading).toBe(false));
  expect(useEventsStore.getState().list.map((event) => event.title)).toEqual(['Newest']);
});

it('a cancelled snapshot cannot restore removed markers or finish a replacement load', async () => {
  const old = deferred<LiveEvent[]>();
  const current = deferred<LiveEvent[]>();
  vi.spyOn(api, 'fetchEvents')
    .mockReturnValueOnce(old.promise)
    .mockReturnValueOnce(current.promise);
  const loading = useEventsStore.getState().load();
  resync('stream_gap');
  old.resolve([liveEvent({ id: 'stale' })]);
  await loading;
  expect(useEventsStore.getState().list).toEqual([]);
  expect(useEventsStore.getState().loading).toBe(true);
  current.resolve([liveEvent({ id: 'current' })]);
  await vi.waitFor(() => expect(useEventsStore.getState().loading).toBe(false));
  expect(useEventsStore.getState().list.map((event) => event.id)).toEqual(['current']);
});

it('keeps the stale mirror cleared when reload fails', async () => {
  vi.spyOn(api, 'fetchEvents').mockRejectedValue(new Error('offline'));
  useEventsStore.getState().applyUpsert([liveEvent({ id: 'stale' })]);
  resync();
  await vi.waitFor(() => expect(useEventsStore.getState().loading).toBe(false));
  expect(useEventsStore.getState().list).toEqual([]);
  expect(useEventsStore.getState().error).toBeTruthy();
});

it('ignores malformed signals and cannot restore a logged-out session', async () => {
  const snapshot = deferred<LiveEvent[]>();
  const fetch = vi.spyOn(api, 'fetchEvents').mockReturnValue(snapshot.promise);
  resync('unrecognised');
  expect(fetch).not.toHaveBeenCalled();
  resync();
  useEventsStore.getState().reset();
  snapshot.resolve([liveEvent({ id: 'previous-session' })]);
  await new Promise((resolve) => setTimeout(resolve, 0));
  expect(useEventsStore.getState().list).toEqual([]);
  expect(useEventsStore.getState().loaded).toBe(false);
});
