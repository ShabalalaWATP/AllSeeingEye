import { useCallback, useEffect, useRef } from 'react';
import { useAuthStore } from '@/stores/auth';
import { subscribeWorkspaceAccess, workspaceRevision } from '@/lib/workspaceAccess';

function authority() {
  const state = useAuthStore.getState();
  return `${state.status}:${state.user?.id}:${state.user?.role}:${state.user?.is_active}:${workspaceRevision()}`;
}

/** Abort before the API client can retry a private request with another identity's token. */
export function useMapRequest() {
  const key = authority();
  const pending = useRef<AbortController | null>(null);
  useEffect(() => {
    const abort = () => {
      if (authority() !== key) pending.current?.abort();
    };
    const offAuth = useAuthStore.subscribe(abort);
    const offAccess = subscribeWorkspaceAccess(abort);
    return () => {
      pending.current?.abort();
      offAuth();
      offAccess();
    };
  }, [key]);
  return useCallback(() => {
    pending.current?.abort();
    const controller = new AbortController();
    pending.current = controller;
    if (authority() !== key) controller.abort();
    return controller.signal;
  }, [key]);
}
