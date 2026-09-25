/**
 * Accessibility preferences kept in this browser, like the shell layout. Single-key
 * shortcuts can be turned off (WCAG 2.1.4) for speech input or stray key presses.
 * Nothing here is account data.
 */
import { create } from 'zustand';
import { createJSONStorage, persist } from 'zustand/middleware';

import { safeLocalStorage } from '@/lib/safeStorage';

export const PREFERENCES_KEY = 'ase-preferences';

export interface PreferencesState {
  singleKeyShortcuts: boolean;
  setSingleKeyShortcuts: (enabled: boolean) => void;
  /** Keyboard shortcut help visibility. Session only; never written to storage. */
  shortcutHelpOpen: boolean;
  openShortcutHelp: () => void;
  closeShortcutHelp: () => void;
}

export const usePreferencesStore = create<PreferencesState>()(
  persist(
    (set) => ({
      singleKeyShortcuts: true,
      setSingleKeyShortcuts: (singleKeyShortcuts) => {
        set({ singleKeyShortcuts });
      },
      shortcutHelpOpen: false,
      openShortcutHelp: () => {
        set({ shortcutHelpOpen: true });
      },
      closeShortcutHelp: () => {
        set({ shortcutHelpOpen: false });
      },
    }),
    {
      name: PREFERENCES_KEY,
      storage: createJSONStorage(() => safeLocalStorage),
      partialize: (state) => ({ singleKeyShortcuts: state.singleKeyShortcuts }),
      merge: (saved, current) => {
        const stored = (saved as Partial<PreferencesState> | null)?.singleKeyShortcuts;
        return {
          ...current,
          singleKeyShortcuts: typeof stored === 'boolean' ? stored : current.singleKeyShortcuts,
        };
      },
    },
  ),
);
