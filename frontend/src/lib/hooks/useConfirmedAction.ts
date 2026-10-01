import { useCallback, useRef, useState } from 'react';

import { asApiError } from '@/lib/api/errors';
import type { ApiError } from '@/lib/api/errors';

export interface ConfirmedAction<Target> {
  /** What the open confirmation is about, or null when none is open. */
  target: Target | null;
  busy: boolean;
  error: ApiError | null;
  /** Open the confirmation for one object. Nothing is sent yet. */
  ask: (target: Target) => void;
  /** Close without sending. Ignored while the request runs, since it cannot be recalled. */
  cancel: () => void;
  /** Send the request once. Repeats while it runs are ignored. */
  confirm: () => void;
}

/**
 * Holds a consequential action behind an explicit confirmation. The request is sent only
 * by `confirm`, at most once at a time (the guard is a ref, so it holds before the busy
 * render commits). Success closes the confirmation; a failure keeps it open with the
 * error normalised to ApiError, so the reader can retry or cancel. Authorisation stays
 * with the server: this only decides when the request is sent.
 */
export function useConfirmedAction<Target>(
  action: (target: Target) => Promise<void>,
): ConfirmedAction<Target> {
  const [target, setTarget] = useState<Target | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);
  const pending = useRef(false);

  const ask = useCallback((next: Target) => {
    if (pending.current) return;
    setError(null);
    setTarget(next);
  }, []);

  const cancel = useCallback(() => {
    if (pending.current) return;
    setError(null);
    setTarget(null);
  }, []);

  const confirm = useCallback(() => {
    if (target === null || pending.current) return;
    pending.current = true;
    setBusy(true);
    setError(null);
    void (async () => {
      try {
        await action(target);
        setTarget(null);
      } catch (caught) {
        setError(asApiError(caught));
      } finally {
        pending.current = false;
        setBusy(false);
      }
    })();
  }, [action, target]);

  return { target, busy, error, ask, cancel, confirm };
}
