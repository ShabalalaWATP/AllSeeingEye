/** Account preferences are memory-only and discarded when the signed-in identity changes. */
import { useEffect } from 'react';
import { create } from 'zustand';

import { describeError } from '@/lib/api/errors';
import { fetchProfile, updateProfile } from '@/lib/api/profile';
import type { Profile, ProfileInput } from '@/lib/api/profile';

import { useAuthStore } from './auth';

interface ProfileState {
  owner: string | null;
  profile: Profile | null;
  loading: boolean;
  error: string | null;
  reload: () => Promise<void>;
  save: (input: ProfileInput) => Promise<Profile | null>;
}
let generation = 0;
let readController: AbortController | null = null;
let writeController: AbortController | null = null;
const empty = { owner: null, profile: null, loading: false, error: null };

export const useProfileStore = create<ProfileState>()((set, get) => ({
  ...empty,
  reload: async () => {
    const owner = useAuthStore.getState().user?.id;
    if (!owner || writeController) return;
    readController?.abort();
    const controller = new AbortController();
    readController = controller;
    const version = generation;
    set({ owner, loading: true, error: null });
    try {
      const profile = await fetchProfile(controller.signal);
      if (!controller.signal.aborted && version === generation) set({ profile });
    } catch (error) {
      if (!controller.signal.aborted && version === generation)
        set({ error: describeError(error) });
    } finally {
      if (readController === controller) {
        readController = null;
        set({ loading: false });
      }
    }
  },
  save: async (input) => {
    const owner = useAuthStore.getState().user?.id;
    if (!owner || get().owner !== owner || writeController) return null;
    readController?.abort();
    readController = null;
    const controller = new AbortController();
    writeController = controller;
    const version = generation;
    set({ error: null, loading: false });
    try {
      const profile = await updateProfile(input, controller.signal);
      if (controller.signal.aborted || version !== generation) return null;
      set({ profile });
      useAuthStore.setState((state) =>
        state.user?.id === owner
          ? { user: { ...state.user, display_name: profile.display_name } }
          : {},
      );
      return profile;
    } catch (error) {
      if (!controller.signal.aborted && version === generation)
        set({ error: describeError(error) });
      return null;
    } finally {
      if (writeController === controller) writeController = null;
    }
  },
}));

useAuthStore.subscribe((state, previous) => {
  if (state.user?.id === previous.user?.id && state.status === previous.status) return;
  generation += 1;
  readController?.abort();
  writeController?.abort();
  readController = null;
  writeController = null;
  useProfileStore.setState(empty);
});

export function useProfile() {
  const actorId = useAuthStore((state) => state.user?.id);
  const state = useProfileStore();
  useEffect(() => {
    const current = useProfileStore.getState();
    if (actorId && current.owner !== actorId) void current.reload();
  }, [actorId]);
  return {
    profile: state.owner === actorId ? state.profile : null,
    loading: Boolean(actorId) && (state.owner !== actorId || state.loading),
    error: state.owner === actorId ? state.error : null,
    reload: state.reload,
    save: state.save,
  };
}
