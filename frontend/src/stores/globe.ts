/**
 * View state for the root page: the 3D globe (default) or the flat Mercator map, plus
 * the display preferences that survive a reload (base layer, terminator, lite mode).
 * The view mode is deliberately not persisted: every session starts on the globe.
 */
import { create } from 'zustand';
import { createJSONStorage, persist } from 'zustand/middleware';

export type ViewMode = 'globe' | 'map';

/** What is drawn under the data: the dark vector style, imagery, or OS raster tiles. */
export type BaseLayer = 'dark' | 'satellite' | 'hybrid' | 'os_road' | 'os_outdoor' | 'os_light';

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
  setMode: (mode: ViewMode) => void;
  toggleMode: () => void;
  setBaseLayer: (layer: BaseLayer) => void;
  toggleTerminator: () => void;
  toggleLite: () => void;
  toggleInterference: () => void;
}

export const useGlobeStore = create<GlobeState>()(
  persist(
    (set) => ({
      mode: 'globe',
      baseLayer: 'dark',
      terminator: true,
      lite: false,
      interference: false,
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
        terminator: state.terminator,
        lite: state.lite,
        interference: state.interference,
      }),
    },
  ),
);
