/** The live event subscription and the single event scope every view on the page reads. */
import { useDashboardEvents } from './useDashboardEvents';
import { useLiveEvents } from './useLiveEvents';

export function useGlobeEvents(now: number) {
  // One stream for the mounted page; it pauses while hidden and reconnects when shown.
  useLiveEvents();
  return useDashboardEvents(now);
}

export type GlobeEvents = ReturnType<typeof useGlobeEvents>;
