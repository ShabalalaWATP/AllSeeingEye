import { describe, expect, it, vi } from 'vitest';

import { liveEvent } from '@/test/fixtures';
import { useEventsStore } from '@/stores/events';

import {
  REPLAY_STEP_MS,
  cursorAtStep,
  filterReplay,
  indexReplay,
  replayBoundary,
  stepCursor,
  stepOfCursor,
} from './liveReplay';

const HOUR = 3_600_000;
const base = Date.UTC(2026, 8, 30, 0, 0);
const at = (hours: number) => new Date(base + hours * HOUR).toISOString();

const events = [
  liveEvent({ id: 'late', published_at: at(5.5) }),
  liveEvent({ id: 'early', published_at: at(0) }),
  liveEvent({ id: 'middle', published_at: at(2) }),
  liveEvent({ id: 'undated', published_at: null }),
  liveEvent({ id: 'garbled', published_at: 'not a time' }),
];

describe('indexReplay', () => {
  it('spans the usable times and counts the events it must exclude', () => {
    const index = indexReplay(events);
    expect(index.start).toBe(base);
    expect(index.end).toBe(base + 5.5 * HOUR);
    expect(index.usable).toBe(3);
    expect(index.excluded).toBe(2);
    // Hour steps from the oldest retained event, ending exactly on the newest.
    expect(index.steps).toBe(6);
    expect(REPLAY_STEP_MS).toBe(HOUR);
  });

  it('has nothing to replay when no event carries a usable time', () => {
    const index = indexReplay([liveEvent({ published_at: null })]);
    expect(index).toMatchObject({ start: null, end: null, usable: 0, excluded: 1, steps: 0 });
    expect(filterReplay(events, indexReplay([]), base)).toEqual([]);
  });

  it('uses the GDELT indexing time basis rather than the raw publication field', () => {
    const gdelt = liveEvent({
      id: 'gdelt',
      source_id: 'gdelt_news',
      category: 'news',
      published_at: at(1),
      source_dates: [],
    });
    expect(indexReplay([gdelt]).excluded).toBe(1);
  });

  it('indexes replacements and expiry without reparsing unchanged mirror records', () => {
    const store = useEventsStore.getState();
    store.reset();
    const upsert = (records: ReturnType<typeof liveEvent>[]) =>
      store.handleStreamMessage({
        event: 'event.upsert',
        id: null,
        data: JSON.stringify({ events: records }),
      });
    try {
      const early = liveEvent({ id: 'early-correction', published_at: at(0) });
      const later = liveEvent({ id: 'later', published_at: at(2) });
      upsert([early, later]);
      const first = useEventsStore.getState().list;
      const original = useEventsStore.getState().byId[early.id]!;
      const parse = vi.spyOn(Date, 'parse');
      expect(indexReplay(first)).toMatchObject({ start: base, end: base + 2 * HOUR });
      parse.mockClear();

      upsert([{ ...early, published_at: at(4) }]);
      const changed = useEventsStore.getState().list;
      expect(useEventsStore.getState().byId[early.id]).not.toBe(original);
      expect(original.published_at).toBe(at(0));
      expect(changed.find((event) => event.id === 'later')).toBe(first[0]);
      parse.mockClear();
      expect(indexReplay(changed)).toMatchObject({ start: base + 2 * HOUR, end: base + 4 * HOUR });
      expect(parse).toHaveBeenCalledTimes(1);

      store.applyExpire([early.id]);
      parse.mockClear();
      const remaining = useEventsStore.getState().list;
      const index = indexReplay(remaining);
      expect(index).toMatchObject({ start: base + 2 * HOUR, end: base + 2 * HOUR, usable: 1 });
      expect(filterReplay(remaining, index, base + 2 * HOUR).map((event) => event.id)).toEqual([
        'later',
      ]);
      expect(parse).not.toHaveBeenCalled();
    } finally {
      store.reset();
    }
  });
});

describe('filterReplay', () => {
  it('shows only events that had appeared by the cursor, never undated ones', () => {
    const index = indexReplay(events);
    expect(filterReplay(events, index, base).map((event) => event.id)).toEqual(['early']);
    expect(filterReplay(events, index, base + 2 * HOUR).map((event) => event.id)).toEqual([
      'early',
      'middle',
    ]);
    expect(filterReplay(events, index, base + 6 * HOUR)).toHaveLength(3);
  });
});

describe('stepping and scrubbing', () => {
  const index = indexReplay(events);

  it('maps slider steps to times that stop at the newest retained event', () => {
    expect(cursorAtStep(index, 0)).toBe(base);
    expect(cursorAtStep(index, 3)).toBe(base + 3 * HOUR);
    expect(cursorAtStep(index, 6)).toBe(base + 5.5 * HOUR);
    expect(cursorAtStep(index, 99)).toBe(base + 5.5 * HOUR);
    expect(cursorAtStep(index, -4)).toBe(base);
    expect(stepOfCursor(index, base + 3 * HOUR)).toBe(3);
    expect(stepOfCursor(index, base + 5.5 * HOUR)).toBe(6);
  });

  it('steps hour by hour and stops at the retention boundary', () => {
    expect(stepCursor(index, base, 1)).toEqual({ cursor: base + HOUR, blocked: null });
    expect(stepCursor(index, base + HOUR, -1)).toEqual({ cursor: base, blocked: null });
    expect(stepCursor(index, base, -1)).toEqual({ cursor: base, blocked: 'start' });
    expect(stepCursor(index, base + 5 * HOUR, 1)).toEqual({
      cursor: base + 5.5 * HOUR,
      blocked: null,
    });
    expect(stepCursor(index, base + 5.5 * HOUR, 1)).toEqual({
      cursor: base + 5.5 * HOUR,
      blocked: 'end',
    });
    expect(stepCursor(index, base + 5.5 * HOUR, -1)).toEqual({
      cursor: base + 5 * HOUR,
      blocked: null,
    });
  });

  it('moves an off-grid cursor to the neighbouring hour in either direction', () => {
    expect(stepCursor(index, base + 1.5 * HOUR, 1).cursor).toBe(base + 2 * HOUR);
    expect(stepCursor(index, base + 1.5 * HOUR, -1).cursor).toBe(base + HOUR);
  });

  it('names the boundary the cursor rests on', () => {
    expect(replayBoundary(index, base)).toBe('start');
    expect(replayBoundary(index, base + 5.5 * HOUR)).toBe('end');
    expect(replayBoundary(index, base + HOUR)).toBeNull();
    // A cursor left behind by expiry is clamped to the oldest retained event.
    expect(replayBoundary(index, base - HOUR)).toBe('start');
    expect(stepCursor(index, base - 3 * HOUR, 1).cursor).toBe(base + HOUR);
  });
});
