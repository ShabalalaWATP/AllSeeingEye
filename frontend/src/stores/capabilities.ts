/** What this server can offer beyond the defaults; unknown until asked, defaults when it fails. */
import { create } from 'zustand';

import { fetchCapabilities } from '@/lib/api/capabilities';

export interface CapabilitiesState {
  osMaps: boolean;
  loaded: boolean;
  loading: boolean;
  error: string | null;
  load: (refresh?: boolean) => Promise<void>;
}

export const initialCapabilitiesState = {
  osMaps: false,
  loaded: false,
  loading: false,
  error: null as string | null,
};

export const useCapabilitiesStore = create<CapabilitiesState>()((set, get) => ({
  ...initialCapabilitiesState,

  load: async (refresh = false) => {
    if (get().loading || (get().loaded && !refresh && !get().error)) return;
    set({ loading: true, error: null });
    try {
      const capabilities = await fetchCapabilities();
      set({ osMaps: capabilities.os_maps, loaded: true, loading: false });
    } catch {
      set({ loading: false, error: 'Could not check the server’s map connections.' });
    }
  },
}));
