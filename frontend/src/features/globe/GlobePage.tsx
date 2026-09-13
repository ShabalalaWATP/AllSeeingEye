/** Full-canvas globe with on-demand layer and measurement tools. */
import { useCallback, useMemo } from 'react';
import { useSavedMapArea } from './useSavedMapArea';
import { SavedMapAreaNotice } from './SavedMapAreaNotice';
import { useInfrastructure } from './infrastructure/useInfrastructure';
import { useInfrastructureSelection } from './infrastructure/useInfrastructureSelection';
import { useConflictRegions } from './useConflictRegions';
import { useConflictRegionSelection } from './useConflictRegionSelection';
import { GlobeInspectors } from './GlobeInspectors';

import { MapCanvas } from './MapCanvas';
import { MaritimeAttribution } from './MaritimeAttribution';
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
import { dashboardCataloguePanels } from './dashboardCataloguePanels';
import { useContextSelection } from './context/useContextSelection';
import { eventControlPanels } from './eventControlPanels';
import { useDashboardFocus } from './useDashboardFocus';
import { useGlobePreferences } from './useGlobePreferences';

import { MapStatusReadouts } from './MapStatusReadouts';
import { useBritishGrid } from './useBritishGrid';
import { GlobeControls } from './GlobeControls';
import { DashboardLayerRail } from './DashboardLayerRail';
import { useNewsSelectionGuard } from './useNewsSelectionGuard';
import { MapNavigationTools } from './MapNavigationTools';
import { ModeToolbar } from './ModeToolbar';
import { useMapWorkspaceTools } from './useMapWorkspaceTools';
import { mapPlanningPanels } from './MapPlanningPanels';
import { mapReferencePanels } from './MapReferencePanels';
import './dashboard.css';
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

export { FOCUS_ZOOM } from './useMapFocus';
import { useMapFocus } from './useMapFocus';
export default function GlobePage() {
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
  const regions = useConflictRegions(supported && !hidden.includes('conflict'), country);
  const { cyber, news } = useReportingReferences(data, countryByIso, visible, now);
  const nation = country === null ? null : (countryByIso[country] ?? null);

  const cameras = useCameras();
  const figures = useFigures(country);
  const infrastructure = useInfrastructure();
  const context = useContextSelection(country, tools.picking, symbolMode);
  useNewsSelectionGuard(context, data, now);
  useEyeMapContext(engine, supported, selected ?? context.event, cameras, infrastructure);
  const closeContext = context.close;
  const closeCamera = cameras.close;
  const closeFigure = figures.close;
  const closeInfrastructure = infrastructure.close;
  const closeRegion = regions.close;
  const closeCyber = cyber.close;
  const closeNews = news.close;
  const closeCatalogues = useCallback(() => {
    closeCamera();
    closeFigure();
    closeInfrastructure();
    closeRegion();
    closeContext();
    closeCyber();
    closeNews();
  }, [
    closeCamera,
    closeFigure,
    closeInfrastructure,
    closeRegion,
    closeContext,
    closeCyber,
    closeNews,
  ]);
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

  return (
    <div className="globe-dashboard absolute inset-0 bg-ground">
      <MapCanvas containerRef={containerRef} supported={supported} mode={mode} engine={engine} />
      {!opsRoom && <ModeToolbar mode={mode} onChange={setMode} />}
      {!opsRoom && <SavedMapAreaNotice area={savedArea} />}
      <MaritimeAttribution events={quality.filtered} hidden={hidden.includes('maritime')} />
      {!opsRoom && (
        <GlobeControls
          onActiveChange={tools.activatePanel}
          layers={(openPanel, activePanel) => (
            <DashboardLayerRail
              data={data}
              cyberCount={cyber.events.length}
              openPanel={openPanel}
              activePanel={activePanel}
              onTrafficSelect={selectTraffic}
              selectionDisabled={tools.picking}
            />
          )}
          navigation={<MapNavigationTools engine={engine} enabled={supported} />}
        >
          {dashboardCataloguePanels({
            data,
            infrastructure,
            focusInfrastructure,
            onContextSelect: selectContext,
            onSatelliteSelect: selectSatellite,
            onTrafficSelect: selectTraffic,
            picking: tools.picking,
            engine,
            onJam,
            conflictOverview: { regions, onSelect: regionSelection.focus },
            cyber: { cyber, onSelect: cyberSelection.selectRecord, picking: tools.picking },
            gnss: {
              enabled: interference,
              data: gnss,
              filters: gnssFilters,
              selected: details?.kind === 'jam' ? details.cell : null,
            },
          })}
          {mapReferencePanels({
            display: {
              terminator,
              lite,
              onToggleTerminator: toggleTerminator,
              onToggleLite: toggleLite,
            },
            base: {
              initialExpanded: true,
              value: baseLayer,
              osAvailable: osMaps,
              osChecking: osLoading,
              osError,
              onCheckOs: recheckOs,
              onChange: setBaseLayer,
            },
            nation: { countries, value: country, onChange: changeNation, error: countriesError },
            country: nation
              ? { country: nation, events: quality.filtered, selectedId, now, onSelect: focus }
              : null,
            precision: {
              events: quality.visible,
              hidden: [],
              filter: quality.filter,
              onFilterChange: quality.setFilter,
              onSelect: focus,
            },
            grid: { grid: britishGrid, engine },
            cameras: { cameras, onSelect: focusCamera },
            figures: { figures, onSelect: focusFigure },
          })}
          {mapPlanningPanels(tools)}
          {eventControlPanels(data, selectContext)}
        </GlobeControls>
      )}
      <MapStatusReadouts
        tools={tools}
        engine={engine}
        supported={supported}
        opsRoom={opsRoom}
        bng={britishGrid.enabled}
      />
      {!opsRoom && !tools.picking && (
        <GlobeInspectors
          news={{ state: news, onSelect: selectContext }}
          cyber={{ state: cyber, onSelect: cyberSelection.selectRecord }}
          regions={regions}
          infrastructure={infrastructure}
          cameras={cameras}
          figures={figures}
          eventDetails={{
            selected: selected ?? context.event,
            storySize,
            details,
            events: pickableEvents,
            cells: gnssFilters.filtered,
            updatedAt: gnss.updated_at,
            interference,
            onSelect: choose,
            onClose: close,
          }}
        />
      )}
    </div>
  );
}
