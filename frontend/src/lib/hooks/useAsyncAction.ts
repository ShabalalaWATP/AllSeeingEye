import { useCallback, useRef, useState } from 'react';

import { asApiError } from '@/lib/api/errors';
import type { ApiError } from '@/lib/api/errors';

export interface AsyncAction<Args extends unknown[]> {
  run: (...args: Args) => Promise<void>;
  busy: boolean;
  error: ApiError | null;
  clearError: () => void;
}

/**
 * Wraps an async handler with busy and error state. Errors are normalised to
 * ApiError so callers can branch on `code` and read field reasons.
 *
 * Only one attempt runs at a time: a `run` call made while an earlier one is
 * still pending is ignored. The guard is a ref, so it also holds before the
 * busy render commits (for example a second Enter press or a raw double submit).
 */
export function useAsyncAction<Args extends unknown[]>(
  action: (...args: Args) => Promise<void>,
): AsyncAction<Args> {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);
  const pending = useRef(false);

  const run = useCallback(
    async (...args: Args) => {
      if (pending.current) return;
      pending.current = true;
      setBusy(true);
      setError(null);
      try {
        await action(...args);
      } catch (caught) {
        setError(asApiError(caught));
      } finally {
        pending.current = false;
        setBusy(false);
      }
    },
    [action],
  );

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  return { run, busy, error, clearError };
}
