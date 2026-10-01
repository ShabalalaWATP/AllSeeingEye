/** Event picking, inspection and every route that moves the map to a chosen record. */
import type { Country } from '@/lib/api/geoSchemas';
import type { GlobeEngineHandle } from './useGlobeEngine';
import type { GlobeEvents } from './useGlobeEvents';
import type { GlobeSources } from './useGlobeSources';
import { useDashboardFocus } from './useDashboardFocus';
import { useMapFocus } from './useMapFocus';
import { useMapPicking } from './useMapPicking';
import { useTrafficSelection } from './useTrafficSelection';

interface SelectionScope {
  data: GlobeEvents;
  sources: Pick<GlobeSources, 'context' | 'closeCatalogues'>;
  engine: GlobeEngineHandle;
  picking: boolean;
  countryByIso: Record<string, Country>;
}

/** Picking an event closes catalogue inspectors; a measuring or drawing tool suspends picks. */
export function useGlobeSelection({
  data,
  sources: { context, closeCatalogues },
  engine,
  picking,
  countryByIso,
}: SelectionScope) {
  const { hidden, toggleCategory, select, observations } = data;
  const {
    details,
    highlightedId,
    visible: pickableEvents,
    choose,
    close,
    onPick,
    onCluster,
    onJam,
  } = useMapPicking(
    data.quality.filtered,
    data.renderHidden,
    picking,
    select,
    engine,
    closeCatalogues,
  );
  const { selectContext, selectSatellite } = useDashboardFocus({
    engine,
    picking,
    hidden,
    toggleCategory,
    choose,
    close,
    chooseContext: context.choose,
  });
  const selectTraffic = useTrafficSelection(
    engine,
    choose,
    observations.visibility,
    observations.toggle,
    hidden,
    toggleCategory,
  );
  const { focus, changeNation } = useMapFocus(
    engine,
    select,
    closeCatalogues,
    data.setCountry,
    countryByIso,
  );
  return {
    details,
    highlightedId,
    pickableEvents,
    choose,
    close,
    onPick,
    onCluster,
    onJam,
    selectContext,
    selectSatellite,
    selectTraffic,
    focus,
    changeNation,
  };
}

export type GlobeSelection = ReturnType<typeof useGlobeSelection>;
