/** Full-canvas globe with on-demand layer and measurement tools. */
import { useCallback, useRef, useState } from 'react';
import { useInfrastructure } from './infrastructure/useInfrastructure';
import { useInfrastructureSelection } from './infrastructure/useInfrastructureSelection';
import { useConflictRegions } from './useConflictRegions';
import { useConflictRegionSelection } from './useConflictRegionSelection';
import { GlobeInspectors } from './GlobeInspectors';

import { MapCanvas } from './MapCanvas';
import { usePageVisible, useReducedMotion } from '@/components/brand/useMotionPreferences';
import { useCameras } from './cameras/useCameras';
import { useCameraSelection } from './cameras/useCameraSelection';
import { useNow } from '@/lib/hooks/useNow';
import { useMapReferenceData } from './useMapReferenceData';
import { useDashboardEvents } from './useDashboardEvents';
import { EventScopeStrip } from './EventScopeStrip';
import { trafficControlPanels } from './trafficControlPanels';
import { useContextSelection } from './context/useContextSelection';
import { eventControlPanels } from './eventControlPanels';
import { useDashboardFocus } from './useDashboardFocus';
import { useGlobePreferences } from './useGlobePreferences';

import { CoordinateReadout } from './CoordinateReadout';
import { useBritishGrid } from './useBritishGrid';
import { GlobeControls } from './GlobeControls';
import { MeasurementReadout } from './MeasurementReadout';
import { RfMapReadout } from './RfMapReadout';
import { MapLayerRail } from './MapLayerRail';
import { MapNavigationTools } from './MapNavigationTools';
import { ModeToolbar } from './ModeToolbar';
import { WorldClocks } from './WorldClocks';
import { useMapWorkspaceTools } from './useMapWorkspaceTools';
import { mapPlanningPanels } from './MapPlanningPanels';
import { mapReferencePanels } from './MapReferencePanels';
import { catalogueControlPanels } from './catalogueControlPanels';
import './dashboard.css';
import { createEngine } from './globeEngineFactory';
import { useInterference } from './useInterference';
import { useGnssFilters } from './useGnssFilters';
import { useGlobeScene } from './useGlobeScene';
import { useMapPicking } from './useMapPicking';
import { useTrafficSelection } from './useTrafficSelection';

import { useMapRenderView } from './useMapRenderView';
import { useGlobeEngine } from './useGlobeEngine';
import { useViewportCoverage } from './useViewportCoverage';
import { useLiveEvents } from './useLiveEvents';
import { hasWebGl2 } from './webgl';

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
  const [supported] = useState(() => hasWebGl2());
  const containerRef = useRef<HTMLDivElement>(null);
  const engine = useGlobeEngine(containerRef, {
    enabled: supported,
    mode,
    baseLayer,
    lite,
    createEngine,
  });
  const britishGrid = useBritishGrid(engine);
  useLiveEvents();
  useViewportCoverage(engine, supported && visible);
  const tools = useMapWorkspaceTools(engine, supported && !opsRoom, mode);
  const { measurement } = tools;
  const now = useNow();
  const gnssFilters = useGnssFilters(gnss.cells, gnss.receivedAt, now);
  const { zoom, symbolMode } = useMapRenderView(engine, mode);
  const { osMaps, osLoading, osError, recheckOs, countries, countryByIso, countriesError } =
    useMapReferenceData(baseLayer, setBaseLayer);

  const data = useDashboardEvents(now);
  const {
    hidden,
    country,
    selectedId,
    selected,
    stats,
    select,
    setCountry,
    toggleCategory,
    scoped,
    counts,
    observations,
    satellites,
    hazards,
    conflicts,
    quality,
    storySize,
  } = data;
  const regions = useConflictRegions(supported && !hidden.includes('conflict'), country);
  const nation = country === null ? null : (countryByIso[country] ?? null);

  const cameras = useCameras();
  const infrastructure = useInfrastructure();
  const context = useContextSelection(country, tools.picking);
  const closeContext = context.close;
  const closeCamera = cameras.close;
  const closeInfrastructure = infrastructure.close;
  const closeRegion = regions.close;
  const closeCatalogues = useCallback(() => {
    closeCamera();
    closeInfrastructure();
    closeRegion();
    closeContext();
  }, [closeCamera, closeInfrastructure, closeRegion, closeContext]);
  const {
    details,
    highlightedId,
    visible: pickableEvents,
    choose,
    close,
    onPick,
    onCluster,
    onJam,
  } = useMapPicking(quality.filtered, hidden, tools.picking, select, engine, closeCatalogues);
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
    hidden,
    selectedId,
    highlightedId,
    onPick,
    onCluster,
    onJam,
    jamCells: gnssFilters.filtered,
    jamSelection: details?.kind === 'jam' ? details.cell : null,
    gridLayers: britishGrid.layers,
    cameraLayers,
    infrastructureLayers,
    conflictRegionLayers: regionSelection.layers,
    contextLayers: context.layers,
    measured: tools.layers,
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
      {!opsRoom && <EventScopeStrip state={data} />}
      <WorldClocks />
      {!opsRoom && (
        <GlobeControls
          onActiveChange={tools.activatePanel}
          layers={(openPanel, activePanel) => (
            <MapLayerRail
              openPanel={openPanel}
              activePanel={activePanel}
              gnssCount={gnssFilters.filtered.length}
              events={scoped}
              counts={counts}
              visibility={observations.visibility}
              onToggle={observations.toggle}
              flightFilter={observations.flightFilter}
              onFlightFilter={observations.setFlightFilter}
              onTrafficSelect={selectTraffic}
              selectionDisabled={tools.picking}
              vesselFilter={observations.vesselFilter}
              onVesselFilter={observations.setVesselFilter}
            />
          )}
          navigation={<MapNavigationTools engine={engine} enabled={supported} />}
        >
          {catalogueControlPanels({
            infrastructure,
            focusInfrastructure,
            satellites,
            country,
            onContextSelect: selectContext,
            onSatelliteSelect: selectSatellite,
            selectedId,
            qualityFilter: quality.filter,
            conflicts,
            conflictOverview: { regions, onSelect: regionSelection.focus },
            hazards,
            gnss: {
              enabled: interference,
              data: gnss,
              filters: gnssFilters,
              selected: details?.kind === 'jam' ? details.cell : null,
              selectionDisabled: tools.picking,
              onSelect: (cell) => {
                if (tools.picking) return;
                onJam(cell);
                engine.flyTo({ center: [cell.lon, cell.lat], zoom: 6 });
              },
            },
          })}
          {trafficControlPanels({
            events: scoped,
            observations,
            onSelect: selectTraffic,
            selectionDisabled: tools.picking,
            country,
            onContextSelect: selectContext,
            qualityFilter: quality.filter,
            available: Object.fromEntries(
              (stats?.per_category ?? []).flatMap((item) =>
                item.category === 'aviation'
                  ? [['aircraft', item.count]]
                  : item.category === 'maritime'
                    ? [['vessels', item.count]]
                    : [],
              ),
            ),
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
          })}
          {mapPlanningPanels(tools)}
          {eventControlPanels(data, selectContext)}
        </GlobeControls>
      )}
      <MeasurementReadout value={measurement} />
      {!opsRoom && !tools.picking && (
        <RfMapReadout analysis={tools.rf.analysis} estimate={tools.rf.estimate} />
      )}
      {supported && !opsRoom && !tools.picking && (
        <CoordinateReadout engine={engine} bng={britishGrid.enabled} />
      )}
      {!opsRoom && !tools.picking && (
        <GlobeInspectors
          regions={regions}
          infrastructure={infrastructure}
          cameras={cameras}
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
