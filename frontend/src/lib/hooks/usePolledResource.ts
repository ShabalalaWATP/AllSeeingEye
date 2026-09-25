import { useCallback, useRef } from 'react';

import { currentScopeKey, useScopedResource } from './useScopedResource';
import { useVisiblePolling } from './useVisiblePolling';
import type { PollOutcome } from './useVisiblePolling';

/**
 * A scoped resource that refreshes in the background while the page is visible. Refreshes
 * keep the last good data on screen, failures back off, nothing is requested while the tab
 * is hidden, and an identity or access change reloads through the scoped resource alone.
 */
export function usePolledResource<T>(loader: () => Promise<T>, intervalMs: number) {
  const failed = useRef(false);
  const tracked = useCallback(async () => {
    try {
      const data = await loader();
      failed.current = false;
      return data;
    } catch (error) {
      failed.current = true;
      throw error;
    }
  }, [loader]);
  const resource = useScopedResource(tracked);
  const { key, refresh } = resource;
  const poll = useCallback(async (): Promise<PollOutcome> => {
    // The scoped resource is already reloading for the new identity or access revision.
    if (currentScopeKey() !== key) return 'skipped';
    await refresh();
    return failed.current ? 'failed' : 'ok';
  }, [key, refresh]);
  useVisiblePolling({ enabled: true, intervalMs, poll });
  return resource;
}
