/**
 * Environment signals the small brand mark reacts to: the user's reduced-motion
 * preference and whether the tab is visible. Both use useSyncExternalStore so
 * changes re-render without effects or local state.
 */
import { useSyncExternalStore } from 'react';

import { useAuthStore } from '@/stores/auth';
import { useProfileStore } from '@/stores/profile';

const REDUCED_MOTION_QUERY = '(prefers-reduced-motion: reduce)';

function mediaQuery(): MediaQueryList | null {
  if (typeof window.matchMedia !== 'function') return null;
  return window.matchMedia(REDUCED_MOTION_QUERY);
}

function subscribeReducedMotion(onChange: () => void): () => void {
  const query = mediaQuery();
  if (query === null) return () => undefined;
  query.addEventListener('change', onChange);
  return () => {
    query.removeEventListener('change', onChange);
  };
}

function readReducedMotion(): boolean {
  return mediaQuery()?.matches ?? false;
}

/** The operating system's reduced-motion request alone, which nothing in the app overrides. */
export function useSystemReducedMotion(): boolean {
  return useSyncExternalStore(subscribeReducedMotion, readReducedMotion, () => false);
}

/** The signed-in account's saved reduced-motion preference, never another account's. */
export function useAccountReducedMotion(): boolean {
  const actorId = useAuthStore((state) => state.user?.id);
  return useProfileStore(
    (state) => state.owner === actorId && (state.profile?.reduced_motion ?? false),
  );
}

export function useReducedMotion(): boolean {
  const preference = useAccountReducedMotion();
  const system = useSystemReducedMotion();
  return system || preference;
}

function subscribeVisibility(onChange: () => void): () => void {
  document.addEventListener('visibilitychange', onChange);
  return () => {
    document.removeEventListener('visibilitychange', onChange);
  };
}

function readVisible(): boolean {
  return document.visibilityState === 'visible';
}

export function usePageVisible(): boolean {
  return useSyncExternalStore(subscribeVisibility, readVisible, () => true);
}
