/** Installation capabilities and licence decisions; provider access waits for a valid response. */
import { create } from 'zustand';

import { fetchCapabilities, type SourceLicenceDecision } from '@/lib/api/capabilities';

export interface CapabilitiesState {
  osMaps: boolean;
  commercialUse: boolean | null;
  sourceLicences: Record<string, SourceLicenceDecision>;
  loaded: boolean;
  loading: boolean;
  error: string | null;
  load: (refresh?: boolean) => Promise<void>;
}

export const initialCapabilitiesState = {
  osMaps: false,
  commercialUse: null,
  sourceLicences: {} as Record<string, SourceLicenceDecision>,
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
      set({
        osMaps: capabilities.os_maps,
        commercialUse: capabilities.commercial_use,
        sourceLicences: capabilities.source_licences,
        loaded: true,
        loading: false,
      });
    } catch {
      set({ loading: false, error: 'Could not check the installation’s map licence policy.' });
    }
  },
}));
