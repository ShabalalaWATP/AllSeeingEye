/**
 * Environment signals the small brand mark reacts to: the user's reduced-motion
 * preference and whether the tab is visible. Both use useSyncExternalStore so
 * changes re-render without effects or local state.
 */
import { useSystemReducedMotion } from './useDeviceMotion';
export { usePageVisible, useSystemReducedMotion } from './useDeviceMotion';

import { useAuthStore } from '@/stores/auth';
import { useProfileStore } from '@/stores/profile';

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
