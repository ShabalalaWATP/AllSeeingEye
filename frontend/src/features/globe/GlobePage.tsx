/**
 * The root view: a full-bleed 3D globe (default) with an explicit Map mode
 * toggle, live event markers, the nation filter, layer panel, country panel,
 * ticker and inspector. When WebGL2 is unavailable the engine is not mounted
 * and the page explains why; the panels still work from the event mirror.
 */
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

import { Alert } from '@/components/ui/Alert';
import type { LiveEvent } from '@/lib/api/eventSchemas';
import { zoomForBounds } from '@/lib/api/geo';
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
import { CountryPanel } from './CountryPanel';
import { EventInspector } from './EventInspector';
import { LayerPanel } from './LayerPanel';
import { ModeToolbar } from './ModeToolbar';
import { NationFilter } from './NationFilter';
import { Ticker } from './Ticker';
import { createMapLibreEngine } from './engine/MapLibreEngine';
import { buildEventLayers } from './layers/registry';
import { useGlobeEngine } from './useGlobeEngine';
import { useLiveEvents } from './useLiveEvents';
import { useNow } from './useNow';
import { hasWebGl2 } from './webgl';

/** Zoom used when the user focuses an event from a list. */
export const FOCUS_ZOOM = 4;

export default function GlobePage() {
  const mode = useGlobeStore((state) => state.mode);
  const setMode = useGlobeStore((state) => state.setMode);
  const baseLayer = useGlobeStore((state) => state.baseLayer);
  const setBaseLayer = useGlobeStore((state) => state.setBaseLayer);
  const [supported] = useState(() => hasWebGl2());
  const containerRef = useRef<HTMLDivElement>(null);
  // Only our own tile proxy ever sees the session token; the engine checks the origin.
  const createEngine = useCallback(
    () => createMapLibreEngine({ authHeader: () => useAuthStore.getState().accessToken }),
    [],
  );
  const engine = useGlobeEngine(containerRef, mode, supported, baseLayer, createEngine);
  const osMaps = useCapabilitiesStore((state) => state.osMaps);
  const loadCapabilities = useCapabilitiesStore((state) => state.load);
  useEffect(() => {
    void loadCapabilities();
  }, [loadCapabilities]);
  useLiveEvents();
  const now = useNow();

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

  const onPick = useCallback(
    (event: LiveEvent | null) => {
      select(event?.id ?? null);
    },
    [select],
  );

  useEffect(() => {
    if (!supported) return;
    engine.setLayers(buildEventLayers(scoped, hidden, onPick, selectedId));
  }, [engine, hidden, scoped, onPick, selectedId, supported]);

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
          onToggle={toggleCategory}
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
      {selected !== null && <EventInspector event={selected} onClose={close} />}
    </div>
  );
}
