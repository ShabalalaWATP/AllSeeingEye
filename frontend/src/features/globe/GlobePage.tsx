/** Full-canvas globe with on-demand layer and measurement tools. */
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useInfrastructure } from './infrastructure/useInfrastructure';
import { useInfrastructureSelection } from './infrastructure/useInfrastructureSelection';
import { InfrastructureInspector } from './infrastructure/InfrastructureInspector';

import { MapCanvas } from './MapCanvas';
import { usePageVisible, useReducedMotion } from '@/components/brand/useMotionPreferences';
import { useCameras } from './cameras/useCameras';
import { CameraInspector } from './cameras/CameraInspector';
import { useCameraSelection } from './cameras/useCameraSelection';
import { useNow } from '@/lib/hooks/useNow';
import { useMapReferenceData } from './useMapReferenceData';
import {
  countByCategory,
  filterByCountry,
  filterByWindow,
  selectSelectedEvent,
  useEventsStore,
} from '@/stores/events';
import { useGlobeStore } from '@/stores/globe';

import { CoordinateReadout } from './CoordinateReadout';
import { SelectedMapDetails } from './SelectedMapDetails';
import { useBritishGrid } from './useBritishGrid';
import { ControlPanel, GlobeControls } from './GlobeControls';
import { MeasurementReadout } from './MeasurementReadout';
import { MapLayerRail } from './MapLayerRail';
import { MapNavigationTools } from './MapNavigationTools';
import { LayerPanel } from './LayerPanel';
import { ModeToolbar } from './ModeToolbar';
import { WorldClocks } from './WorldClocks';
import { useObservationFilters } from './ObservationControls';
import { useSatelliteFilters } from './useSatelliteFilters';
import { useConflictFilters } from './useConflictFilters';
import { useLocationQuality } from './useLocationQuality';
import { useHazardFilters } from './useHazardFilters';
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

import { clusteringZoomFor } from './layers/clusters';
import { useGlobeEngine } from './useGlobeEngine';
import { useViewportCoverage } from './useViewportCoverage';
import { useLiveEvents } from './useLiveEvents';
import { hasWebGl2 } from './webgl';

export { FOCUS_ZOOM } from './useMapFocus';
import { useMapFocus } from './useMapFocus';

export default function GlobePage() {
  const mode = useGlobeStore((state) => state.mode);
  const setMode = useGlobeStore((state) => state.setMode);
  const baseLayer = useGlobeStore((state) => state.baseLayer);
  const setBaseLayer = useGlobeStore((state) => state.setBaseLayer);
  const terminator = useGlobeStore((state) => state.terminator);
  const toggleTerminator = useGlobeStore((state) => state.toggleTerminator);
  const lite = useGlobeStore((state) => state.lite);
  const toggleLite = useGlobeStore((state) => state.toggleLite);
  const interference = useGlobeStore((state) => state.interference);
  const opsRoom = useGlobeStore((state) => state.opsRoom);
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
  const [zoom, setZoom] = useState(1.5);
  useEffect(
    () =>
      engine.onView((view) => {
        setZoom(clusteringZoomFor(view.zoom));
      }),
    [engine],
  );
  const { osMaps, osLoading, osError, recheckOs, countries, countryByIso, countriesError } =
    useMapReferenceData(baseLayer, setBaseLayer);

  const hidden = useEventsStore((state) => state.hidden);
  const country = useEventsStore((state) => state.country);
  const selectedId = useEventsStore((state) => state.selectedId);
  const selected = useEventsStore(selectSelectedEvent);
  const stats = useEventsStore((state) => state.stats);
  const status = useEventsStore((state) => state.status);
  const error = useEventsStore((state) => state.error);
  const select = useEventsStore((state) => state.select);
  const setCountry = useEventsStore((state) => state.setCountry);
  const toggleCategory = useEventsStore((state) => state.toggleCategory);
  const list = useEventsStore((state) => state.list);
  const windowHours = useEventsStore((state) => state.windowHours);
  const setWindow = useEventsStore((state) => state.setWindow);
  const countryEvents = useMemo(() => filterByCountry(list, country), [list, country]);
  const scoped = useMemo(
    () => filterByWindow(countryEvents, windowHours, now),
    [countryEvents, windowHours, now],
  );
  const counts = useMemo(() => countByCategory(scoped), [scoped]);
  const observations = useObservationFilters(scoped);
  const satellites = useSatelliteFilters(observations.filtered);
  const hazards = useHazardFilters(satellites.filtered);
  const conflicts = useConflictFilters(hazards.filtered);
  const quality = useLocationQuality(conflicts.filtered, hidden);
  const nation = country === null ? null : (countryByIso[country] ?? null);
  const storySize = useMemo(
    () =>
      selected?.story_id == null
        ? 1
        : list.filter((event) => event.story_id === selected.story_id).length,
    [list, selected],
  );

  const cameras = useCameras();
  const infrastructure = useInfrastructure();
  const closeCamera = cameras.close;
  const closeInfrastructure = infrastructure.close;
  const closeCatalogues = useCallback(() => {
    closeCamera();
    closeInfrastructure();
  }, [closeCamera, closeInfrastructure]);
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

  const { focusCamera, cameraLayers } = useCameraSelection(
    cameras,
    tools.picking,
    close,
    engine,
    mode,
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
    mode,
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
            conflicts,
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
              ? { country: nation, events: scoped, selectedId, now, onSelect: focus }
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
          <ControlPanel side="left" label="Topics & time" icon="topics">
            <LayerPanel
              counts={counts}
              hidden={hidden}
              stats={stats}
              status={status}
              error={error}
              windowHours={windowHours}
              onWindow={setWindow}
              onToggle={toggleCategory}
            />
          </ControlPanel>
        </GlobeControls>
      )}
      <MeasurementReadout value={measurement} />
      {supported && !opsRoom && !tools.picking && (
        <CoordinateReadout engine={engine} bng={britishGrid.enabled} />
      )}
      {!opsRoom &&
        !tools.picking &&
        (infrastructure.selected ? (
          <InfrastructureInspector
            selected={infrastructure.selected}
            data={infrastructure.data}
            onClose={infrastructure.close}
          />
        ) : cameras.selected ? (
          <CameraInspector
            key={cameras.selected.id}
            camera={cameras.selected}
            onClose={cameras.close}
          />
        ) : (
          <SelectedMapDetails
            selected={selected}
            storySize={storySize}
            details={details}
            events={pickableEvents}
            cells={gnssFilters.filtered}
            updatedAt={gnss.updated_at}
            interference={interference}
            onSelect={choose}
            onClose={close}
          />
        ))}
    </div>
  );
}
