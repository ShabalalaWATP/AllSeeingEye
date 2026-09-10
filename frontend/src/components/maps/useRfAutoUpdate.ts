import { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react';
import { useAuthStore } from '@/stores/auth';
import { subscribeWorkspaceAccess } from '@/lib/workspaceAccess';

export const RF_AUTO_DEBOUNCE_MS = 1200;
export const RF_AUTO_INTERVAL_MS = 30000;
interface Options {
  identity: string;
  ready: boolean;
  busy: boolean;
  picking: boolean;
  run: () => Promise<void>;
  cancel: () => void;
}

/** Edits may schedule one attempt after an explicit run. No mount work, polling or retries. */
export function useRfAutoUpdate(options: Options) {
  const { identity, ready, busy, picking } = options;
  const [enabled, setEnabled] = useState(true);
  const [armed, setArmed] = useState(false);
  const latest = useRef(options);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const permitted = useRef(false);
  const attempted = useRef<string | null>(null);
  const lastAttempt = useRef(-Infinity);
  const autoInFlight = useRef(false);
  const attemptGeneration = useRef(0);
  useLayoutEffect(() => {
    latest.current = options;
  });
  const clearTimer = useCallback(() => {
    if (timer.current !== null) clearTimeout(timer.current);
    timer.current = null;
  }, []);
  const disarm = useCallback(() => {
    clearTimer();
    permitted.current = false;
    autoInFlight.current = false;
    attemptGeneration.current += 1;
    attempted.current = null;
    latest.current.cancel();
    setArmed(false);
  }, [clearTimer]);
  useEffect(() => {
    const account = () => {
      const state = useAuthStore.getState();
      return `${state.status}:${state.user?.id}:${state.user?.role}:${state.user?.is_active}`;
    };
    let original = account();
    const offAuth = useAuthStore.subscribe(() => {
      const next = account();
      if (next !== original) {
        original = next;
        disarm();
      }
    });
    const offAccess = subscribeWorkspaceAccess(disarm);
    return () => {
      clearTimer();
      permitted.current = false;
      latest.current.cancel();
      offAuth();
      offAccess();
    };
  }, [clearTimer, disarm]);
  const manuallyAnalyse = useCallback(() => {
    clearTimer();
    const current = latest.current;
    if (!current.ready || current.busy || current.picking) return;
    permitted.current = true;
    autoInFlight.current = false;
    attemptGeneration.current += 1;
    attempted.current = current.identity;
    lastAttempt.current = Date.now();
    setArmed(true);
    void current.run();
  }, [clearTimer]);
  useEffect(() => {
    clearTimer();
    if (
      !enabled ||
      !armed ||
      !permitted.current ||
      !ready ||
      busy ||
      picking ||
      attempted.current === identity
    )
      return;
    timer.current = setTimeout(
      () => {
        timer.current = null;
        const current = latest.current;
        if (
          !permitted.current ||
          !current.ready ||
          current.busy ||
          current.picking ||
          current.identity !== identity
        )
          return;
        attempted.current = identity;
        lastAttempt.current = Date.now();
        autoInFlight.current = true;
        const generation = ++attemptGeneration.current;
        void current.run().finally(() => {
          if (generation === attemptGeneration.current) autoInFlight.current = false;
        });
      },
      Math.max(RF_AUTO_DEBOUNCE_MS, lastAttempt.current + RF_AUTO_INTERVAL_MS - Date.now()),
    );
    return clearTimer;
  }, [identity, ready, busy, picking, enabled, armed, clearTimer]);
  const changeEnabled = useCallback(
    (value: boolean) => {
      clearTimer();
      if (!value && autoInFlight.current) latest.current.cancel();
      setEnabled(value);
    },
    [clearTimer],
  );
  return { enabled, armed, setEnabled: changeEnabled, manuallyAnalyse, disarm };
}
