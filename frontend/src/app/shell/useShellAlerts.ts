import { useEffect } from 'react';

import { fetchAlerts } from '@/lib/api/warning';
import { useScopedResource } from '@/lib/hooks/useScopedResource';

const loadAlerts = () => fetchAlerts(24);
const POLL_MS = 60_000;

/** Poll within the current identity/access revision; stale alerts never survive revocation. */
export function useShellAlerts() {
  const { data, reload } = useScopedResource(loadAlerts);
  useEffect(() => {
    const timer = window.setInterval(() => void reload(), POLL_MS);
    return () => window.clearInterval(timer);
  }, [reload]);
  return data;
}
