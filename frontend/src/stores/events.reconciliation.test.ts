import { beforeEach, describe, expect, it, vi } from 'vitest';
import * as api from '@/lib/api/events';
import type { LiveEvent } from '@/lib/api/eventSchemas';
import { liveEvent, storeStats } from '@/test/fixtures';
import { MAX_CLIENT_EVENTS, SNAPSHOT_LIMIT, useEventsStore } from './events';

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((done) => {
    resolve = done;
  });
  return { promise, resolve };
}

beforeEach(() => {
  useEventsStore.getState().reset();
  vi.spyOn(api, 'fetchStats').mockResolvedValue(storeStats);
});

describe('snapshot and stream reconciliation', () => {
  it('keeps stream updates and tombstones when an older snapshot arrives late', async () => {
    const snapshot = deferred<LiveEvent[]>();
    vi.spyOn(api, 'fetchEvents').mockReturnValue(snapshot.promise);
    const store = useEventsStore.getState();
    const loading = store.load();
    store.applyUpsert([
      liveEvent({ id: 'updated', title: 'Fresh stream title' }),
      liveEvent({ id: 'new' }),
    ]);
    store.applyExpire(['expired']);
    store.select('new');
    snapshot.resolve([
      liveEvent({ id: 'updated', title: 'Stale title' }),
      liveEvent({ id: 'expired' }),
      liveEvent({ id: 'snapshot-only' }),
    ]);
    await loading;
    const state = useEventsStore.getState();
    expect(state.byId.updated?.title).toBe('Fresh stream title');
    expect(state.byId.expired).toBeUndefined();
    expect(state.byId.new).toBeDefined();
    expect(state.byId['snapshot-only']).toBeDefined();
    expect(state.selectedId).toBe('new');
  });

  it('reconciles the final operation per id and idempotent replay', async () => {
    const snapshot = deferred<LiveEvent[]>();
    vi.spyOn(api, 'fetchEvents').mockReturnValue(snapshot.promise);
    const store = useEventsStore.getState();
    const loading = store.load();
    store.applyExpire(['returned']);
    store.applyUpsert([liveEvent({ id: 'returned' }), liveEvent({ id: 'gone' })]);
    store.applyUpsert([liveEvent({ id: 'returned' })]);
    store.applyExpire(['gone']);
    snapshot.resolve([liveEvent({ id: 'gone' })]);
    await loading;
    expect(useEventsStore.getState().list.map((event) => event.id)).toEqual(['returned']);
  });

  it('ignores superseded loads and reset results even when transport ignores cancellation', async () => {
    const first = deferred<LiveEvent[]>();
    const second = deferred<LiveEvent[]>();
    const fetch = vi
      .spyOn(api, 'fetchEvents')
      .mockReturnValueOnce(first.promise)
      .mockReturnValueOnce(second.promise);
    const one = useEventsStore.getState().load();
    const two = useEventsStore.getState().load();
    expect(fetch.mock.calls[0]?.[1]?.aborted).toBe(true);
    second.resolve([liveEvent({ id: 'latest' })]);
    await two;
    first.resolve([liveEvent({ id: 'stale' })]);
    await one;
    expect(useEventsStore.getState().list.map((event) => event.id)).toEqual(['latest']);
    const last = deferred<LiveEvent[]>();
    fetch.mockReturnValueOnce(last.promise);
    const loading = useEventsStore.getState().load();
    useEventsStore.getState().reset();
    last.resolve([liveEvent()]);
    await loading;
    expect(useEventsStore.getState().list).toEqual([]);
    expect(useEventsStore.getState().loaded).toBe(false);
  });

  it('discards unsafe snapshots after bounded journal overflow without resurrecting records', async () => {
    const snapshot = deferred<LiveEvent[]>();
    vi.spyOn(api, 'fetchEvents').mockReturnValue(snapshot.promise);
    const store = useEventsStore.getState();
    const loading = store.load();
    store.applyExpire(
      Array.from({ length: MAX_CLIENT_EVENTS + 1 }, (_, index) => `expired-${index}`),
    );
    store.applyUpsert([liveEvent({ id: 'fresh' })]);
    snapshot.resolve([liveEvent({ id: 'expired-0' })]);
    await loading;
    expect(useEventsStore.getState().list.map((event) => event.id)).toEqual(['fresh']);
    expect(useEventsStore.getState().error).toContain('reload to resynchronise');
    expect(useEventsStore.getState().loading).toBe(false);
  });

  it('caps reconciled state and discloses partial snapshot coverage', async () => {
    const snapshot = deferred<LiveEvent[]>();
    vi.spyOn(api, 'fetchEvents').mockReturnValue(snapshot.promise);
    vi.mocked(api.fetchStats).mockResolvedValue({ ...storeStats, total: 10_000 });
    const store = useEventsStore.getState();
    const loading = store.load();
    store.applyUpsert(
      Array.from({ length: MAX_CLIENT_EVENTS }, (_, index) =>
        liveEvent({ id: `stream-${index}`, observed_at: '2026-09-06T00:00:00Z' }),
      ),
    );
    snapshot.resolve(
      Array.from({ length: SNAPSHOT_LIMIT }, (_, index) => liveEvent({ id: `snapshot-${index}` })),
    );
    await loading;
    const state = useEventsStore.getState();
    expect(state.list).toHaveLength(MAX_CLIENT_EVENTS);
    expect(state.snapshotCount).toBe(SNAPSHOT_LIMIT);
    expect(state.snapshotLimited).toBe(true);
    expect(state.mirrorCapped).toBe(true);
    expect(state.byId['stream-0']).toBeDefined();
  });

  it('clears selections removed by a reconnect snapshot and retains stream data on failure', async () => {
    const store = useEventsStore.getState();
    store.applyUpsert([liveEvent({ id: 'old' })]);
    store.select('old');
    vi.spyOn(api, 'fetchEvents')
      .mockResolvedValueOnce([])
      .mockRejectedValueOnce(new Error('Offline'));
    await store.load();
    expect(useEventsStore.getState().selectedId).toBeNull();
    store.applyUpsert([liveEvent({ id: 'live' })]);
    await store.load();
    expect(useEventsStore.getState().byId.live).toBeDefined();
    expect(useEventsStore.getState().error).not.toBeNull();
  });
});
