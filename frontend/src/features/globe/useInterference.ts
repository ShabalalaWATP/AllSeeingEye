import { useCallback, useEffect, useState } from 'react';
import { fetchJamMap, type JamMap } from '@/lib/api/aviation';
import { describeError } from '@/lib/api/errors';

/** One cancellable request at a time, only while this independent layer is enabled. */
export function useInterference(enabled: boolean) {
  const [snapshot, setSnapshot] = useState<{ map: JamMap; receivedAt: number | null }>({
    map: { cells: [], updated_at: null },
    receivedAt: null,
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [revision, setRevision] = useState(0);
  const refresh = useCallback(() => setRevision((value) => value + 1), []);
  useEffect(() => {
    if (!enabled) return;
    const controller = new AbortController();
    // The signal can change while fetch is awaiting, despite TypeScript's narrowing.
    const cancelled = () => controller.signal.aborted;
    let pending = false;
    const load = async () => {
      if (pending || cancelled()) return;
      pending = true;
      setLoading(true);
      setError(null);
      try {
        const value = await fetchJamMap(controller.signal);
        if (!cancelled()) setSnapshot({ map: value, receivedAt: Date.now() });
      } catch (caught) {
        if (!cancelled()) setError(describeError(caught));
      } finally {
        pending = false;
        if (!cancelled()) setLoading(false);
      }
    };
    void load();
    const timer = window.setInterval(() => void load(), 5 * 60_000);
    return () => {
      controller.abort();
      window.clearInterval(timer);
    };
  }, [enabled, revision]);
  return {
    ...snapshot.map,
    receivedAt: snapshot.receivedAt,
    loading: enabled && loading,
    error,
    refresh,
  };
}
