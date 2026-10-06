import { useCallback, useEffect } from 'react';
import type { LiveEvent } from '@/lib/api/eventSchemas';
import { subscribeWorkspaceAccess } from '@/lib/workspaceAccess';
import { useAuthStore } from '@/stores/auth';
import { useEventsStore } from '@/stores/events';

/**
 * Validate picks against all visible records, including the separate news snapshot.
 * `shown` is the mirror list these records derive from. While it lags the store, a stream
 * transition is pending, so a just-arrived selection is kept until that view commits.
 */
export function useDashboardSelection(
  events: readonly LiveEvent[],
  shown: readonly LiveEvent[] = useEventsStore.getState().list,
) {
  const requestedId = useEventsStore((state) => state.selectedId);
  const storeSelect = useEventsStore((state) => state.select);
  const select = useCallback((id: string | null) => storeSelect(id, 'view'), [storeSelect]);
  const selected =
    requestedId === null ? null : (events.find((event) => event.id === requestedId) ?? null);
  useEffect(() => {
    const current = useEventsStore.getState();
    if (requestedId && !selected && current.selectedId === requestedId && current.list === shown)
      select(null);
  }, [requestedId, selected, select, shown]);
  useEffect(() => {
    const clear = () => {
      if (useEventsStore.getState().selectionOwner === 'view') storeSelect(null);
    };
    const offAccess = subscribeWorkspaceAccess(clear);
    const offAuth = useAuthStore.subscribe((next, previous) => {
      if (
        next.status !== previous.status ||
        next.user?.id !== previous.user?.id ||
        next.user?.role !== previous.user?.role ||
        next.user?.is_active !== previous.user?.is_active
      )
        clear();
    });
    return () => {
      offAccess();
      offAuth();
      clear();
    };
  }, [storeSelect]);
  return { selected, select };
}
