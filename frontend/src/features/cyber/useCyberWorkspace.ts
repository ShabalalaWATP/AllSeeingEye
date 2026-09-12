import { useCallback, useEffect } from 'react';
import { fetchCyberActors, ensureCyberBriefing, type CyberDays } from '@/lib/api/cyber';
import { useScopedResource } from '@/lib/hooks/useScopedResource';
import { useBriefing } from '@/lib/hooks/useDailyBriefing';
import { useCyberSnapshot } from './useCyberSnapshot';

/** One scope owns the snapshot and briefing. Country/search filters never admit extra jobs. */
export function useCyberWorkspace(days: CyberDays) {
  const ensure = useCallback((signal: AbortSignal) => ensureCyberBriefing(days, signal), [days]);
  const snapshot = useCyberSnapshot(days);
  const actors = useScopedResource(fetchCyberActors);
  const briefing = useBriefing(ensure);
  const refresh = snapshot.refresh;
  useEffect(() => {
    const timer = setInterval(() => {
      if (document.visibilityState === 'visible') void refresh();
    }, 300_000);
    return () => clearInterval(timer);
  }, [refresh]);
  return { snapshot, actors, briefing };
}
export type CyberBriefingState = ReturnType<typeof useCyberWorkspace>['briefing'];
