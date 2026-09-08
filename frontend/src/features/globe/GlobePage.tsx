/** Full-canvas globe with on-demand layer and measurement tools. */
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useInfrastructure } from './infrastructure/useInfrastructure';
import { useInfrastructureSelection } from './infrastructure/useInfrastructureSelection';
import { InfrastructurePanel } from './infrastructure/InfrastructurePanel';
import { InfrastructureInspector } from './infrastructure/InfrastructureInspector';

import { WebGlFallback } from './WebGlFallback';
import { usePageVisible, useReducedMotion } from '@/components/brand/useMotionPreferences';
import { useCameras } from './cameras/useCameras';
import { CameraPanel } from './cameras/CameraPanel';
import { CameraInspector } from './cameras/CameraInspector';
import { useCameraSelection } from './cameras/useCameraSelection';
import { useNow } from '@/lib/hooks/useNow';
import { useAuthStore } from '@/stores/auth';
import { useMapReferenceData } from './useMapReferenceData';
import {
  countByCategory,
  filterByCountry,
  filterByWindow,
  selectSelectedEvent,
  useEventsStore,
} from '@/stores/events';
import { useGlobeStore } from '@/stores/globe';

import { BaseLayerToolbar } from './BaseLayerToolbar';
import { GeographicPrecisionPanel } from './GeographicPrecisionPanel';
import { CoordinateReadout } from './CoordinateReadout';
import { CountryPanel } from './CountryPanel';
import { SelectedMapDetails } from './SelectedMapDetails';
import { useBritishGrid } from './useBritishGrid';
import { BritishGridTool } from './BritishGridTool';
import { ControlPanel, GlobeControls } from './GlobeControls';
import { MeasurementReadout } from './MeasurementReadout';
import { MapLayerRail } from './MapLayerRail';
import { MapNavigationTools } from './MapNavigationTools';
import { LayerPanel } from './LayerPanel';
import { ModeToolbar } from './ModeToolbar';
import { NationFilter } from './NationFilter';
import { Ticker } from './Ticker';
import { WorldClocks } from './WorldClocks';
import { MapMeasurementPanel } from '@/components/maps/MapMeasurementPanel';
import { useMapMeasurement } from './useMapMeasurement';
import { measurementLayers } from '@/lib/map/measurementLayers';
import { useObservationFilters } from './ObservationControls';
import { useSatelliteFilters } from './useSatelliteFilters';
import { SatelliteFilterPanel } from './SatelliteFilterPanel';
import './dashboard.css';
import { createMapLibreEngine } from './engine/MapLibreEngine';
import { useInterference } from './useInterference';
import { useGlobeScene } from './useGlobeScene';
import { useMapPicking } from './useMapPicking';

import { clusteringZoomFor } from './layers/clusters';
import { useGlobeEngine } from './useGlobeEngine';
import { useLiveEvents } from './useLiveEvents';
import { hasWebGl2 } from './webgl';

export { FOCUS_ZOOM } from './useMapFocus';
import { useMapFocus } from './useMapFocus';

// Only our own tile proxy ever sees the session token; the engine checks the origin.
const createEngine = () =>
  createMapLibreEngine({ authHeader: () => useAuthStore.getState().accessToken });

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
  const toggleInterference = useGlobeStore((state) => state.toggleInterference);
  const opsRoom = useGlobeStore((state) => state.opsRoom);
  const reducedMotion = useReducedMotion();
  const visible = usePageVisible();
  const { cells: jamCells, updated_at: jamUpdatedAt } = useInterference(interference);
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
  const measurement = useMapMeasurement(engine, supported && !opsRoom);
  const measured = useMemo(
    () => measurementLayers(measurement.points, measurement.mode, mode === 'map'),
    [measurement.points, measurement.mode, mode],
  );
  const now = useNow();
  const [zoom, setZoom] = useState(1.5);
  useEffect(
    () =>
      engine.onView((view) => {
        setZoom(clusteringZoomFor(view.zoom));
      }),
    [engine],
  );
  const { osMaps, countries, countryByIso, countriesError } = useMapReferenceData(
    baseLayer,
    setBaseLayer,
  );

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
  } = useMapPicking(
    satellites.filtered,
    hidden,
    measurement.picking,
    select,
    engine,
    closeCatalogues,
  );

  const { focusCamera, cameraLayers } = useCameraSelection(
    cameras,
    measurement.picking,
    close,
    engine,
    mode,
  );
  const { focus: focusInfrastructure, layers: infrastructureLayers } = useInfrastructureSelection(
    infrastructure,
    measurement.picking,
    close,
    engine,
    mode,
  );
  useGlobeScene({
    engine,
    events: satellites.filtered,
    hidden,
    selectedId,
    highlightedId,
    onPick,
    onCluster,
    onJam,
    jamCells,
    gridLayers: britishGrid.layers,
    cameraLayers,
    infrastructureLayers,
    measured,
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
      {supported ? (
        <div
          ref={containerRef}
          role="region"
          aria-label={mode === 'globe' ? '3D globe' : 'Map'}
          data-testid="map-container"
          // MapLibre's stylesheet forces position: relative on this element, so it
          // needs an explicit height rather than absolute positioning.
          className="h-full w-full"
        />
      ) : (
        <WebGlFallback />
      )}
      {!opsRoom && <ModeToolbar mode={mode} onChange={setMode} />}
      <Ticker events={scoped} selectedId={selectedId} now={now} onSelect={focus} />
      <WorldClocks />
      {!opsRoom && (
        <GlobeControls
          layers={
            <MapLayerRail
              events={scoped}
              counts={counts}
              visibility={observations.visibility}
              onToggle={observations.toggle}
              flightFilter={observations.flightFilter}
              onFlightFilter={observations.setFlightFilter}
            />
          }
          navigation={<MapNavigationTools engine={engine} enabled={supported} />}
        >
          <ControlPanel side="left" label="Infrastructure" icon="signal">
            <InfrastructurePanel state={infrastructure} onSelect={focusInfrastructure} />
          </ControlPanel>
          <ControlPanel side="left" label="Satellite filters" icon="filter">
            <SatelliteFilterPanel
              group={satellites.group}
              setGroup={satellites.setGroup}
              counts={satellites.counts}
            />
          </ControlPanel>
          <ControlPanel side="right" label="Map style" icon="layers">
            <BaseLayerToolbar
              initialExpanded
              value={baseLayer}
              osAvailable={osMaps}
              onChange={setBaseLayer}
            />
          </ControlPanel>
          <ControlPanel label="Measure distance and area" icon="measure">
            <MapMeasurementPanel key={measurement.resetSequence} value={measurement} />
          </ControlPanel>
          <ControlPanel label="Find nation" icon="nation">
            <NationFilter
              countries={countries}
              value={country}
              onChange={changeNation}
              error={countriesError}
            />
            {nation !== null && (
              <CountryPanel
                country={nation}
                events={scoped}
                selectedId={selectedId}
                now={now}
                onSelect={focus}
              />
            )}
          </ControlPanel>
          <ControlPanel side="left" label="Layers and settings" icon="settings">
            <LayerPanel
              observations={{
                events: scoped,
                visibility: observations.visibility,
                onToggle: observations.toggle,
              }}
              counts={counts}
              hidden={hidden}
              stats={stats}
              status={status}
              error={error}
              terminator={terminator}
              lite={lite}
              windowHours={windowHours}
              onWindow={setWindow}
              onToggle={toggleCategory}
              onToggleTerminator={toggleTerminator}
              onToggleLite={toggleLite}
              interference={interference}
              onToggleInterference={toggleInterference}
            />
          </ControlPanel>
          <ControlPanel label="Location precision" icon="precision">
            <GeographicPrecisionPanel
              events={satellites.filtered}
              hidden={hidden}
              onSelect={focus}
            />
          </ControlPanel>
          <ControlPanel side="right" label="British National Grid" icon="grid">
            <BritishGridTool grid={britishGrid} engine={engine} />
          </ControlPanel>
          <ControlPanel side="left" label="CCTV" icon="camera">
            <CameraPanel cameras={cameras} onSelect={focusCamera} />
          </ControlPanel>
        </GlobeControls>
      )}
      <MeasurementReadout value={measurement} />
      {supported && !opsRoom && !measurement.picking && (
        <CoordinateReadout engine={engine} bng={britishGrid.enabled} />
      )}
      {!opsRoom &&
        !measurement.picking &&
        (infrastructure.selected ? (
          <InfrastructureInspector
            selected={infrastructure.selected}
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
            cells={jamCells}
            updatedAt={jamUpdatedAt}
            interference={interference}
            onSelect={choose}
            onClose={close}
          />
        ))}
    </div>
  );
}
