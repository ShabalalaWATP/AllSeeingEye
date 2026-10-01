import { useCallback, useRef, useState } from 'react';

import { asApiError } from '@/lib/api/errors';
import type { ApiError } from '@/lib/api/errors';

export interface AsyncAction<Args extends unknown[]> {
  run: (...args: Args) => Promise<void>;
  busy: boolean;
  error: ApiError | null;
  clearError: () => void;
}

// Arguments that cannot be serialised share one key, so such calls are never duplicated.
const UNKEYED = '\u0000unkeyed';

function keyOf(args: readonly unknown[]): string {
  try {
    return JSON.stringify(args);
  } catch {
    return UNKEYED;
  }
}

/**
 * Wraps an async handler with busy and error state. Errors are normalised to
 * ApiError so callers can branch on `code` and read field reasons.
 *
 * A call is ignored while an identical call (the same arguments) is still pending,
 * so a second Enter press or a raw double submit cannot send a request twice. The
 * guard is a ref, so it holds before the busy render commits. Calls with different
 * arguments, such as acknowledging two different alerts, still run independently,
 * and `busy` stays true until every pending call has settled.
 */
export function useAsyncAction<Args extends unknown[]>(
  action: (...args: Args) => Promise<void>,
): AsyncAction<Args> {
  const [pendingCount, setPendingCount] = useState(0);
  const [error, setError] = useState<ApiError | null>(null);
  const pending = useRef(new Set<string>());

  const run = useCallback(
    async (...args: Args) => {
      const key = keyOf(args);
      if (pending.current.has(key)) return;
      pending.current.add(key);
      setPendingCount((count) => count + 1);
      setError(null);
      try {
        await action(...args);
      } catch (caught) {
        setError(asApiError(caught));
      } finally {
        pending.current.delete(key);
        setPendingCount((count) => count - 1);
      }
    },
    [action],
  );

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  return { run, busy: pendingCount > 0, error, clearError };
}
