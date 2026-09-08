/**
 * The root view: a full-bleed 3D globe (default) with an explicit Map mode
 * toggle, live event markers, the day and night terminator, base layers, the
 * nation filter, layer panel, country panel, ticker, inspector and coordinate
 * readout. When WebGL2 is unavailable the engine is not mounted and the page
 * explains why; the panels still work from the event mirror.
 */
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

import { Alert } from '@/components/ui/Alert';
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
import { EventInspector } from './EventInspector';
import { GlobeControls } from './GlobeControls';
import { LayerPanel } from './LayerPanel';
import { ModeToolbar } from './ModeToolbar';
import { NationFilter } from './NationFilter';
import { Ticker } from './Ticker';
import { WorldClocks } from './WorldClocks';
import { MapMeasurementPanel } from '@/components/maps/MapMeasurementPanel';
import { useMapMeasurement } from './useMapMeasurement';
import { measurementLayers } from '@/lib/map/measurementLayers';
import { ObservationControls, useObservationFilters } from './ObservationControls';
import './dashboard.css';
import { createMapLibreEngine } from './engine/MapLibreEngine';
import { isOsLayer } from './engine/baseLayers';
import { buildEventLayers } from './layers/registry';
import { useInterference } from './useInterference';
import { MapDetailsInspector } from './MapDetailsInspector';
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
        ? buildEventLayers(observations.filtered, hidden, onPick, selectedId, {
            zoom,
            onCluster,
            globe: mode === 'globe',
          })
        : [],
    [hidden, onCluster, onPick, observations.filtered, selectedId, supported, zoom, mode],
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
      engine.setLayers([...night, ...(jam === null ? [] : [jam]), ...eventLayers, ...measured]);
  }, [engine, eventLayers, jam, night, supported, measured]);

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
    // Fills the shell's relative <main> directly: a percentage height would collapse
    // because the main area takes its height from flex, not from an explicit value.
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
        <div className="flex h-full items-center justify-center p-6">
          <Alert tone="warning" title="WebGL2 is required" className="max-w-md">
            The globe needs WebGL2, which this browser or device does not provide. Enable hardware
            acceleration or use a current version of Chrome, Edge, Firefox or Safari.
          </Alert>
        </div>
      )}
      {!opsRoom && <ModeToolbar mode={mode} onChange={setMode} />}
      <Ticker events={scoped} selectedId={selectedId} now={now} onSelect={focus} />
      <WorldClocks />
      {!opsRoom && (
        <GlobeControls>
          <BaseLayerToolbar value={baseLayer} osAvailable={osMaps} onChange={setBaseLayer} />
          <MapMeasurementPanel key={measurement.resetSequence} value={measurement} />
          <ObservationControls
            events={scoped}
            visibility={observations.visibility}
            hidden={hidden}
            onToggle={observations.toggle}
          />
          <NationFilter
            countries={countries}
            value={country}
            onChange={changeNation}
            error={countriesError}
          />
          <LayerPanel
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
          <GeographicPrecisionPanel
            events={observations.filtered}
            hidden={hidden}
            onSelect={focus}
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
        </GlobeControls>
      )}
      {measurement.picking && (
        <button
          type="button"
          onClick={() => measurement.setPicking(false)}
          className="absolute bottom-24 left-1/2 z-10 -translate-x-1/2 rounded border border-cyan bg-ground px-3 py-2 text-xs text-cyan"
        >
          {measurement.points.length}/32 points · Stop measuring
        </button>
      )}
      {supported && !opsRoom && !measurement.picking && <CoordinateReadout engine={engine} />}
      {selected === null &&
        details &&
        !opsRoom &&
        !measurement.picking &&
        (details.kind !== 'jam' || interference) && (
          <MapDetailsInspector
            key={
              details.kind === 'cluster'
                ? details.cluster.id
                : `${details.cell.lon}:${details.cell.lat}`
            }
            details={details}
            events={pickableEvents}
            cells={jamCells}
            updatedAt={jamUpdatedAt}
            onSelect={choose}
            onClose={close}
          />
        )}
      {selected !== null && !opsRoom && !measurement.picking && (
        <EventInspector event={selected} storySize={storySize} onClose={close} />
      )}
    </div>
  );
}
