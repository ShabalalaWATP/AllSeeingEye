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
    const message = { event, data: '{}', id: null };
    batch.receive(message);
    expect(sink.handleStreamMessage).toHaveBeenLastCalledWith(message);
  }
  vi.advanceTimersByTime(STREAM_BATCH_MS);
  expect(sink.applyUpsert).not.toHaveBeenCalled();
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
