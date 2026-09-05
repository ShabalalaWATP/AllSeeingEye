/**
 * The root view: a full-bleed 3D globe (default) with an explicit Map mode
 * toggle, live event markers, the day and night terminator, base layers, the
 * nation filter, layer panel, country panel, ticker, inspector and coordinate
 * readout. When WebGL2 is unavailable the engine is not mounted and the page
 * explains why; the panels still work from the event mirror.
 */
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

import { Alert } from '@/components/ui/Alert';
import type { LiveEvent } from '@/lib/api/eventSchemas';
import { zoomForBounds } from '@/lib/api/geo';
import { useNow } from '@/lib/hooks/useNow';
import { useAuthStore } from '@/stores/auth';
import { useCapabilitiesStore } from '@/stores/capabilities';
import { useCountriesStore } from '@/stores/countries';
import {
  countByCategory,
  filterByCountry,
  selectSelectedEvent,
  useEventsStore,
} from '@/stores/events';
import { useGlobeStore } from '@/stores/globe';

import { BaseLayerToolbar } from './BaseLayerToolbar';
import { CoordinateReadout } from './CoordinateReadout';
import { CountryPanel } from './CountryPanel';
import { EventInspector } from './EventInspector';
import { LayerPanel } from './LayerPanel';
import { ModeToolbar } from './ModeToolbar';
import { NationFilter } from './NationFilter';
import { Ticker } from './Ticker';
import { createMapLibreEngine } from './engine/MapLibreEngine';
import { isOsLayer } from './engine/baseLayers';
import { buildEventLayers } from './layers/registry';
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
  const now = useNow();

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
  const scoped = useMemo(() => filterByCountry(list, country), [list, country]);
  const counts = useMemo(() => countByCategory(scoped), [scoped]);
  const nation = country === null ? null : (countryByIso[country] ?? null);
  const storySize = useMemo(
    () =>
      selected?.story_id == null
        ? 1
        : list.filter((event) => event.story_id === selected.story_id).length,
    [list, selected],
  );

  const onPick = useCallback(
    (event: LiveEvent | null) => {
      select(event?.id ?? null);
    },
    [select],
  );

  useEffect(() => {
    if (!supported) return;
    const events = buildEventLayers(scoped, hidden, onPick, selectedId);
    const night = terminator && !lite ? [buildTerminatorLayer(new Date(now))] : [];
    engine.setLayers([...night, ...events]);
  }, [engine, hidden, lite, now, onPick, scoped, selectedId, supported, terminator]);

  const focus = useCallback(
    (event: LiveEvent) => {
      select(event.id);
      if (event.point !== null) {
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

  const close = useCallback(() => {
    select(null);
  }, [select]);

  return (
    // Fills the shell's relative <main> directly: a percentage height would collapse
    // because the main area takes its height from flex, not from an explicit value.
    <div className="absolute inset-0 bg-ground">
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
      <ModeToolbar mode={mode} onChange={setMode} />
      <Ticker events={scoped} selectedId={selectedId} now={now} onSelect={focus} />
      <div className="absolute top-16 bottom-3 left-3 z-10 flex w-52 flex-col gap-2 overflow-y-auto">
        <BaseLayerToolbar value={baseLayer} osAvailable={osMaps} onChange={setBaseLayer} />
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
          onToggle={toggleCategory}
          onToggleTerminator={toggleTerminator}
          onToggleLite={toggleLite}
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
      </div>
      {supported && <CoordinateReadout engine={engine} />}
      {selected !== null && (
        <EventInspector event={selected} storySize={storySize} onClose={close} />
      )}
    </div>
  );
}
