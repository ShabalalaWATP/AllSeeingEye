import { useCallback, useEffect } from 'react';
import type { LiveEvent } from '@/lib/api/eventSchemas';
import { subscribeWorkspaceAccess } from '@/lib/workspaceAccess';
import { useAuthStore } from '@/stores/auth';
import { useEventsStore } from '@/stores/events';

/** Validate picks against all visible records, including the separate news snapshot. */
export function useDashboardSelection(events: readonly LiveEvent[]) {
  const requestedId = useEventsStore((state) => state.selectedId);
  const storeSelect = useEventsStore((state) => state.select);
  const select = useCallback((id: string | null) => storeSelect(id, 'view'), [storeSelect]);
  const selected = events.find((event) => event.id === requestedId) ?? null;
  useEffect(() => {
    if (requestedId && !selected && useEventsStore.getState().selectedId === requestedId)
      select(null);
  }, [requestedId, selected, select]);
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
