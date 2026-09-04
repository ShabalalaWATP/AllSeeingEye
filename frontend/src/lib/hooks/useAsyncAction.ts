import { useCallback, useState } from 'react';

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
 */
export function useAsyncAction<Args extends unknown[]>(
  action: (...args: Args) => Promise<void>,
): AsyncAction<Args> {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);

  const run = useCallback(
    async (...args: Args) => {
      setBusy(true);
      setError(null);
      try {
        await action(...args);
      } catch (caught) {
        setError(asApiError(caught));
      } finally {
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
