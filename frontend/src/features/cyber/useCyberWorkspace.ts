import { useCallback, useEffect } from 'react';
import { fetchJamMap } from '@/lib/api/aviation';
import { fetchCyberActors, ensureCyberBriefing, type CyberDays } from '@/lib/api/cyber';
import { fetchCyberBoard } from '@/lib/api/modules';
import { useScopedResource } from '@/lib/hooks/useScopedResource';
import { useBriefing } from '@/lib/hooks/useDailyBriefing';
import { useCyberSnapshot } from './useCyberSnapshot';

const loadJamMap = () => fetchJamMap();

/** One scope owns the snapshot and briefing. Country/search filters never admit extra jobs. */
export function useCyberWorkspace(days: CyberDays) {
  const ensure = useCallback((signal: AbortSignal) => ensureCyberBriefing(days, signal), [days]);
  const snapshot = useCyberSnapshot(days);
  const actors = useScopedResource(fetchCyberActors);
  // The aircraft-derived GNSS map covers roughly the last day, whatever period is chosen.
  const gnss = useScopedResource(loadJamMap);
  // The live board counts fixed 24-hour and 7-day windows, whatever period is chosen.
  const live = useScopedResource(fetchCyberBoard);
  const briefing = useBriefing(ensure);
  const refresh = snapshot.refresh;
  const refreshGnss = gnss.refresh;
  const refreshLive = live.refresh;
  useEffect(() => {
    const timer = setInterval(() => {
      if (document.visibilityState === 'visible') {
        void refresh();
        void refreshGnss();
        void refreshLive();
      }
    }, 300_000);
    return () => clearInterval(timer);
  }, [refresh, refreshGnss, refreshLive]);
  return { snapshot, actors, briefing, gnss, live };
}
export type CyberBriefingState = ReturnType<typeof useCyberWorkspace>['briefing'];
export type CyberGnssState = ReturnType<typeof useCyberWorkspace>['gnss'];
export type CyberLiveState = ReturnType<typeof useCyberWorkspace>['live'];
