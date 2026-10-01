/** Catalogue map layers, their selection actions and the fixed order they are drawn in. */
import type { Layer } from '@deck.gl/core';
import type { Country } from '@/lib/api/geoSchemas';
import type { ViewMode } from '@/stores/globe';
import { useCameraSelection } from './cameras/useCameraSelection';
import { useFigureSelection } from './figures/useFigureSelection';
import { useInfrastructureSelection } from './infrastructure/useInfrastructureSelection';
import type { GlobeEngineHandle } from './useGlobeEngine';
import type { GlobeEvents } from './useGlobeEvents';
import type { GlobeSelection } from './useGlobeSelection';
import type { GlobeSources } from './useGlobeSources';
import { useConflictRegionSelection } from './useConflictRegionSelection';
import { useCyberMapSelection } from './useCyberMapSelection';
import { useGlobeLayerGroups } from './useGlobeLayerGroups';
import { useNetworkMapSelection } from './useNetworkMap';
import { useNewsCountryLayers } from './useNewsCountryLayers';
import { useRadarAttackLayers } from './useRadarAttackMap';

interface CatalogueScope {
  data: GlobeEvents;
  sources: GlobeSources;
  selection: Pick<GlobeSelection, 'close' | 'selectContext'>;
  engine: GlobeEngineHandle;
  picking: boolean;
  symbolMode: ViewMode;
  countryByIso: Record<string, Country>;
  gridLayers: readonly Layer[];
  toolLayers: readonly Layer[];
  now: number;
}

/** Each catalogue owns its layers; selecting one closes event inspection first. */
export function useGlobeCatalogueLayers({
  data,
  sources,
  selection: { close, selectContext },
  engine,
  picking,
  symbolMode,
  countryByIso,
  gridLayers,
  toolLayers,
  now,
}: CatalogueScope) {
  const { network, radar, regions, cyber, news, cameras, figures, infrastructure, context } =
    sources;
  const { hidden } = data;
  const newsLayers = useNewsCountryLayers(news, context.event, engine, close, picking, symbolMode);
  const cyberSelection = useCyberMapSelection({
    cyber,
    enabled: !hidden.includes('cyber'),
    picking,
    closeOthers: close,
    engine,
    mode: symbolMode,
    context,
    countries: countryByIso,
    quality: data.quality.filter,
    windowHours: data.windowHours,
    now,
    networkOpen: network.open,
  });
  const networkSelection = useNetworkMapSelection({
    network,
    contextEvent: context.event,
    selectContext,
    picking,
    closeOthers: close,
    engine,
    mode: symbolMode,
    countries: countryByIso,
  });
  const radarLayers = useRadarAttackLayers({
    radar,
    engine,
    closeOthers: close,
    picking,
    mode: symbolMode,
  });
  const regionSelection = useConflictRegionSelection(
    regions,
    !hidden.includes('conflict'),
    picking,
    close,
    engine,
    symbolMode,
  );
  const { focusCamera, cameraLayers } = useCameraSelection(
    cameras,
    picking,
    close,
    engine,
    symbolMode,
  );
  const { focusFigure, figureLayers } = useFigureSelection(
    figures,
    picking,
    close,
    engine,
    symbolMode,
  );
  const { focus: focusInfrastructure, layers: infrastructureLayers } = useInfrastructureSelection(
    infrastructure,
    picking,
    close,
    engine,
    symbolMode,
  );
  const layerGroups = useGlobeLayerGroups({
    grid: gridLayers,
    infrastructure: infrastructureLayers,
    regions: regionSelection.layers,
    cameras: cameraLayers,
    figures: figureLayers,
    context: context.layers,
    cyber: cyberSelection.layers,
    radar: radarLayers,
    network: networkSelection.layers,
    news: newsLayers,
    tools: toolLayers,
  });
  return {
    layerGroups,
    cyberSelection,
    networkSelection,
    regionSelection,
    focusCamera,
    focusFigure,
    focusInfrastructure,
  };
}

export type GlobeCatalogueLayers = ReturnType<typeof useGlobeCatalogueLayers>;
