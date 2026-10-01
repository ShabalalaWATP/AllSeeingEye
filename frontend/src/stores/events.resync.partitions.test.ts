import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import * as api from '@/lib/api/events';
import type { EventsQuery } from '@/lib/api/events';
import type { Category, LiveEvent, StoreStats } from '@/lib/api/eventSchemas';
import { ApiError } from '@/lib/api/errors';
import { liveEvent } from '@/test/fixtures';

import { useEventsStore } from './events';
import { MAX_REFRESH_RETRIES, SNAPSHOT_REFRESH_MS } from './events.refresh';
import { REFRESH_FAILED_ERROR } from './events.snapshot';

const busy: StoreStats = {
  total: 9_000,
  estimated_bytes: 1,
  budget_bytes: 10,
  per_category: (['maritime', 'aviation', 'space', 'disaster'] as const).map((category) => ({
    category,
    count: 2_000,
    oldest: null,
    newest: null,
  })),
};

const ship = (id: string, title = id) =>
  liveEvent({ id, title, category: 'maritime', subtype: 'vessel_position', source_id: 'ais' });
const plane = liveEvent({ id: 'plane', category: 'aviation', subtype: 'aircraft' });
const quake = liveEvent({ id: 'quake' });

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason: unknown) => void;
  const promise = new Promise<T>((done, fail) => {
    resolve = done;
    reject = fail;
  });
  return { promise, resolve, reject };
}

/** Answers each request from the records a server would hold, recording every query. */
function server(records: LiveEvent[]) {
  const queries: EventsQuery[] = [];
  const fetch = vi.spyOn(api, 'fetchEvents').mockImplementation((query = {}) => {
    queries.push(query);
    const wanted = query.categories;
    return Promise.resolve(
      records.filter((event) => wanted === undefined || wanted.includes(event.category)),
    );
  });
  return { queries, fetch };
}

function hint(categories?: readonly string[]) {
  useEventsStore.getState().handleStreamMessage({
    event: 'event.resync',
    data: JSON.stringify({ reason: 'snapshot_required', categories, source_id: 'ais' }),
    id: null,
  });
}

/** Distinct partitions a set of queries touched; an unscoped query touches everything. */
function partitions(queries: EventsQuery[]): (Category | 'all')[] {
  const touched = new Set<Category | 'all'>();
  for (const query of queries) {
    if (query.categories) for (const category of query.categories) touched.add(category);
    else if (query.sources?.some((source) => source.startsWith('celestrak'))) touched.add('space');
    else if (query.sources?.some((source) => source.startsWith('firms'))) touched.add('disaster');
    else touched.add('all');
  }
  return [...touched].sort();
}

async function loaded(records: LiveEvent[]) {
  const answer = server(records);
  await useEventsStore.getState().load();
  answer.queries.length = 0;
  return answer;
}

beforeEach(() => {
  vi.useFakeTimers();
  useEventsStore.getState().reset();
  vi.spyOn(api, 'fetchStats').mockResolvedValue(busy);
});
afterEach(() => {
  useEventsStore.getState().reset();
  vi.useRealTimers();
});

describe('a bulk maritime update', () => {
  it('requests only maritime partitions, where a full refresh requested every partition', async () => {
    const full = await loaded([ship('a'), plane, quake]);
    hint();
    await vi.advanceTimersByTimeAsync(SNAPSHOT_REFRESH_MS);
    const before = { requests: full.queries.length, partitions: partitions(full.queries) };

    full.queries.length = 0;
    hint(['maritime']);
    await vi.advanceTimersByTimeAsync(SNAPSHOT_REFRESH_MS);
    const after = { requests: full.queries.length, partitions: partitions(full.queries) };

    expect(before).toEqual({
      requests: 8,
      partitions: ['all', 'aviation', 'disaster', 'maritime', 'space'],
    });
    expect(after).toEqual({ requests: 3, partitions: ['maritime'] });
    expect(full.queries[0]).toMatchObject({
      categories: ['maritime'],
      limit: 2_000,
      sampling: 'geographic',
    });
  });

  it('replaces the whole partition and keeps unrelated records and their identity', async () => {
    const records = [ship('kept', 'Old position'), ship('gone'), plane, quake];
    const answer = await loaded(records);
    const before = useEventsStore.getState();
    useEventsStore.getState().select('plane');
    records.splice(0, 2, ship('kept', 'New position'), ship('new'));
    hint(['maritime']);
    await vi.advanceTimersByTimeAsync(SNAPSHOT_REFRESH_MS);
    const after = useEventsStore.getState();
    expect(answer.queries.every((query) => query.categories?.includes('maritime') ?? true)).toBe(
      true,
    );
    expect(Object.keys(after.byId).sort()).toEqual(['kept', 'new', 'plane', 'quake']);
    expect(after.byId.kept?.title).toBe('New position');
    expect(after.byId.plane).toBe(before.byId.plane);
    expect(after.byId.quake).toBe(before.byId.quake);
    expect(after.selectedId).toBe('plane');
    expect(after.snapshotCount).toBe(4);
  });

  it('keeps known data visible and lets newer deltas win over the refresh response', async () => {
    await loaded([ship('kept', 'Snapshot'), ship('expiring'), plane]);
    const response = deferred<LiveEvent[]>();
    vi.mocked(api.fetchEvents).mockReturnValueOnce(response.promise);
    hint(['maritime']);
    await vi.advanceTimersByTimeAsync(SNAPSHOT_REFRESH_MS);
    expect(useEventsStore.getState()).toMatchObject({ loading: true, error: null });
    expect(useEventsStore.getState().list).toHaveLength(3);

    const store = useEventsStore.getState();
    store.applyUpsert([ship('kept', 'Newest delta'), liveEvent({ id: 'arrived' })]);
    store.applyExpire(['expiring']);
    response.resolve([ship('kept', 'Older response'), ship('expiring')]);
    await vi.advanceTimersByTimeAsync(0);
    await vi.waitFor(() => expect(useEventsStore.getState().loading).toBe(false));
    const { byId } = useEventsStore.getState();
    expect(byId.kept?.title).toBe('Newest delta');
    expect(byId.expiring).toBeUndefined();
    expect(Object.keys(byId).sort()).toEqual(['arrived', 'kept', 'plane']);
  });
});

it('coalesces hints into one refresh of every named partition', async () => {
  const answer = await loaded([ship('a'), plane, quake]);
  hint(['maritime']);
  hint(['aviation', 'maritime']);
  await vi.advanceTimersByTimeAsync(SNAPSHOT_REFRESH_MS);
  expect(answer.queries[0]?.categories).toEqual(['maritime', 'aviation']);
  expect(partitions(answer.queries)).toEqual(['aviation', 'maritime']);
});

it.each([[undefined], [[]], [['maritime', 'weather']]])(
  'falls back to a full refresh for missing or unknown partitions (%j)',
  async (categories) => {
    const answer = await loaded([ship('a'), plane]);
    hint(categories);
    await vi.advanceTimersByTimeAsync(SNAPSHOT_REFRESH_MS);
    expect(answer.queries[0]?.categories).toBeUndefined();
    expect(partitions(answer.queries)).toContain('all');
  },
);

it('takes a full snapshot when the mirror never completed one', async () => {
  const answer = server([ship('a'), plane]);
  vi.mocked(api.fetchStats).mockRejectedValueOnce(new ApiError(500, 'internal', 'Failed'));
  await useEventsStore.getState().load();
  answer.queries.length = 0;
  hint(['maritime']);
  await vi.advanceTimersByTimeAsync(SNAPSHOT_REFRESH_MS);
  expect(answer.queries[0]?.categories).toBeUndefined();
  expect(Object.keys(useEventsStore.getState().byId).sort()).toEqual(['a', 'plane']);
});

it('retries a rate-limited refresh without erasing the last valid snapshot', async () => {
  const records = [ship('a', 'First'), plane];
  const answer = await loaded(records);
  const limited = () => Promise.reject(new ApiError(429, 'rate_limited', 'Too many requests'));
  answer.fetch.mockImplementationOnce(limited);
  hint(['maritime']);
  await vi.advanceTimersByTimeAsync(SNAPSHOT_REFRESH_MS);
  expect(useEventsStore.getState()).toMatchObject({ error: null, loading: false });
  expect(Object.keys(useEventsStore.getState().byId).sort()).toEqual(['a', 'plane']);

  records[0] = ship('a', 'Second');
  await vi.advanceTimersByTimeAsync(SNAPSHOT_REFRESH_MS);
  expect(useEventsStore.getState().byId.a?.title).toBe('Second');
  expect(answer.queries.filter((query) => query.categories?.[0] === 'maritime')).toHaveLength(3);

  // Persistent failure stops after bounded, slower retries and says so, keeping the data.
  answer.fetch.mockImplementation(limited);
  answer.queries.length = 0;
  hint(['maritime']);
  await vi.advanceTimersByTimeAsync(SNAPSHOT_REFRESH_MS * 2 ** (MAX_REFRESH_RETRIES + 1));
  expect(answer.fetch.mock.calls.length).toBeGreaterThan(MAX_REFRESH_RETRIES);
  expect(useEventsStore.getState().error).toBe(REFRESH_FAILED_ERROR);
  expect(useEventsStore.getState().byId.a?.title).toBe('Second');
  const calls = answer.fetch.mock.calls.length;
  await vi.advanceTimersByTimeAsync(SNAPSHOT_REFRESH_MS * 10);
  expect(answer.fetch.mock.calls.length).toBe(calls);
});

it.each([
  ['a stream gap', () => hintGap()],
  ['a new viewport', () => useEventsStore.getState().setCoverageBounds([0, 0, 10, 10])],
])('discards a partition response superseded by %s', async (_, supersede) => {
  await loaded([ship('a', 'Before'), plane]);
  const response = deferred<LiveEvent[]>();
  vi.mocked(api.fetchEvents).mockReturnValueOnce(response.promise);
  hint(['maritime']);
  await vi.advanceTimersByTimeAsync(SNAPSHOT_REFRESH_MS);
  supersede();
  response.resolve([ship('a', 'Stale response'), ship('stale')]);
  await vi.advanceTimersByTimeAsync(0);
  expect(useEventsStore.getState().byId.stale).toBeUndefined();
  expect(useEventsStore.getState().byId.a?.title).not.toBe('Stale response');
});

function hintGap() {
  useEventsStore.getState().handleStreamMessage({
    event: 'event.resync',
    data: JSON.stringify({ reason: 'stream_gap', categories: ['maritime'] }),
    id: null,
  });
}

it('clears a selected record that left its refreshed partition', async () => {
  const records = [ship('chosen'), plane];
  await loaded(records);
  useEventsStore.getState().select('chosen');
  records.splice(0, 1);
  hint(['maritime']);
  await vi.advanceTimersByTimeAsync(SNAPSHOT_REFRESH_MS);
  expect(useEventsStore.getState().selectedId).toBeNull();
  expect(useEventsStore.getState().byId.plane).toBeDefined();
});
