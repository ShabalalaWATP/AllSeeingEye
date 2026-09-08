/** Full-canvas globe with on-demand layer and measurement tools. */
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

import { WebGlFallback } from './WebGlFallback';
import { usePageVisible, useReducedMotion } from '@/components/brand/useMotionPreferences';
import type { LiveEvent } from '@/lib/api/eventSchemas';
import { zoomForBounds } from '@/lib/api/geo';
import { useNow } from '@/lib/hooks/useNow';
import { useAuthStore } from '@/stores/auth';
import { useCapabilitiesStore } from '@/stores/capabilities';
import { useCountriesStore } from '@/stores/countries';
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
import { isMappedEvent } from './geographicPrecision';
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
import './dashboard.css';
import { createMapLibreEngine } from './engine/MapLibreEngine';
import { isOsLayer } from './engine/baseLayers';
import { buildEventLayers } from './layers/registry';
import { useInterference } from './useInterference';
import { useMapPicking } from './useMapPicking';

import { clusteringZoomFor } from './layers/clusters';
import { buildJamLayer } from './layers/jamming';
import { buildTerminatorLayer } from './layers/terminator';
import { useGlobeEngine } from './useGlobeEngine';
import { useLiveEvents } from './useLiveEvents';
import { hasWebGl2 } from './webgl';

/** Zoom used when the user focuses an event from a list. */
export const FOCUS_ZOOM = 4;

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
  const osMaps = useCapabilitiesStore((state) => state.osMaps);
  const capabilitiesLoaded = useCapabilitiesStore((state) => state.loaded);
  const loadCapabilities = useCapabilitiesStore((state) => state.load);
  useEffect(() => {
    void loadCapabilities();
  }, [loadCapabilities]);
  useEffect(() => {
    // A remembered OS layer is meaningless on a server without an OS key.
    if (capabilitiesLoaded && !osMaps && isOsLayer(baseLayer)) setBaseLayer('dark');
  }, [baseLayer, capabilitiesLoaded, osMaps, setBaseLayer]);

  const countries = useCountriesStore((state) => state.items);
  const countryByIso = useCountriesStore((state) => state.byIso);
  const loadCountries = useCountriesStore((state) => state.load);
  const countriesError = useCountriesStore((state) => state.error);
  useEffect(() => {
    void loadCountries();
  }, [loadCountries]);

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
  const nation = country === null ? null : (countryByIso[country] ?? null);
  const storySize = useMemo(
    () =>
      selected?.story_id == null
        ? 1
        : list.filter((event) => event.story_id === selected.story_id).length,
    [list, selected],
  );

  const {
    details,
    highlightedId,
    visible: pickableEvents,
    choose,
    close,
    onPick,
    onCluster,
    onJam,
  } = useMapPicking(observations.filtered, hidden, measurement.picking, select, engine);

  const eventLayers = useMemo(
    () =>
      supported
        ? buildEventLayers(observations.filtered, hidden, onPick, selectedId ?? highlightedId, {
            zoom,
            onCluster,
            globe: mode === 'globe',
          })
        : [],
    [
      hidden,
      onCluster,
      onPick,
      observations.filtered,
      selectedId,
      supported,
      zoom,
      mode,
      highlightedId,
    ],
  );
  const night = useMemo(
    () => (supported && terminator && !lite ? [buildTerminatorLayer(new Date(now))] : []),
    [lite, now, supported, terminator],
  );
  const jam = useMemo(
    () => (supported && interference ? buildJamLayer(jamCells, onJam) : null),
    [interference, jamCells, supported, onJam],
  );
  useEffect(() => {
    if (supported)
      engine.setLayers([
        ...night,
        ...(jam === null ? [] : [jam]),
        ...britishGrid.layers,
        ...eventLayers,
        ...measured,
      ]);
  }, [engine, eventLayers, jam, night, supported, measured, britishGrid.layers]);

  // The wall screen turns the globe slowly; lite mode and the flat map keep it still.
  useEffect(() => {
    if (!supported) return;
    engine.spin(opsRoom && mode === 'globe' && !lite && !reducedMotion && visible);
    return () => {
      engine.spin(false);
    };
  }, [engine, lite, mode, opsRoom, reducedMotion, supported, visible]);

  const focus = useCallback(
    (event: LiveEvent) => {
      select(event.id);
      if (event.point !== null && isMappedEvent(event)) {
        engine.flyTo({ center: [event.point.lon, event.point.lat], zoom: FOCUS_ZOOM });
      }
    },
    [engine, select],
  );

  const changeNation = useCallback(
    (iso: string | null) => {
      setCountry(iso);
      const target = iso === null ? null : countryByIso[iso];
      if (target !== null && target !== undefined) {
        engine.flyTo({ center: target.centroid, zoom: zoomForBounds(target.bounds) });
      }
    },
    [countryByIso, engine, setCountry],
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
            />
          }
          navigation={<MapNavigationTools engine={engine} enabled={supported} />}
        >
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
              events={observations.filtered}
              hidden={hidden}
              onSelect={focus}
            />
          </ControlPanel>
          <ControlPanel side="right" label="British National Grid" icon="grid">
            <BritishGridTool grid={britishGrid} engine={engine} />
          </ControlPanel>
          <ControlPanel side="left" label="CCTV" icon="camera">
            <p className="p-3 text-sm text-muted">
              Public CCTV integration is planned. Camera locations and previews are not available
              yet.
            </p>
          </ControlPanel>
        </GlobeControls>
      )}
      <MeasurementReadout value={measurement} />
      {supported && !opsRoom && !measurement.picking && (
        <CoordinateReadout engine={engine} bng={britishGrid.enabled} />
      )}
      {!opsRoom && !measurement.picking && (
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
      )}
    </div>
  );
}
