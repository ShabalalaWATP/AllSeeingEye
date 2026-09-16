/**
 * Shell layout preferences that survive a reload: whether the left rail is collapsed
 * to icons. Nothing here is account data; it is a per-browser convenience.
 */
import { create } from 'zustand';
import { createJSONStorage, persist } from 'zustand/middleware';

export const SHELL_PREFS_KEY = 'ase-shell-prefs';

export interface ShellState {
  railCollapsed: boolean;
  setRailCollapsed: (collapsed: boolean) => void;
  toggleRail: () => void;
  /** Search palette visibility. Session only; never written to storage. */
  paletteOpen: boolean;
  openPalette: () => void;
  closePalette: () => void;
}

export const useShellStore = create<ShellState>()(
  persist(
    (set) => ({
      railCollapsed: false,
      setRailCollapsed: (railCollapsed) => {
        set({ railCollapsed });
      },
      toggleRail: () => {
        set((state) => ({ railCollapsed: !state.railCollapsed }));
      },
      paletteOpen: false,
      openPalette: () => {
        set({ paletteOpen: true });
      },
      closePalette: () => {
        set({ paletteOpen: false });
      },
    }),
    {
      name: SHELL_PREFS_KEY,
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({ railCollapsed: state.railCollapsed }),
      merge: (saved, current) => ({
        ...current,
        railCollapsed:
          typeof (saved as Partial<ShellState> | null)?.railCollapsed === 'boolean'
            ? Boolean((saved as Partial<ShellState>).railCollapsed)
            : current.railCollapsed,
      }),
    },
  ),
);
