import { afterEach, beforeEach, expect, it, vi } from 'vitest';

import * as api from '@/lib/api/events';
import type { LiveEvent } from '@/lib/api/eventSchemas';
import { liveEvent, storeStats } from '@/test/fixtures';

import { useEventsStore } from './events';
import { SNAPSHOT_LIMIT } from './events.limits';
import { SNAPSHOT_REFRESH_MS } from './events.refresh';

const ship = (id: string) =>
  liveEvent({ id, category: 'maritime', subtype: 'vessel_position', source_id: 'ais' });

// The primary page holds the first records; supplements return the vessels it cannot fit.
let primary: LiveEvent[] = [];
let supplement: LiveEvent[] = [];
let gate: Promise<void> | null = null;
let supplementWaiting = false;

function hint(categories?: readonly string[]) {
  useEventsStore.getState().handleStreamMessage({
    event: 'event.resync',
    data: JSON.stringify({ reason: 'snapshot_required', categories, source_id: 'ais' }),
    id: null,
  });
}

const ids = () => Object.keys(useEventsStore.getState().byId).sort();

beforeEach(() => {
  vi.useFakeTimers();
  useEventsStore.getState().reset();
  primary = [liveEvent({ id: 'quake' }), ship('near')];
  supplement = [ship('far'), ship('dropped')];
  gate = null;
  supplementWaiting = false;
  vi.spyOn(api, 'fetchStats').mockResolvedValue({
    ...storeStats,
    total: 4_000,
    per_category: [{ category: 'maritime', count: 2_000, oldest: null, newest: null }],
  });
  vi.spyOn(api, 'fetchEvents').mockImplementation(async (query = {}) => {
    if (query.limit === SNAPSHOT_LIMIT)
      return primary.filter(
        (event) => !query.categories || query.categories.includes(event.category),
      );
    supplementWaiting = true;
    if (gate) await gate;
    return query.military ? [] : supplement;
  });
});
afterEach(() => {
  useEventsStore.getState().reset();
  vi.useRealTimers();
});

it.each([
  ['a maritime partition', ['maritime']],
  ['every partition', undefined],
])('keeps supplement-only records visible while %s refreshes', async (_label, categories) => {
  await useEventsStore.getState().load();
  expect(ids()).toEqual(['dropped', 'far', 'near', 'quake']);
  const before = useEventsStore.getState().snapshotCount;

  let release!: () => void;
  gate = new Promise<void>((done) => (release = done));
  supplementWaiting = false;
  supplement = [ship('far'), ship('arrived')];
  hint(categories);
  await vi.advanceTimersByTimeAsync(SNAPSHOT_REFRESH_MS);

  // The primary page has arrived and the supplement is still pending.
  expect(supplementWaiting).toBe(true);
  expect(useEventsStore.getState().loading).toBe(true);
  expect(ids()).toEqual(['dropped', 'far', 'near', 'quake']);
  expect(useEventsStore.getState().snapshotCount).toBe(before);

  release();
  await vi.waitFor(() => expect(useEventsStore.getState().loading).toBe(false));
  expect(ids()).toEqual(['arrived', 'far', 'near', 'quake']);
});

it('still applies live updates and expiries that arrive during an atomic refresh', async () => {
  await useEventsStore.getState().load();
  let release!: () => void;
  gate = new Promise<void>((done) => (release = done));
  hint(['maritime']);
  await vi.advanceTimersByTimeAsync(SNAPSHOT_REFRESH_MS);
  expect(supplementWaiting).toBe(true);

  useEventsStore.getState().applyExpire(['far']);
  useEventsStore.getState().applyUpsert([ship('live')]);
  expect(useEventsStore.getState().byId.far).toBeUndefined();
  expect(useEventsStore.getState().byId.live).toBeDefined();

  release();
  await vi.waitFor(() => expect(useEventsStore.getState().loading).toBe(false));
  expect(ids()).toEqual(['dropped', 'live', 'near', 'quake']);
});
