import { useLayoutEffect } from 'react';

import { useProfile } from '@/stores/profile';

/** The authenticated shell follows this account, never the last browser user. */
export function PersonalAppearance() {
  const { profile } = useProfile();
  const theme = profile?.appearance_theme ?? 'obsidian';
  const reduced = profile?.reduced_motion ?? false;
  useLayoutEffect(() => {
    const root = document.documentElement;
    root.dataset.appearance = theme;
    root.dataset.reducedMotion = String(reduced);
    return () => {
      delete root.dataset.appearance;
      delete root.dataset.reducedMotion;
    };
  }, [theme, reduced]);
  return null;
}
