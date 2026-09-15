import { useEffect, useState } from 'react';

import { asApiError, describeError } from '@/lib/api/errors';
import { fetchSchedules, type Schedule } from '@/lib/api/schedules';

const ACTIVE_DELAY = 5_000;
const IDLE_DELAY = 30_000;
const MAX_BACKOFF = 300_000;

function interval(items: readonly Schedule[]): number {
  return items.some((item) => item.enabled && Date.parse(item.next_run_at) <= Date.now())
    ? ACTIVE_DELAY
    : IDLE_DELAY;
}

/** Refresh list summaries only, retaining the last authorised snapshot on transient failure. */
export function useScheduleRefresh(
  items: Schedule[] | null,
  key: string,
  setItems: (value: Schedule[] | null) => void,
): string | null {
  const [failure, setFailure] = useState<{
    key: string;
    message: string;
    items: Schedule[];
  } | null>(null);
  useEffect(() => {
    if (items === null) return;
    let stopped = false;
    let attempts = 0;
    let current = items;
    let timer: ReturnType<typeof setTimeout> | undefined;
    let controller: AbortController | null = null;
    const schedule = (delay: number) => {
      clearTimeout(timer);
      if (document.visibilityState === 'visible') timer = setTimeout(() => void refresh(), delay);
    };
    const refresh = async () => {
      if (stopped || document.visibilityState !== 'visible') return;
      controller = new AbortController();
      const signal = controller.signal;
      try {
        const next = await fetchSchedules(signal);
        // The effect may have been replaced while the request was in flight.
        // eslint-disable-next-line @typescript-eslint/no-unnecessary-condition
        if (stopped || signal.aborted) return;
        current = next;
        attempts = 0;
        setFailure(null);
        setItems(next);
        schedule(interval(current));
      } catch (error) {
        // eslint-disable-next-line @typescript-eslint/no-unnecessary-condition
        if (stopped || signal.aborted) return;
        const denied = [401, 403].includes(asApiError(error).status);
        if (denied) setItems(null);
        attempts += 1;
        setFailure({ key, message: describeError(error), items: current });
        if (!denied) schedule(Math.min(interval(current) * 2 ** attempts, MAX_BACKOFF));
      } finally {
        if (controller.signal === signal) controller = null;
      }
    };
    const visibility = () => {
      clearTimeout(timer);
      controller?.abort();
      if (document.visibilityState === 'visible') void refresh();
    };
    document.addEventListener('visibilitychange', visibility);
    schedule(interval(current));
    return () => {
      stopped = true;
      clearTimeout(timer);
      controller?.abort();
      document.removeEventListener('visibilitychange', visibility);
    };
  }, [items, key, setItems]);
  return failure?.key === key && (items === null || failure.items === items)
    ? failure.message
    : null;
}
