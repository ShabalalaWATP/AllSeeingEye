import { useCallback, useRef } from 'react';

import { currentScopeKey, useAbortableScopedResource } from './useScopedResource';
import { useVisiblePolling } from './useVisiblePolling';
import type { PollOutcome } from './useVisiblePolling';

/**
 * A scoped resource that refreshes in the background while the page is visible. Refreshes
 * keep the last good data on screen, failures back off, nothing is requested while the tab
 * is hidden, and an identity or access change reloads through the scoped resource alone.
 *
 * The loader receives an abort signal and must forward it to its request. The request in
 * flight is aborted on unmount, when the tab is hidden, on an identity or access change
 * and before any newer load; an aborted request never updates state, never shows as an
 * error and never counts as a failure for back-off.
 */
export function usePolledResource<T>(
  loader: (signal: AbortSignal) => Promise<T>,
  intervalMs: number,
) {
  const failed = useRef(false);
  const tracked = useCallback(
    async (signal: AbortSignal) => {
      try {
        const data = await loader(signal);
        failed.current = false;
        return data;
      } catch (error) {
        if (!signal.aborted) failed.current = true;
        throw error;
      }
    },
    [loader],
  );
  const resource = useAbortableScopedResource(tracked);
  const { key, refreshWithSignal } = resource;
  const poll = useCallback(
    async (signal: AbortSignal): Promise<PollOutcome> => {
      // The scoped resource is already reloading for the new identity or access revision.
      if (currentScopeKey() !== key) return 'skipped';
      await refreshWithSignal(signal);
      if (signal.aborted) return 'skipped';
      return failed.current ? 'failed' : 'ok';
    },
    [key, refreshWithSignal],
  );
  useVisiblePolling({ enabled: true, intervalMs, poll });
  return resource;
}
