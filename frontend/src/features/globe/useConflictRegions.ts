import { useCallback, useEffect, useMemo, useState, useSyncExternalStore } from 'react';
import { fetchConflictBoard, type ConflictCard } from '@/lib/api/trackers';
import { useScopedRequest } from '@/lib/hooks/useScopedRequest';
import { useAuthStore } from '@/stores/auth';
import { subscribeWorkspaceAccess, workspaceRevision } from '@/lib/workspaceAccess';
import {
  conflictRegions,
  filterConflictRegions,
  type RegionStatus,
  type ConflictRegion,
} from './conflictRegions';

/** One explicit snapshot when the category is enabled; no new feed or polling loop. */
export function useConflictRegions(enabled: boolean, country: string | null) {
  const auth = useAuthStore(
    (state) => `${state.status}:${state.user?.id}:${state.user?.role}:${state.user?.is_active}`,
  );
  const revision = useSyncExternalStore(subscribeWorkspaceAccess, workspaceRevision);
  const scope = `${auth}:${revision}`;
  const request = useScopedRequest();
  const [snapshot, setSnapshot] = useState<{
    scope: string;
    cards: ConflictCard[];
    at: string;
    error: boolean;
  } | null>(null);
  const [refresh, setRefresh] = useState(0);
  const [showRegions, setShowRegions] = useState(true);
  const [status, setStatus] = useState<RegionStatus>('all');
  const [query, setQuery] = useState('');
  const [selection, setSelection] = useState<{ scope: string; id: string } | null>(null);
  const selectionScope = JSON.stringify([scope, enabled, showRegions, country, status, query]);
  // Clear as filters change, so restoring an earlier filter cannot revive an old highlight.
  if (selection && selection.scope !== selectionScope) setSelection(null);
  useEffect(() => {
    if (!enabled || !auth.startsWith('authenticated:')) return;
    const signal = request();
    void fetchConflictBoard(signal)
      .then((cards) => {
        if (!signal.aborted)
          setSnapshot({ scope, cards, at: new Date().toISOString(), error: false });
      })
      .catch(() => {
        if (!signal.aborted)
          setSnapshot({ scope, cards: [], at: new Date().toISOString(), error: true });
      });
    return () => {
      request();
    };
  }, [enabled, auth, scope, request, refresh]);
  const current = snapshot?.scope === scope ? snapshot : null;
  const regions = useMemo(() => conflictRegions(current?.cards ?? []), [current]);
  const filtered = useMemo(
    () => filterConflictRegions(regions, query, status, country),
    [regions, query, status, country],
  );
  const selected =
    enabled && showRegions && selection?.scope === selectionScope
      ? (filtered.find((item) => item.card.conflict.id === selection.id) ?? null)
      : null;
  const close = useCallback(() => setSelection(null), []);
  return {
    enabled,
    filtered,
    selected,
    close,
    status,
    setStatus,
    query,
    setQuery,
    showRegions,
    setShowRegions: (show: boolean) => {
      setShowRegions(show);
      close();
    },
    select: useCallback(
      (region: ConflictRegion) =>
        setSelection({ scope: selectionScope, id: region.card.conflict.id }),
      [selectionScope],
    ),
    loading: enabled && !current,
    error: current?.error ?? false,
    fetchedAt: current?.at ?? null,
    retry: () => {
      setSnapshot(null);
      setRefresh((value) => value + 1);
    },
  };
}
