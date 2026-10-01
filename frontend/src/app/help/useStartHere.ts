import { useCallback, useSyncExternalStore } from 'react';

import {
  dismissStartHere,
  isStartHereDismissed,
  reopenStartHere,
  subscribeStartHere,
} from '@/lib/startHere';
import { useAuthStore } from '@/stores/auth';

/** Whether the signed-in account sees the Start here card; only its own choice is read. */
export function useStartHere() {
  const accountId = useAuthStore((state) => state.user?.id ?? null);
  const dismissed = useSyncExternalStore(
    subscribeStartHere,
    () => accountId === null || isStartHereDismissed(accountId),
    () => true,
  );
  const dismiss = useCallback(() => {
    if (accountId !== null) dismissStartHere(accountId);
  }, [accountId]);
  const reopen = useCallback(() => {
    if (accountId !== null) reopenStartHere(accountId);
  }, [accountId]);
  return { visible: !dismissed, dismiss, reopen };
}
