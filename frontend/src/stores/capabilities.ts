/** What this server can offer beyond the defaults; unknown until asked, defaults when it fails. */
import { create } from 'zustand';

import { fetchCapabilities } from '@/lib/api/capabilities';

export interface CapabilitiesState {
  osMaps: boolean;
  loaded: boolean;
  load: () => Promise<void>;
}

export const initialCapabilitiesState = { osMaps: false, loaded: false };

export const useCapabilitiesStore = create<CapabilitiesState>()((set, get) => ({
  ...initialCapabilitiesState,

  load: async () => {
    if (get().loaded) return;
    try {
      const capabilities = await fetchCapabilities();
      set({ osMaps: capabilities.os_maps, loaded: true });
    } catch {
      set({ loaded: true });
    }
  },
}));
