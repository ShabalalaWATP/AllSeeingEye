/**
 * Hand-off between whoever opens a live view (the saved-views panel, a link or the ops-room
 * rotation) and the map that applies it. Session memory only: nothing here is persisted,
 * so no view is restored at sign-in. Any change of account or workspace access clears it
 * and stops a rotating playlist, so no stale private state keeps cycling on a wall.
 */
import { create } from 'zustand';

import type { LiveViewState } from '@/lib/liveViews/liveViewState';
import { subscribeWorkspaceAccess } from '@/lib/workspaceAccess';
import { useAuthStore } from './auth';
import { useGlobeStore } from './globe';

export type LiveViewRequest =
  | { nonce: number; kind: 'view'; view: LiveViewState }
  | { nonce: number; kind: 'area'; areaId: string };

interface LiveViewStore {
  request: LiveViewRequest | null;
  /** The playlist the ops room is rotating through, if any. */
  playlistId: string | null;
  /** Why the last rotation stopped, shown on the wall until it is dismissed. */
  rotationNotice: string | null;
  openView: (view: LiveViewState) => void;
  focusArea: (areaId: string) => void;
  consume: (nonce: number) => void;
  startPlaylist: (id: string) => void;
  stopPlaylist: (notice?: string) => void;
  dismissNotice: () => void;
  reset: () => void;
}

let nonce = 0;

export const useLiveViewStore = create<LiveViewStore>()((set, get) => ({
  request: null,
  playlistId: null,
  rotationNotice: null,
  openView: (view) => set({ request: { nonce: ++nonce, kind: 'view', view } }),
  focusArea: (areaId) => set({ request: { nonce: ++nonce, kind: 'area', areaId } }),
  consume: (done) => {
    if (get().request?.nonce === done) set({ request: null });
  },
  startPlaylist: (id) => set({ playlistId: id, rotationNotice: null }),
  stopPlaylist: (notice) => set({ playlistId: null, rotationNotice: notice ?? null }),
  dismissNotice: () => set({ rotationNotice: null }),
  reset: () =>
    set((state) => ({
      request: null,
      playlistId: null,
      rotationNotice:
        state.playlistId === null ? null : 'The rotation stopped because your access changed.',
    })),
}));

useAuthStore.subscribe((next, previous) => {
  if (
    next.status !== previous.status ||
    next.user?.id !== previous.user?.id ||
    next.user?.role !== previous.user?.role ||
    next.user?.is_active !== previous.user?.is_active
  ) {
    useLiveViewStore.getState().reset();
    if (next.status !== 'authenticated') useLiveViewStore.getState().dismissNotice();
  }
});
// Leaving the ops room, by Escape or its exit button, ends the rotation.
useGlobeStore.subscribe((next, previous) => {
  if (previous.opsRoom && !next.opsRoom) useLiveViewStore.getState().stopPlaylist();
});
subscribeWorkspaceAccess(() => useLiveViewStore.getState().reset());
