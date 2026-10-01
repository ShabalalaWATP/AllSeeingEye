/** Catalogue and reference sources shown beside live events, and one way to close them all. */
import type { Country } from '@/lib/api/geoSchemas';
import type { ViewMode } from '@/stores/globe';
import { useCameras } from './cameras/useCameras';
import { useContextSelection } from './context/useContextSelection';
import { useFigures } from './figures/useFigures';
import { useInfrastructure } from './infrastructure/useInfrastructure';
import type { GlobeEvents } from './useGlobeEvents';
import { useCatalogueCloser } from './useCatalogueCloser';
import { useConflictRegions } from './useConflictRegions';
import { useNetworkMap } from './useNetworkMap';
import { useNewsSelectionGuard } from './useNewsSelectionGuard';
import { useRadarAttackMap } from './useRadarAttackMap';
import { useReportingReferences } from './useReportingReferences';

interface SourceScope {
  data: GlobeEvents;
  countryByIso: Record<string, Country>;
  supported: boolean;
  visible: boolean;
  picking: boolean;
  symbolMode: ViewMode;
  now: number;
}

/** Sources tied to an event category follow its visibility; the rest load on demand. */
export function useGlobeSources({
  data,
  countryByIso,
  supported,
  visible,
  picking,
  symbolMode,
  now,
}: SourceScope) {
  const { hidden, country } = data;
  const network = useNetworkMap(country, countryByIso);
  const radar = useRadarAttackMap(!hidden.includes('cyber'), visible, countryByIso);
  const regions = useConflictRegions(supported && !hidden.includes('conflict'), country);
  const { cyber, news } = useReportingReferences(data, countryByIso, visible, now);
  const cameras = useCameras();
  const figures = useFigures(country);
  const infrastructure = useInfrastructure(countryByIso);
  const context = useContextSelection(country, picking, symbolMode);
  useNewsSelectionGuard(context, data, now);
  const closeCatalogues = useCatalogueCloser({
    radar: radar.close,
    network: network.close,
    cameras: cameras.close,
    figures: figures.close,
    infrastructure: infrastructure.close,
    regions: regions.close,
    context: context.close,
    cyber: cyber.close,
    news: news.close,
  });
  return {
    network,
    radar,
    regions,
    cyber,
    news,
    cameras,
    figures,
    infrastructure,
    context,
    closeCatalogues,
  };
}

export type GlobeSources = ReturnType<typeof useGlobeSources>;
