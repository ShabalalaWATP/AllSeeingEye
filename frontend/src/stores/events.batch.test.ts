import { afterEach, beforeEach, expect, it, vi } from 'vitest';

import type { LiveEvent } from '@/lib/api/eventSchemas';
import { liveEvent } from '@/test/fixtures';
import { streamEvent } from '@/test/streamFixture';

import { MAX_CLIENT_EVENTS, useEventsStore } from './events';
import { newestFirst, toList } from './events.batch';
import { subscribeEventChanges, type EventChange } from './events.changes';
import { RESERVED_VESSELS } from './events.coverage';
import { EventUpdateBatch } from './events.stream';

const BASE = Date.UTC(2026, 8, 1);

beforeEach(() => {
  useEventsStore.getState().reset();
});
afterEach(() => {
  useEventsStore.getState().reset();
});

/** A full mirror with many vessels, so eviction exercises the source reservations. */
function fullMirror(): LiveEvent[] {
  return Array.from({ length: MAX_CLIENT_EVENTS }, (_, i) => streamEvent(i, BASE));
}

function sequential(mirror: LiveEvent[], expired: string[], events: LiveEvent[]) {
  const store = useEventsStore.getState();
  store.reset();
  store.applyUpsert(mirror);
  store.select('s1');
  store.applyExpire(expired);
  store.applyUpsert(events);
  const { byId, list, selectedId, selectionOwner, mirrorCapped } = useEventsStore.getState();
  return { byId, list, selectedId, selectionOwner, mirrorCapped };
}

it('applies a mixed batch as one store update with the same result as separate steps', () => {
  const mirror = fullMirror();
  const expired = ['s1', 's2', 's3', 'never-loaded'];
  const events = [
    ...Array.from({ length: 300 }, (_, i) => streamEvent(MAX_CLIENT_EVENTS + i, BASE)),
    streamEvent(7, BASE, { title: 'Updated in place' }),
  ];
  const expected = sequential(mirror, expired, events);

  const store = useEventsStore.getState();
  store.reset();
  store.applyUpsert(mirror);
  store.select('s1');
  const changes: EventChange[] = [];
  const offChanges = subscribeEventChanges((change) => changes.push(change));
  const notified = vi.fn();
  const off = useEventsStore.subscribe(notified);
  store.applyBatch(expired, events);
  off();
  offChanges();

  expect(notified).toHaveBeenCalledOnce();
  const { byId, list, selectedId, selectionOwner, mirrorCapped } = useEventsStore.getState();
  expect({ byId, list, selectedId, selectionOwner, mirrorCapped }).toEqual(expected);
  expect(list).toHaveLength(MAX_CLIENT_EVENTS);
  expect(byId.s7?.title).toBe('Updated in place');
  expect(selectedId).toBeNull();
  // Expiry is announced before the upserts, as two separate stream deliveries were.
  expect(changes.map((change) => change.kind)).toEqual(['expire', 'upsert']);
  // Eviction ran once over the merged result, keeping every reserved vessel.
  const vessels = (records: readonly LiveEvent[]) =>
    records.filter((event) => event.subtype === 'vessel_position').length;
  // 1,000 mirror vessels and 60 new ones, less the expired s2.
  expect(vessels(list)).toBe(1_059);
  expect(vessels(list)).toBeLessThanOrEqual(RESERVED_VESSELS);
});

it('clears a view-owned selection when its record expires, even outside the mirror', () => {
  const store = useEventsStore.getState();
  store.applyUpsert([liveEvent({ id: 'kept' })]);
  store.select('news-only', 'view');
  const notified = vi.fn();
  const off = useEventsStore.subscribe(notified);
  store.applyBatch(['news-only'], []);
  off();
  expect(useEventsStore.getState().selectedId).toBeNull();
  expect(useEventsStore.getState().selectionOwner).toBe('mirror');
  expect(notified).toHaveBeenCalledOnce();
});

it('leaves the mirror untouched for an empty or irrelevant batch', () => {
  const store = useEventsStore.getState();
  store.applyUpsert([liveEvent({ id: 'kept' })]);
  const list = useEventsStore.getState().list;
  const notified = vi.fn();
  const off = useEventsStore.subscribe(notified);
  store.applyBatch([], []);
  store.applyBatch(['never-loaded'], [useEventsStore.getState().byId.kept!]);
  off();
  expect(notified).not.toHaveBeenCalled();
  expect(useEventsStore.getState().list).toBe(list);
});

it('flushes a mixed stream batch through one coherent update, upsert winning a re-add', () => {
  vi.useFakeTimers();
  try {
    const store = useEventsStore.getState();
    store.applyUpsert([liveEvent({ id: 'gone' }), liveEvent({ id: 'readded', title: 'Old' })]);
    const batch = new EventUpdateBatch(useEventsStore.getState);
    const notified = vi.fn();
    const off = useEventsStore.subscribe(notified);
    const message = (event: string, data: unknown) => ({
      event,
      id: null,
      data: JSON.stringify(data),
    });
    batch.receive(message('event.expire', { ids: ['gone', 'readded'], count: 2 }));
    batch.receive(
      message('event.upsert', { events: [liveEvent({ id: 'readded', title: 'New' })] }),
    );
    batch.receive(message('event.upsert', { events: [liveEvent({ id: 'fresh' })] }));
    vi.runAllTimers();
    off();
    expect(notified).toHaveBeenCalledOnce();
    const { byId } = useEventsStore.getState();
    expect(Object.keys(byId).sort()).toEqual(['fresh', 'readded']);
    expect(byId.readded?.title).toBe('New');
  } finally {
    vi.useRealTimers();
  }
});

it('merges a batch into the sorted list in exactly the order of a full sort', () => {
  const mirror = fullMirror();
  const byId = Object.fromEntries(mirror.map((event) => [event.id, event]));
  const previous = toList(byId);
  // Shuffled timestamps, ties broken by id, replacements and removals.
  const next = { ...byId };
  for (let i = 0; i < 400; i++) {
    const id = `s${(i * 7_919) % 6_000}`;
    next[id] = streamEvent((i * 7_919) % 6_000, BASE + (i % 3) * 60_000, { title: `v${i}` });
  }
  for (let i = 0; i < 50; i++) Reflect.deleteProperty(next, `s${i * 13}`);
  next.tie = liveEvent({ id: 'tie', published_at: previous[10]!.published_at });
  const full = Object.values(next).sort(newestFirst);
  expect(toList(next, previous)).toEqual(full);
  // An unsorted previous list falls back to a full sort rather than trusting it.
  expect(toList(next, [...previous].reverse())).toEqual(full);
});
