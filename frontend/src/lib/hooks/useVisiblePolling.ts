import { useCallback, useEffect, useRef } from 'react';

import { subscribeWorkspaceAccess } from '@/lib/workspaceAccess';

/**
 * `ok` resets back-off, `failed` doubles the delay, `skipped` keeps the current
 * delay and `stop` ends polling until the hook is re-enabled.
 */
export type PollOutcome = 'ok' | 'failed' | 'skipped' | 'stop';

export const MAX_POLL_INTERVAL = 300_000;

interface VisiblePollingOptions {
  enabled: boolean;
  intervalMs: number;
  maxIntervalMs?: number;
  poll: (signal: AbortSignal) => Promise<PollOutcome>;
}

const pageHidden = () => document.visibilityState === 'hidden';

/**
 * Bounded background refresh: runs only while the page is not hidden, never overlaps
 * requests, backs off after failures and aborts in-flight work on unmount. An access
 * change triggers an immediate check so stale authority is not kept for a full interval.
 */
export function useVisiblePolling({
  enabled,
  intervalMs,
  maxIntervalMs = MAX_POLL_INTERVAL,
  poll,
}: VisiblePollingOptions) {
  const pollRef = useRef(poll);
  const loadedAt = useRef(0);
  useEffect(() => {
    pollRef.current = poll;
  }, [poll]);

  /** Record a load attempt made outside the poller, such as the first load or a manual retry. */
  const markLoaded = useCallback(() => {
    loadedAt.current = Date.now();
  }, []);

  useEffect(() => {
    if (!enabled) return;
    let stopped = false;
    let failures = 0;
    let timer: ReturnType<typeof setTimeout> | undefined;
    let controller: AbortController | null = null;
    if (loadedAt.current === 0) loadedAt.current = Date.now();

    const delay = () => Math.min(intervalMs * 2 ** failures, maxIntervalMs);
    const schedule = (ms: number) => {
      clearTimeout(timer);
      if (!stopped && !pageHidden()) timer = setTimeout(() => void tick(), ms);
    };
    const tick = async () => {
      if (stopped || pageHidden() || controller !== null) return;
      const current = new AbortController();
      controller = current;
      let outcome: PollOutcome;
      try {
        outcome = await pollRef.current(current.signal);
      } catch {
        outcome = 'failed';
      }
      if (controller === current) controller = null;
      // Cleanup or an access change may have run while the request was in flight.
      // eslint-disable-next-line @typescript-eslint/no-unnecessary-condition
      if (stopped || current.signal.aborted) return;
      if (outcome === 'stop') {
        stopped = true;
        return;
      }
      if (outcome === 'ok') {
        failures = 0;
        loadedAt.current = Date.now();
      } else if (outcome === 'failed') {
        failures += 1;
      }
      schedule(delay());
    };
    // Refresh at once when the last load is already older than the current delay.
    const resume = () => {
      const wait = delay() - (Date.now() - loadedAt.current);
      if (wait <= 0) void tick();
      else schedule(wait);
    };
    const onVisibility = () => {
      clearTimeout(timer);
      if (pageHidden() || controller !== null) return;
      resume();
    };
    const onAccessChange = () => {
      clearTimeout(timer);
      controller?.abort();
      controller = null;
      failures = 0;
      void tick();
    };

    document.addEventListener('visibilitychange', onVisibility);
    const unsubscribe = subscribeWorkspaceAccess(onAccessChange);
    resume();
    return () => {
      stopped = true;
      clearTimeout(timer);
      controller?.abort();
      document.removeEventListener('visibilitychange', onVisibility);
      unsubscribe();
    };
  }, [enabled, intervalMs, maxIntervalMs]);

  return { markLoaded };
}
