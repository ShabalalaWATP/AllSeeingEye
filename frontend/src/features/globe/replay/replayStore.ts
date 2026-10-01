/**
 * Replay mode for the live map. Session-only and never persisted: a reload or leaving
 * the map always returns to live. The cursor is an absolute time, so expiry of the
 * oldest events never silently moves the replayed moment.
 */
import { create } from 'zustand';

export interface ReplayState {
  active: boolean;
  /** Show events whose record time is at or before this instant (epoch milliseconds). */
  cursor: number | null;
  playing: boolean;
  /** The latest polite announcement, set only by discrete state changes. */
  announcement: string;
  update: (
    patch: Partial<Pick<ReplayState, 'active' | 'cursor' | 'playing' | 'announcement'>>,
  ) => void;
  returnToLive: (announce?: boolean) => void;
}

export const useReplayStore = create<ReplayState>()((set) => ({
  active: false,
  cursor: null,
  playing: false,
  announcement: '',
  update: (patch) => {
    set(patch);
  },
  returnToLive: (announce = true) => {
    set((state) => ({
      active: false,
      cursor: null,
      playing: false,
      announcement: announce && state.active ? 'Returned to live events.' : state.announcement,
    }));
  },
}));
