import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { liveEvent } from '@/test/fixtures';
import { useEventsStore } from './events';
import { EventUpdateBatch, STREAM_BATCH_MS } from './events.stream';

const upsert = (id: string, title = id) => ({
  event: 'event.upsert',
  id: null,
  data: JSON.stringify({ events: [liveEvent({ id, title })] }),
});
const expire = (id: string) => ({
  event: 'event.expire',
  id: null,
  data: JSON.stringify({ ids: [id], count: 1 }),
});

beforeEach(() => {
  useEventsStore.getState().reset();
  vi.useFakeTimers();
});
afterEach(() => {
  vi.useRealTimers();
  useEventsStore.getState().reset();
});

it('publishes one bounded mirror for 5,000 updates and preserves the newest copy', () => {
  const batch = new EventUpdateBatch(useEventsStore.getState);
  const changed = vi.fn();
  const off = useEventsStore.subscribe(changed);
  for (let i = 0; i < 5_000; i++) batch.receive(upsert(String(i)));
  batch.receive(upsert('0', 'latest'));
  expect(changed).not.toHaveBeenCalled();
  vi.advanceTimersByTime(STREAM_BATCH_MS);
  expect(changed).toHaveBeenCalledOnce();
  expect(useEventsStore.getState().list).toHaveLength(5_000);
  expect(useEventsStore.getState().byId['0']?.title).toBe('latest');
  off();
});

it('preserves expiry/upsert ordering and does not rebuild for absent expiries', () => {
  useEventsStore.getState().applyUpsert([liveEvent({ id: 'gone' })]);
  const batch = new EventUpdateBatch(useEventsStore.getState);
  batch.receive(upsert('gone'));
  batch.receive(expire('gone'));
  batch.receive(expire('back'));
  batch.receive(upsert('back'));
  batch.flush();
  expect(useEventsStore.getState().list.map((event) => event.id)).toEqual(['back']);
  const list = useEventsStore.getState().list;
  useEventsStore.getState().applyExpire(['never-loaded']);
  expect(useEventsStore.getState().list).toBe(list);
});

it('bounds queued records during a larger feed burst and leaves no timer after clear', () => {
  const sink = { applyUpsert: vi.fn(), applyExpire: vi.fn(), handleStreamMessage: vi.fn() };
  const batch = new EventUpdateBatch(() => sink);
  for (let i = 0; i < 5_001; i++) batch.receive(upsert(String(i)));
  expect(sink.applyUpsert).toHaveBeenCalledOnce();
  expect(sink.applyUpsert.mock.calls[0]?.[0]).toHaveLength(5_000);
  batch.clear();
  vi.advanceTimersByTime(STREAM_BATCH_MS);
  expect(sink.applyUpsert).toHaveBeenCalledOnce();
});

it('handles authority and resync immediately, dropping queued sensor records', () => {
  const sink = { applyUpsert: vi.fn(), applyExpire: vi.fn(), handleStreamMessage: vi.fn() };
  const batch = new EventUpdateBatch(() => sink);
  for (const event of ['access.changed', 'event.resync']) {
    batch.receive(upsert('old'));
    const message = { event, data: '{"reason":"stream_gap"}', id: null };
    batch.receive(message);
    expect(sink.handleStreamMessage).toHaveBeenLastCalledWith(message);
  }
  vi.advanceTimersByTime(STREAM_BATCH_MS);
  expect(sink.applyUpsert).not.toHaveBeenCalled();
});

it('preserves queued updates when a resync signal is malformed', () => {
  const sink = { applyUpsert: vi.fn(), applyExpire: vi.fn(), handleStreamMessage: vi.fn() };
  const batch = new EventUpdateBatch(() => sink);
  batch.receive(upsert('valid'));
  for (const data of ['invalid JSON', '{}', '{"reason":"unrecognised"}'])
    batch.receive({ event: 'event.resync', data, id: null });
  vi.advanceTimersByTime(STREAM_BATCH_MS);
  expect(sink.applyUpsert).toHaveBeenCalledWith([expect.objectContaining({ id: 'valid' })]);
  expect(sink.handleStreamMessage).not.toHaveBeenCalled();
});

it('preserves queued tombstones and updates before requesting a bulk refresh', () => {
  const order: string[] = [];
  const sink = {
    applyUpsert: vi.fn(() => order.push('upsert')),
    applyExpire: vi.fn(() => order.push('expire')),
    handleStreamMessage: vi.fn(() => order.push('refresh')),
  };
  const batch = new EventUpdateBatch(() => sink);
  batch.receive(upsert('gone'));
  batch.receive(expire('gone'));
  batch.receive(upsert('latest'));
  batch.receive({ event: 'event.resync', data: '{"reason":"snapshot_required"}', id: null });
  expect(sink.applyExpire).toHaveBeenCalledWith(['gone']);
  expect(sink.applyUpsert).toHaveBeenCalledWith([expect.objectContaining({ id: 'latest' })]);
  expect(order).toEqual(['expire', 'upsert', 'refresh']);
  vi.advanceTimersByTime(STREAM_BATCH_MS);
  expect(sink.applyUpsert).toHaveBeenCalledOnce();
});

it('ignores out-of-view deltas without rebuilding the mirror, but removes records leaving it', () => {
  const store = useEventsStore.getState();
  store.setCoverageBounds([-10, 40, 10, 60]);
  const retained = liveEvent({ id: 'visible', point: { lon: 0, lat: 50 } });
  store.applyUpsert([retained]);
  store.select(retained.id);
  const previous = useEventsStore.getState().list;
  const changed = vi.fn();
  const off = useEventsStore.subscribe(changed);
  store.applyUpsert(
    Array.from({ length: 5_000 }, (_, i) =>
      liveEvent({ id: `outside-${i}`, point: { lon: 100, lat: 0 } }),
    ),
  );
  store.applyUpsert([retained]);
  expect(changed).not.toHaveBeenCalled();
  expect(useEventsStore.getState().list).toBe(previous);
  store.applyUpsert([{ ...retained, point: { lon: 100, lat: 0 } }]);
  expect(changed).toHaveBeenCalledOnce();
  expect(useEventsStore.getState().list).toEqual([]);
  expect(useEventsStore.getState().selectedId).toBeNull();
  off();
});

it('ignores malformed sensor frames and lets metadata bypass without flushing sensors', () => {
  const sink = { applyUpsert: vi.fn(), applyExpire: vi.fn(), handleStreamMessage: vi.fn() };
  const batch = new EventUpdateBatch(() => sink);
  for (const [event, data] of [
    ['event.upsert', 'bad'],
    ['event.upsert', '{}'],
    ['event.expire', '{}'],
  ])
    batch.receive({ event: event!, data: data!, id: null });
  batch.flush();
  expect(sink.applyUpsert).not.toHaveBeenCalled();
  batch.receive(upsert('valid'));
  batch.receive({ event: 'hello', data: '{}', id: null });
  expect(sink.applyUpsert).not.toHaveBeenCalled();
  expect(sink.handleStreamMessage).toHaveBeenCalledOnce();
  vi.advanceTimersByTime(STREAM_BATCH_MS);
  expect(sink.applyUpsert).toHaveBeenCalledOnce();
});
