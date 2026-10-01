/**
 * Client-side replay over the events this browser already holds. It orders records by
 * the map's own time basis (mapRecordTime), so it never substitutes a retrieval time,
 * and it makes no requests: replay is bounded by what the live store still retains.
 */
import type { LiveEvent } from '@/lib/api/eventSchemas';
import { mapRecordTime } from '@/lib/newsMapTime';

export const REPLAY_STEP_MS = 3_600_000;

export type ReplayBoundary = 'start' | 'end';

export interface ReplayIndex {
  /** Record times aligned with the indexed events; NaN marks an unusable time. */
  readonly times: Float64Array;
  /** The oldest usable time: the retention boundary of what is held, or null. */
  readonly start: number | null;
  readonly end: number | null;
  readonly usable: number;
  readonly excluded: number;
  /** Slider positions after the first, one per hour, the last landing on `end`. */
  readonly steps: number;
}

/** One pass over the events: parse each time once and find the retained span. */
export function indexReplay(events: readonly LiveEvent[]): ReplayIndex {
  const times = new Float64Array(events.length);
  let start = Infinity;
  let end = -Infinity;
  let usable = 0;
  events.forEach((event, position) => {
    const time = mapRecordTime(event);
    times[position] = time;
    if (!Number.isFinite(time)) return;
    usable += 1;
    if (time < start) start = time;
    if (time > end) end = time;
  });
  if (usable === 0) {
    return { times, start: null, end: null, usable, excluded: events.length, steps: 0 };
  }
  const steps = Math.ceil((end - start) / REPLAY_STEP_MS);
  return { times, start, end, usable, excluded: events.length - usable, steps };
}

/** Events that had appeared by the cursor. Undated events never appear in replay. */
export function filterReplay(
  events: readonly LiveEvent[],
  index: ReplayIndex,
  cursor: number,
): LiveEvent[] {
  if (index.start === null) return [];
  // NaN comparisons are false, so unusable times drop out here.
  return events.filter((_, position) => (index.times[position] ?? NaN) <= cursor);
}

/** Keeps a cursor inside the retained span, or null when nothing can be replayed. */
export function clampCursor(index: ReplayIndex, cursor: number | null): number | null {
  if (index.start === null || index.end === null) return null;
  if (cursor === null) return index.start;
  return Math.min(Math.max(cursor, index.start), index.end);
}

export function cursorAtStep(index: ReplayIndex, step: number): number {
  if (index.start === null || index.end === null) return NaN;
  const bounded = Math.min(Math.max(Math.round(step), 0), index.steps);
  return Math.min(index.start + bounded * REPLAY_STEP_MS, index.end);
}

export function stepOfCursor(index: ReplayIndex, cursor: number): number {
  const at = clampCursor(index, cursor);
  if (at === null || index.start === null) return 0;
  return Math.ceil((at - index.start) / REPLAY_STEP_MS);
}

export function replayBoundary(index: ReplayIndex, cursor: number | null): ReplayBoundary | null {
  const at = clampCursor(index, cursor);
  if (at === null) return null;
  if (at === index.start) return 'start';
  if (at === index.end) return 'end';
  return null;
}

/** One hour forward or back; a step past either end stays put and names that boundary. */
export function stepCursor(
  index: ReplayIndex,
  cursor: number | null,
  direction: 1 | -1,
): { cursor: number | null; blocked: ReplayBoundary | null } {
  const at = clampCursor(index, cursor);
  if (at === null || index.start === null) return { cursor: null, blocked: null };
  if (direction === -1 && at === index.start) return { cursor: at, blocked: 'start' };
  if (direction === 1 && at === index.end) return { cursor: at, blocked: 'end' };
  const offset = (at - index.start) / REPLAY_STEP_MS;
  const step = direction === 1 ? Math.floor(offset) + 1 : Math.ceil(offset) - 1;
  return { cursor: cursorAtStep(index, step), blocked: null };
}
