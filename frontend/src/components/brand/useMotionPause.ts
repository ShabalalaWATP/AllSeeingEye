/**
 * Whether the brand eye should hold still, and the viewer's control over it. The
 * operating system's reduced-motion request always wins; otherwise a pending or
 * failed account save for this session, then the account's saved preference or a
 * pre-sign-in device pause.
 */
import { useCallback, useSyncExternalStore } from 'react';

import { useAuthStore } from '@/stores/auth';

import {
  chooseMotionPause,
  readLocalPause,
  retryMotionPause,
  subscribeLocalPause,
  useMotionPauseStore,
} from './motionPause';
import { useAccountReducedMotion, useSystemReducedMotion } from './useMotionPreferences';

export interface MotionPause {
  /** The eye is held still, for whatever reason (the control's pressed state). */
  paused: boolean;
  /**
   * The viewer or account chose to pause, so the render loop stops. The device
   * request is applied separately by the existing still-frame settings.
   */
  chosenPause: boolean;
  /** The device requests reduced motion, so Resume cannot start the eye. */
  systemReduced: boolean;
  saving: boolean;
  /** The account preference could not be saved; the eye stays still this session. */
  failed: boolean;
  toggle: () => void;
  retry: () => void;
}

export function useMotionPause(): MotionPause {
  const actorId = useAuthStore((state) => state.user?.id ?? null);
  const systemReduced = useSystemReducedMotion();
  const accountPaused = useAccountReducedMotion();
  const localPaused = useSyncExternalStore(subscribeLocalPause, readLocalPause, () => false);
  const session = useMotionPauseStore((state) =>
    actorId !== null && state.session?.owner === actorId ? state.session : null,
  );
  const chosen = session !== null ? session.paused : accountPaused || localPaused;
  const saving = session?.saving ?? false;

  const toggle = useCallback(() => {
    if (systemReduced || saving) return;
    void chooseMotionPause(!chosen);
  }, [chosen, saving, systemReduced]);
  const retry = useCallback(() => {
    void retryMotionPause();
  }, []);

  return {
    paused: systemReduced || chosen,
    chosenPause: chosen,
    systemReduced,
    saving,
    failed: session?.failed ?? false,
    toggle,
    retry,
  };
}
