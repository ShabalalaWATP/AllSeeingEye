/** View mode for the root page: the 3D globe (default) or the flat Mercator map. */
import { create } from 'zustand';

export type ViewMode = 'globe' | 'map';

export interface GlobeState {
  mode: ViewMode;
  setMode: (mode: ViewMode) => void;
  toggleMode: () => void;
}

export const useGlobeStore = create<GlobeState>()((set) => ({
  mode: 'globe',
  setMode: (mode) => {
    set({ mode });
  },
  toggleMode: () => {
    set((state) => ({ mode: state.mode === 'globe' ? 'map' : 'globe' }));
  },
}));
