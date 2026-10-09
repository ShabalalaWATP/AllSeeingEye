import { useCallback, useSyncExternalStore } from 'react';

import {
  readLocalPause,
  subscribeLocalPause,
  writeLocalPause,
} from '@/components/brand/localMotionPause';
import { useSystemReducedMotion } from '@/components/brand/useDeviceMotion';

/** Public controls save a device choice only, even when the visitor has an account. */
export function useProductMotionPause() {
  const systemReduced = useSystemReducedMotion();
  const chosenPause = useSyncExternalStore(subscribeLocalPause, readLocalPause, () => false);
  const toggle = useCallback(() => {
    if (!systemReduced) writeLocalPause(!chosenPause);
  }, [chosenPause, systemReduced]);
  return { paused: systemReduced || chosenPause, systemReduced, toggle };
}
