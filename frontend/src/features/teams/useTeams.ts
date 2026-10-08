import { useCallback, useEffect, useRef, useState } from 'react';

import { asApiError, describeError } from '@/lib/api/errors';
import type { ApiError } from '@/lib/api/errors';

/**
 * Discard superseded requests and clear old rosters before checking current access.
 * `reload` starts from an empty, loading state (for Retry and explicit refresh buttons).
 * `refresh` keeps the current data mounted while it loads, so a change does not lose
 * notices, focus or open panels. A failed refresh still hides the data, because the
 * failure may mean access was removed.
 */
export function useTeamsResource<T>(loader: () => Promise<T>) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [loading, setLoading] = useState(true);
  const generation = useRef(0);
  const load = useCallback(
    async (background: boolean) => {
      const request = ++generation.current;
      if (!background) {
        setData(null);
        setError(null);
        setLoading(true);
      }
      try {
        const value = await loader();
        if (request === generation.current) {
          setData(value);
          setError(null);
        }
      } catch (caught) {
        if (request === generation.current) {
          setData(null);
          setError(asApiError(caught));
        }
      } finally {
        if (request === generation.current) setLoading(false);
      }
    },
    [loader],
  );
  const reload = useCallback(() => load(false), [load]);
  const refresh = useCallback(() => load(true), [load]);
  useEffect(() => {
    // Request generation invalidates responses from unmounted identities and teams.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void reload();
    return () => {
      generation.current += 1;
    };
  }, [reload]);
  return { data, error, loading, reload, refresh };
}

/** Keep request state outside forms so reloading a roster cannot lose an error. */
export function useTeamAction() {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const pending = useRef(false);
  const run = async (
    action: () => Promise<unknown>,
    message: string,
    refresh: () => Promise<void>,
  ) => {
    if (pending.current) return;
    pending.current = true;
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      await action();
      setNotice(message);
      await refresh();
    } catch (caught) {
      setError(describeError(asApiError(caught)));
      // Access can be revoked while a form is open. Refresh rather than retain authority.
      await refresh();
    } finally {
      pending.current = false;
      setBusy(false);
    }
  };
  return { busy, error, notice, run };
}
