import { useEffect, useRef } from 'react';
import { useAuthStore } from '@/stores/auth';

function identity() {
  const user = useAuthStore.getState().user;
  return `${user?.id ?? ''}:${user?.role ?? ''}:${user?.is_active ?? false}`;
}

/** Stop private mutations before a delayed 401 can refresh and retry as another account. */
export function useAccountRequest() {
  const pending = useRef<AbortController | null>(null);
  const mounted = useRef(false);
  const actor = identity();
  useEffect(() => {
    mounted.current = true;
    // The subscription runs synchronously on identity changes, before React cleanup.
    const unsubscribe = useAuthStore.subscribe(() => {
      if (identity() !== actor) pending.current?.abort();
    });
    return () => {
      mounted.current = false;
      pending.current?.abort();
      unsubscribe();
    };
  }, [actor]);
  return () => {
    pending.current?.abort();
    const controller = new AbortController();
    pending.current = controller;
    if (!mounted.current || identity() !== actor) controller.abort();
    return controller.signal;
  };
}
