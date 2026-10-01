import { useEffect } from 'react';

import { fetchBell } from '@/lib/api/bell';
import type { BellAlert } from '@/lib/api/bell';
import { subscribeBellChanges } from '@/lib/bellSignal';
import { usePolledResource } from '@/lib/hooks/usePolledResource';

import { SHELL_POLL_MS } from './useNotificationBell';

const loadBell = (signal: AbortSignal) => fetchBell(signal);

/**
 * The bell's alerts for the wall screen: the same seven-day window, scope and mutes as the
 * bell, polled within the current identity and access revision. Stale alerts never survive
 * revocation, and a bell change from the live stream refetches them.
 */
export function useShellAlerts(): { items: BellAlert[]; total: number } {
  const bell = usePolledResource(loadBell, SHELL_POLL_MS);
  const { refresh } = bell;
  useEffect(() => subscribeBellChanges(() => void refresh()), [refresh]);
  const alerts = bell.data?.alerts;
  return alerts === undefined || alerts.muted
    ? { items: [], total: 0 }
    : { items: alerts.items, total: alerts.total };
}
