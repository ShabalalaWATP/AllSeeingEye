/** Orchestrates the live map data, selections and scene outside the page view. */
import { useMemo } from 'react';
import { useSavedMapArea } from './useSavedMapArea';
import { useInfrastructure } from './infrastructure/useInfrastructure';
import { useInfrastructureSelection } from './infrastructure/useInfrastructureSelection';
import { useConflictRegions } from './useConflictRegions';
import { useConflictRegionSelection } from './useConflictRegionSelection';
import { usePageVisible, useReducedMotion } from '@/components/brand/useMotionPreferences';
import { useCameras } from './cameras/useCameras';
import { useCameraSelection } from './cameras/useCameraSelection';
import { useFigures } from './figures/useFigures';
import { useFigureSelection } from './figures/useFigureSelection';
import { useNow } from '@/lib/hooks/useNow';
import { useMapReferenceData } from './useMapReferenceData';
import { useDashboardEvents } from './useDashboardEvents';
import { useReportingReferences } from './useReportingReferences';
import { useNewsCountryLayers } from './useNewsCountryLayers';
import { useCyberMapSelection } from './useCyberMapSelection';
import { useContextSelection } from './context/useContextSelection';
import { useTechnologyControl } from './useTechnologyControl';
import { useNetworkMap, useNetworkMapSelection } from './useNetworkMap';
import { useRadarAttackMap, useRadarAttackLayers } from './useRadarAttackMap';
import { useDashboardFocus } from './useDashboardFocus';
import { useGlobePreferences } from './useGlobePreferences';
import { useBritishGrid } from './useBritishGrid';
import { useNewsSelectionGuard } from './useNewsSelectionGuard';
import { useMapWorkspaceTools } from './useMapWorkspaceTools';
import { useInterference } from './useInterference';
import { useGnssFilters } from './useGnssFilters';
import { useGlobeScene } from './useGlobeScene';
import { useMapPicking } from './useMapPicking';
import { useTrafficSelection } from './useTrafficSelection';
import { useMapRenderView } from './useMapRenderView';
import { useDashboardEngine } from './useDashboardEngine';
import { useViewportCoverage } from './useViewportCoverage';
import { useLiveEvents } from './useLiveEvents';
import { useEyeMapContext } from './useEyeMapContext';
import { useAssistantMapSelection } from './useAssistantMapSelection';
import { useMapFocus } from './useMapFocus';
import { useCatalogueCloser } from './useCatalogueCloser';

export function useGlobePage() {
  const {
    mode,
    setMode,
    baseLayer,
    setBaseLayer,
    terminator,
    toggleTerminator,
    lite,
    toggleLite,
    interference,
    opsRoom,
  } = useGlobePreferences();
  const reducedMotion = useReducedMotion();
  const visible = usePageVisible();
  const gnss = useInterference(interference && visible);
  const { supported, containerRef, engine } = useDashboardEngine({ mode, baseLayer, lite });
  const britishGrid = useBritishGrid(engine);
  useLiveEvents();
  useViewportCoverage(engine, supported && visible);
  const tools = useMapWorkspaceTools(engine, supported && !opsRoom, mode);
  const now = useNow();
  const gnssFilters = useGnssFilters(gnss.cells, gnss.receivedAt, now);
  const { zoom, symbolMode } = useMapRenderView(engine, mode);
  const { osMaps, osLoading, osError, recheckOs, countries, countryByIso, countriesError } =
    useMapReferenceData(baseLayer, setBaseLayer);
  const savedArea = useSavedMapArea(engine, countryByIso, mode === 'map');
  const toolLayers = useMemo(
    () => [...tools.layers, ...savedArea.layers],
    [tools.layers, savedArea.layers],
  );

  const data = useDashboardEvents(now);
  const {
    hidden,
    country,
    selectedId,
    selected,
    select,
    setCountry,
    toggleCategory,
    observations,
    quality,
    storySize,
  } = data;
  const network = useNetworkMap(country, countryByIso);
  const radar = useRadarAttackMap(!hidden.includes('cyber'), visible, countryByIso);
  const regions = useConflictRegions(supported && !hidden.includes('conflict'), country);
  const { cyber, news } = useReportingReferences(data, countryByIso, visible, now);
  const nation = country === null ? null : (countryByIso[country] ?? null);

  const cameras = useCameras();
  const figures = useFigures(country);
  const infrastructure = useInfrastructure(countryByIso);
  const context = useContextSelection(country, tools.picking, symbolMode);
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
    quality.filtered,
    data.renderHidden,
    tools.picking,
    select,
    engine,
    closeCatalogues,
  );
  const newsLayers = useNewsCountryLayers(
    news,
    context.event,
    engine,
    close,
    tools.picking,
    symbolMode,
  );
  const cyberSelection = useCyberMapSelection({
    cyber,
    enabled: !hidden.includes('cyber'),
    picking: tools.picking,
    closeOthers: close,
    engine,
    mode: symbolMode,
    context,
    countries: countryByIso,
    quality: quality.filter,
    windowHours: data.windowHours,
    now,
    networkOpen: network.open,
  });
  const { selectContext, selectSatellite } = useDashboardFocus({
    engine,
    picking: tools.picking,
    hidden,
    toggleCategory,
    choose,
    close,
    chooseContext: context.choose,
  });
  const networkSelection = useNetworkMapSelection({
    network,
    contextEvent: context.event,
    selectContext,
    picking: tools.picking,
    closeOthers: close,
    engine,
    mode: symbolMode,
    countries: countryByIso,
  });
  const radarAttackLayers = useRadarAttackLayers({
    radar,
    engine,
    closeOthers: close,
    picking: tools.picking,
    mode: symbolMode,
  });
  const regionSelection = useConflictRegionSelection(
    regions,
    !hidden.includes('conflict'),
    tools.picking,
    close,
    engine,
    symbolMode,
  );

  const { focusCamera, cameraLayers } = useCameraSelection(
    cameras,
    tools.picking,
    close,
    engine,
    symbolMode,
  );
  const technology = useTechnologyControl(
    network,
    infrastructure,
    country,
    networkSelection.selectRecord,
  );
  const { focusFigure, figureLayers } = useFigureSelection(
    figures,
    tools.picking,
    close,
    engine,
    symbolMode,
  );
  const selectTraffic = useTrafficSelection(
    engine,
    choose,
    observations.visibility,
    observations.toggle,
    hidden,
    toggleCategory,
  );
  const { focus: focusInfrastructure, layers: infrastructureLayers } = useInfrastructureSelection(
    infrastructure,
    tools.picking,
    close,
    engine,
    symbolMode,
  );
  const selectAssistantMapSource = useAssistantMapSelection(
    pickableEvents,
    cameras,
    infrastructure,
    choose,
    focusCamera,
    focusInfrastructure,
  );
  useEyeMapContext(
    engine,
    supported,
    selected ?? context.event,
    cameras,
    infrastructure,
    selectAssistantMapSource,
  );
  useGlobeScene({
    engine,
    events: quality.filtered,
    hidden: data.renderHidden,
    selectedId,
    highlightedId,
    onPick,
    onCluster,
    onJam,
    jamCells: gnssFilters.filtered,
    jamSelection: details?.kind === 'jam' ? details.cell : null,
    gridLayers: britishGrid.layers,
    cameraLayers,
    figureLayers,
    infrastructureLayers,
    conflictRegionLayers: regionSelection.layers,
    contextLayers: context.layers,
    cyberCountryLayers: cyberSelection.layers,
    radarAttackLayers,
    networkCountryLayers: networkSelection.layers,
    newsCountryLayers: newsLayers,
    measured: toolLayers,
    supported,
    terminator,
    lite,
    interference,
    opsRoom,
    reducedMotion,
    visible,
    now,
    zoom,
    mode,
    symbolMode,
  });

  const { focus, changeNation } = useMapFocus(
    engine,
    select,
    closeCatalogues,
    setCountry,
    countryByIso,
  );

  return {
    display: {
      mode,
      setMode,
      baseLayer,
      setBaseLayer,
      terminator,
      toggleTerminator,
      lite,
      toggleLite,
      interference,
      opsRoom,
    },
    canvas: { containerRef, supported, engine, britishGrid, tools, savedArea },
    reference: {
      osMaps,
      osLoading,
      osError,
      recheckOs,
      countries,
      countriesError,
      changeNation,
      nation,
    },
    events: {
      data,
      hidden,
      country,
      selectedId,
      selected,
      quality,
      storySize,
      details,
      pickableEvents,
      choose,
      close,
      onJam,
      focus,
      selectTraffic,
    },
    sources: {
      radar,
      network,
      news,
      cyber,
      regions,
      infrastructure,
      cameras,
      figures,
      context,
      gnss,
      gnssFilters,
    },
    actions: {
      technology,
      selectContext,
      selectSatellite,
      focusInfrastructure,
      focusCamera,
      focusFigure,
      regionSelection,
      cyberSelection,
      networkSelection,
    },
    now,
  };
}
