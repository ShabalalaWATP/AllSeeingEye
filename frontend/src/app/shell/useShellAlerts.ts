import { fetchAlerts } from '@/lib/api/warning';
import { usePolledResource } from '@/lib/hooks/usePolledResource';

const loadAlerts = () => fetchAlerts(24);
export const SHELL_POLL_MS = 60_000;

/**
 * The last day's alerts, polled within the current identity and access revision while the
 * page is visible. Stale alerts never survive revocation.
 */
export function useShellAlertsResource() {
  return usePolledResource(loadAlerts, SHELL_POLL_MS);
}

export function useShellAlerts() {
  return useShellAlertsResource().data;
}
