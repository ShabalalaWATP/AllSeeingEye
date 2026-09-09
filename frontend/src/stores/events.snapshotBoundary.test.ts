import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import * as api from '@/lib/api/events';
import { liveEvent, storeStats } from '@/test/fixtures';
import { useEventsStore } from './events';
import { SNAPSHOT_REFRESH_MS } from './events.refresh';
import { EventUpdateBatch, STREAM_BATCH_MS } from './events.stream';

const dispose: (() => void)[] = [];
beforeEach(() => {
  vi.useFakeTimers();
  useEventsStore.getState().reset();
  vi.spyOn(api, 'fetchStats').mockResolvedValue({ ...storeStats, per_category: [] });
});
afterEach(() => {
  for (const off of dispose.splice(0)) off();
  useEventsStore.getState().reset();
  vi.useRealTimers();
});

it.each(['event.upsert', 'event.expire'])(
  'flushes a queued %s before a scheduled snapshot can publish newer data',
  async (event) => {
    const store = useEventsStore.getState();
    const batch = new EventUpdateBatch(useEventsStore.getState);
    dispose.push(
      store.onSnapshotStart(() => batch.flush()),
      () => batch.clear(),
    );
    const updated = liveEvent({ id: 'tracked', title: 'New snapshot' });
    const fetch = vi
      .spyOn(api, 'fetchEvents')
      .mockResolvedValueOnce([])
      .mockResolvedValue([updated]);
    await store.load();
    batch.receive({ event: 'event.resync', data: '{"reason":"snapshot_required"}', id: null });
    await vi.advanceTimersByTimeAsync(SNAPSHOT_REFRESH_MS - 100);
    batch.receive({
      event,
      data: JSON.stringify(
        event === 'event.upsert'
          ? { events: [liveEvent({ id: 'tracked', title: 'Old buffered update' })] }
          : { ids: ['tracked'], count: 1 },
      ),
      id: null,
    });
    await vi.advanceTimersByTimeAsync(100);
    expect(fetch).toHaveBeenCalledTimes(2);
    expect(useEventsStore.getState().byId.tracked?.title).toBe('New snapshot');
    await vi.advanceTimersByTimeAsync(STREAM_BATCH_MS);
    expect(useEventsStore.getState().byId.tracked?.title).toBe('New snapshot');
  },
);

it('also flushes before an explicit viewport reload and releases the boundary on unmount', async () => {
  const store = useEventsStore.getState();
  const batch = new EventUpdateBatch(useEventsStore.getState);
  const flush = vi.fn(() => batch.flush());
  const off = store.onSnapshotStart(flush);
  dispose.push(off, () => batch.clear());
  vi.spyOn(api, 'fetchEvents').mockResolvedValue([liveEvent({ id: 'tracked', title: 'Current' })]);
  batch.receive({ event: 'event.expire', data: '{"ids":["tracked"],"count":1}', id: null });
  await store.load();
  await vi.advanceTimersByTimeAsync(STREAM_BATCH_MS);
  expect(useEventsStore.getState().byId.tracked?.title).toBe('Current');
  expect(flush).toHaveBeenCalledOnce();
  off();
  await store.load();
  expect(flush).toHaveBeenCalledOnce();
});
