/** GNSS interference cells and their display filters, polled only while shown and visible. */
import { useGnssFilters } from './useGnssFilters';
import { useInterference } from './useInterference';

export function useGlobeInterference(enabled: boolean, now: number) {
  const gnss = useInterference(enabled);
  const filters = useGnssFilters(gnss.cells, gnss.receivedAt, now);
  return { gnss, filters };
}

export type GlobeInterference = ReturnType<typeof useGlobeInterference>;
