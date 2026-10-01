import { useEffect, useMemo } from 'react';

import { usePageVisible } from '@/components/brand/useMotionPreferences';
import { fetchPlanMapMatches } from '@/lib/api/direction';
import type { LiveEvent } from '@/lib/api/eventSchemas';
import { usePlanMapFilterStore } from '@/stores/planMapFilter';

/** One request per minute at most, only while the page is visible, never two at once. */
export const PLAN_MATCH_REFRESH_MS = 60_000;

/**
 * Keeps the selected plan's match sample current and narrows `events` to it. The sample is
 * intersected with events that already passed every other map filter, so geography, source,
 * category and time filters still apply, and expired events drop out with the live store.
 */
export function usePlanMapFilter(events: LiveEvent[]): LiveEvent[] {
  const planId = usePlanMapFilterStore((state) => state.planId);
  const authority = usePlanMapFilterStore((state) => state.authority);
  const refreshes = usePlanMapFilterStore((state) => state.refreshes);
  const codes = usePlanMapFilterStore((state) => state.codes);
  const visible = usePageVisible();
  useEffect(() => {
    if (planId === null || !visible) return;
    const controller = new AbortController();
    let pending = false;
    const load = async () => {
      if (pending) return;
      pending = true;
      const store = usePlanMapFilterStore.getState();
      store.begin(planId);
      try {
        const result = await fetchPlanMapMatches(planId, controller.signal);
        if (!controller.signal.aborted) store.succeed(planId, result, Date.now());
      } catch (error) {
        if (!controller.signal.aborted) store.fail(planId, error);
      } finally {
        pending = false;
      }
    };
    void load();
    const timer = window.setInterval(() => void load(), PLAN_MATCH_REFRESH_MS);
    return () => {
      controller.abort();
      window.clearInterval(timer);
    };
  }, [planId, authority, refreshes, visible]);
  return useMemo(
    () => (planId === null ? events : events.filter((event) => codes?.has(event.id) === true)),
    [events, planId, codes],
  );
}
