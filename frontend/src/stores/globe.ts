/** View mode and base layer for the root page: the 3D globe (default) or the flat Mercator map. */
import { create } from 'zustand';

export type ViewMode = 'globe' | 'map';

/** What is drawn under the data: the dark vector style, imagery, or OS raster tiles. */
export type BaseLayer = 'dark' | 'satellite' | 'hybrid' | 'os_road' | 'os_outdoor' | 'os_light';

export interface GlobeState {
  mode: ViewMode;
  baseLayer: BaseLayer;
  setMode: (mode: ViewMode) => void;
  toggleMode: () => void;
  setBaseLayer: (layer: BaseLayer) => void;
}

export const useGlobeStore = create<GlobeState>()((set) => ({
  mode: 'globe',
  baseLayer: 'dark',
  setMode: (mode) => {
    set({ mode });
  },
  setBaseLayer: (layer) => {
    set({ baseLayer: layer });
  },
  toggleMode: () => {
    set((state) => ({ mode: state.mode === 'globe' ? 'map' : 'globe' }));
  },
}));
