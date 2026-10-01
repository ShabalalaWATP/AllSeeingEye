/** Applies replay to the map's event scope and owns playback; it never requests data. */
import { useCallback, useEffect, useMemo, useRef } from 'react';

import { useReducedMotion } from '@/components/brand/useMotionPreferences';
import type { LiveEvent } from '@/lib/api/eventSchemas';
import { formatUtc } from '@/lib/format';

import {
  clampCursor,
  cursorAtStep,
  filterReplay,
  indexReplay,
  replayBoundary,
  stepCursor,
} from './liveReplay';
import { useReplayStore } from './replayStore';

/** One replayed hour per second while playing. */
export const REPLAY_TICK_MS = 1_000;

export function formatReplayTime(cursor: number | null): string {
  return cursor === null || !Number.isFinite(cursor)
    ? 'Unknown'
    : formatUtc(new Date(cursor).toISOString());
}

export function boundaryMessage(boundary: 'start' | 'end', cursor: number | null): string {
  return boundary === 'start'
    ? `Start of the retained window, ${formatReplayTime(cursor)}. Older events have expired from the live store or sit outside the chosen time window, so replay cannot go further back.`
    : `Newest retained event reached, ${formatReplayTime(cursor)}. Return to live to resume live updates.`;
}

export function useLiveReplay(events: LiveEvent[]) {
  const active = useReplayStore((state) => state.active);
  const stored = useReplayStore((state) => state.cursor);
  const playing = useReplayStore((state) => state.playing);
  const announcement = useReplayStore((state) => state.announcement);
  const update = useReplayStore((state) => state.update);
  const returnToLive = useReplayStore((state) => state.returnToLive);
  const reducedMotion = useReducedMotion();
  const index = useMemo(() => indexReplay(events), [events]);
  const cursor = active ? clampCursor(index, stored) : null;
  const shown = useMemo(
    () => (active ? (cursor === null ? [] : filterReplay(events, index, cursor)) : events),
    [active, cursor, events, index],
  );
  const boundary = active ? replayBoundary(index, cursor) : null;
  const latest = useRef({ index, cursor });
  useEffect(() => {
    latest.current = { index, cursor };
    // Expiry can move the retained boundary past the stored moment; keep the banner honest.
    if (active && cursor !== stored) update({ cursor });
  });

  const start = useCallback(() => {
    const first = latest.current.index.start;
    if (first === null) return;
    update({
      active: true,
      cursor: first,
      playing: false,
      announcement: `Replay started at ${formatReplayTime(first)}. The map is not live.`,
    });
  }, [update]);

  const step = useCallback(
    (direction: 1 | -1) => {
      const next = stepCursor(latest.current.index, latest.current.cursor, direction);
      update({
        cursor: next.cursor,
        playing: false,
        announcement:
          next.blocked === null
            ? `Replay at ${formatReplayTime(next.cursor)}.`
            : boundaryMessage(next.blocked, next.cursor),
      });
    },
    [update],
  );

  const scrub = useCallback(
    (position: number) => {
      update({ cursor: cursorAtStep(latest.current.index, position), playing: false });
    },
    [update],
  );

  const play = useCallback(() => {
    if (reducedMotion) return;
    const { index: current, cursor: at } = latest.current;
    const restart = at !== null && at === current.end;
    update({
      playing: true,
      cursor: restart ? current.start : at,
      announcement: 'Replay playing.',
    });
  }, [reducedMotion, update]);

  const pause = useCallback(() => {
    update({
      playing: false,
      announcement: `Replay paused at ${formatReplayTime(latest.current.cursor)}.`,
    });
  }, [update]);

  // Playback only advances the in-memory cursor. Reduced motion stops it outright.
  const running = active && playing && !reducedMotion;
  useEffect(() => {
    if (active && playing && reducedMotion) update({ playing: false });
    if (!running) return;
    const timer = setInterval(() => {
      const next = stepCursor(latest.current.index, latest.current.cursor, 1);
      if (next.blocked === null && next.cursor !== latest.current.index.end) {
        update({ cursor: next.cursor });
        return;
      }
      update({
        cursor: next.cursor,
        playing: false,
        announcement: boundaryMessage('end', next.cursor),
      });
    }, REPLAY_TICK_MS);
    return () => {
      clearInterval(timer);
    };
  }, [active, playing, reducedMotion, running, update]);

  // Leaving the map always returns it to live.
  useEffect(
    () => () => {
      returnToLive(false);
      update({ announcement: '' });
    },
    [returnToLive, update],
  );

  return {
    events: shown,
    index,
    total: events.length,
    active,
    playing: running,
    cursor,
    boundary,
    reducedMotion,
    announcement,
    start,
    step,
    scrub,
    play,
    pause,
    stop: returnToLive,
  };
}

export type LiveReplay = ReturnType<typeof useLiveReplay>;
