import { useCallback, useEffect, useState } from 'react';

import { fetchAuditPage } from '@/lib/api/admin';
import { asApiError } from '@/lib/api/errors';
import type { ApiError } from '@/lib/api/errors';
import type { AuditEntry } from '@/lib/api/schemas';

export interface AuditLog {
  entries: AuditEntry[];
  nextBefore: number | null;
  loading: boolean;
  error: ApiError | null;
  loadMore: () => void;
}

/** Pages through the audit log newest first using the `next_before` cursor. */
export function useAuditLog(): AuditLog {
  const [entries, setEntries] = useState<AuditEntry[]>([]);
  const [nextBefore, setNextBefore] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<ApiError | null>(null);

  // State changes only after the request settles; `loading` starts as true so
  // the first page can be requested from an effect without a synchronous update.
  const fetchPage = useCallback(async (before: number | null) => {
    try {
      const page = await fetchAuditPage(before);
      setEntries((current) => (before === null ? page.items : [...current, ...page.items]));
      setNextBefore(page.next_before);
      setError(null);
    } catch (caught) {
      setError(asApiError(caught));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    // State changes only after the request settles; the lint rule cannot see the
    // await. Phase 1 replaces this with a TanStack Query infinite query.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void fetchPage(null);
  }, [fetchPage]);

  const loadMore = useCallback(() => {
    if (nextBefore === null) return;
    setLoading(true);
    void fetchPage(nextBefore);
  }, [fetchPage, nextBefore]);

  return { entries, nextBefore, loading, error, loadMore };
}
