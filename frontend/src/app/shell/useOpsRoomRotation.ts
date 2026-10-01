/**
 * Cycles the ops room through a saved playlist. Every entry is re-read under the viewer's
 * current access when it comes round, and the playlist itself at the start of each cycle,
 * so a deleted or newly private entry is skipped with a notice instead of being shown from
 * memory. Time only counts while the tab is visible and nobody is interacting.
 */
import { useCallback, useEffect, useRef, useState } from 'react';

import { usePageVisible } from '@/components/brand/useMotionPreferences';
import { fetchAois } from '@/lib/api/direction';
import { getLiveView, getPlaylist } from '@/lib/api/liveViews';
import type { PlaylistEntry } from '@/lib/liveViews/opsPlaylist';
import { useLiveViewStore } from '@/stores/liveView';

/** How long an interaction holds the rotation before it carries on by itself. */
export const INTERACTION_HOLD_MS = 60_000;

export interface ShownEntry {
  seq: number;
  index: number;
  total: number;
  caption: string;
}

let sequence = 0;

async function present(entry: PlaylistEntry, signal: AbortSignal): Promise<string | null> {
  const store = useLiveViewStore.getState();
  if (entry.kind === 'view') {
    const { document, view } = await getLiveView(entry.id, signal);
    if (signal.aborted) return null;
    store.openView(view);
    return entry.caption || document.title;
  }
  const area = (await fetchAois()).find((item) => item.id === entry.id);
  if (signal.aborted) return null;
  if (!area) throw new Error('Area unavailable.');
  store.focusArea(area.id);
  return entry.caption || area.name;
}

export function useOpsRoomRotation(playlistId: string | null) {
  const stopPlaylist = useLiveViewStore((state) => state.stopPlaylist);
  const visible = usePageVisible();
  const [cursor, setCursor] = useState({ index: 0, seq: 0 });
  const [shown, setShown] = useState<ShownEntry | null>(null);
  const [skipped, setSkipped] = useState<string | null>(null);
  const [paused, setPaused] = useState(false);
  const [held, setHeld] = useState(false);
  const entries = useRef<PlaylistEntry[] | null>(null);
  const remaining = useRef({ seq: 0, ms: 0 });

  useEffect(() => {
    if (!playlistId) return;
    const controller = new AbortController();
    const { signal } = controller;
    void (async () => {
      let list = entries.current;
      if (cursor.index === 0 || !list) {
        try {
          list = (await getPlaylist(playlistId, signal)).playlist.entries;
        } catch {
          if (!signal.aborted)
            stopPlaylist('This playlist is unavailable or you no longer have access.');
          return;
        }
        if (signal.aborted) return;
        entries.current = list;
      }
      for (let attempt = 0; attempt < list.length; attempt += 1) {
        const index = cursor.index + attempt;
        if (index >= list.length) {
          // Wrapping round re-reads the playlist itself before carrying on.
          setCursor((previous) => ({ index: 0, seq: previous.seq + 1 }));
          return;
        }
        const entry = list[index];
        if (!entry) continue;
        try {
          const caption = await present(entry, signal);
          if (caption === null || signal.aborted) return;
          const seq = ++sequence;
          remaining.current = { seq, ms: entry.dwell_seconds * 1000 };
          setShown({ seq, index, total: list.length, caption });
          return;
        } catch {
          if (signal.aborted) return;
          setSkipped(
            `Skipped ${String(index + 1)}${entry.caption ? ` (${entry.caption})` : ''}: ` +
              'unavailable or no longer shared with you.',
          );
        }
      }
      stopPlaylist('No playlist entries are available to you.');
    })();
    return () => controller.abort();
  }, [cursor, playlistId, stopPlaylist]);

  const running = shown !== null && visible && !paused && !held;
  useEffect(() => {
    if (!running) return;
    const { seq, index, total } = shown;
    const started = Date.now();
    const timer = setTimeout(
      () => setCursor((previous) => ({ index: (index + 1) % total, seq: previous.seq + 1 })),
      remaining.current.seq === seq ? remaining.current.ms : 0,
    );
    return () => {
      clearTimeout(timer);
      if (remaining.current.seq === seq)
        remaining.current = { seq, ms: Math.max(0, remaining.current.ms - (Date.now() - started)) };
    };
  }, [running, shown]);

  const hold = useRef<ReturnType<typeof setTimeout> | null>(null);
  const interact = useCallback(() => {
    setHeld(true);
    if (hold.current) clearTimeout(hold.current);
    hold.current = setTimeout(() => setHeld(false), INTERACTION_HOLD_MS);
  }, []);
  useEffect(
    () => () => {
      if (hold.current) clearTimeout(hold.current);
    },
    [],
  );

  const step = (offset: number) => {
    if (!shown) return;
    setCursor((previous) => ({
      index: (shown.index + offset + shown.total) % shown.total,
      seq: previous.seq + 1,
    }));
  };
  return {
    shown,
    skipped,
    paused,
    held,
    interact,
    pause: () => setPaused(true),
    resume: () => {
      if (hold.current) clearTimeout(hold.current);
      setHeld(false);
      setPaused(false);
    },
    next: () => step(1),
    previous: () => step(-1),
    stop: () => stopPlaylist(),
  };
}
