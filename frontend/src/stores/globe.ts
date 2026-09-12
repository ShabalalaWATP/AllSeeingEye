/**
 * View state for the root page: the 3D globe (default) or the flat Mercator map, plus
 * the display preferences that survive a reload (base layer and lite mode).
 * Data overlays and the view mode reset each session: only conflicts start visible.
 */
import { create } from 'zustand';
import { createJSONStorage, persist } from 'zustand/middleware';
import { DEFAULT_BASE_LAYER, type BaseLayer } from '@/lib/map/baseLayers';

export type ViewMode = 'globe' | 'map';

export type { BaseLayer } from '@/lib/map/baseLayers';

export const GLOBE_PREFS_KEY = 'ase-globe-prefs';

export interface GlobeState {
  mode: ViewMode;
  baseLayer: BaseLayer;
  /** Draw the night hemisphere over the globe. */
  terminator: boolean;
  /** Drop atmosphere, animation and the terminator for weak GPUs or a wall display. */
  lite: boolean;
  /** Draw the GNSS interference cells from the aviation tracker. */
  interference: boolean;
  /** Wall-screen idle mode: no chrome, a turning globe, the ticker and the alerts. Never persisted. */
  opsRoom: boolean;
  setMode: (mode: ViewMode) => void;
  toggleMode: () => void;
  setBaseLayer: (layer: BaseLayer) => void;
  toggleTerminator: () => void;
  toggleLite: () => void;
  toggleInterference: () => void;
  setOpsRoom: (on: boolean) => void;
}

export const useGlobeStore = create<GlobeState>()(
  persist(
    (set) => ({
      mode: 'globe',
      baseLayer: DEFAULT_BASE_LAYER,
      terminator: false,
      lite: false,
      interference: false,
      opsRoom: false,
      setOpsRoom: (on) => {
        set({ opsRoom: on });
      },
      setMode: (mode) => {
        set({ mode });
      },
      toggleMode: () => {
        set((state) => ({ mode: state.mode === 'globe' ? 'map' : 'globe' }));
      },
      setBaseLayer: (layer) => {
        set({ baseLayer: layer });
      },
      toggleTerminator: () => {
        set((state) => ({ terminator: !state.terminator }));
      },
      toggleLite: () => {
        set((state) => ({ lite: !state.lite }));
      },
      toggleInterference: () => {
        set((state) => ({ interference: !state.interference }));
      },
    }),
    {
      name: GLOBE_PREFS_KEY,
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        baseLayer: state.baseLayer,
        lite: state.lite,
      }),
      // Older installations persisted overlays. Do not restore those switches on reload.
      merge: (saved, current) => {
        const preferences = saved as Partial<GlobeState> | null;
        const validLayers: BaseLayer[] = [
          'dark',
          'streets',
          'light',
          'satellite',
          'hybrid',
          'os_road',
          'os_outdoor',
          'os_light',
        ];
        return {
          ...current,
          baseLayer:
            preferences?.baseLayer && validLayers.includes(preferences.baseLayer)
              ? preferences.baseLayer
              : current.baseLayer,
          lite: typeof preferences?.lite === 'boolean' ? preferences.lite : current.lite,
          terminator: false,
          interference: false,
        };
      },
    },
  ),
);
