/** Capture the live map's view configuration and apply a saved one, without its events. */
import { useCallback, useEffect, useLayoutEffect, useRef } from 'react';

import type { Category } from '@/lib/api/eventSchemas';
import { CATEGORIES } from '@/lib/api/eventSchemas';
import type { LiveViewCamera, LiveViewFilters, LiveViewState } from '@/lib/liveViews/liveViewState';
import type { BaseLayer, ViewMode } from '@/stores/globe';
import { useCyberFiltersStore } from '@/stores/cyberFilters';
import { usePlanMapFilterStore } from '@/stores/planMapFilter';
import type { ConflictGroup } from '@/lib/conflicts';
import type { ConflictPrecision } from '@/lib/conflictDisplayFilters';
import type { LocationQualityFilter } from './geographicPrecision';
import type { FlightFilter } from './flightFilters';
import type { ObservationKind, ObservationVisibility } from './ObservationControls';
import type { GlobeEngineHandle } from './useGlobeEngine';

const TRAFFIC: readonly ObservationKind[] = ['aircraft', 'vessels', 'firms'];

/** The live map state a view reads and writes; every member already exists on the page. */
export interface LiveViewSources {
  engine: Pick<GlobeEngineHandle, 'getCamera' | 'restoreCamera'>;
  mode: ViewMode;
  setMode: (mode: ViewMode) => void;
  baseLayer: BaseLayer;
  setBaseLayer: (layer: BaseLayer) => void;
  terminator: boolean;
  toggleTerminator: () => void;
  interference: boolean;
  toggleInterference: () => void;
  hidden: readonly Category[];
  toggleCategory: (category: Category) => void;
  windowHours: number | null;
  setWindow: (hours: number | null) => void;
  country: string | null;
  setCountry: (iso: string | null) => void;
  observations: {
    visibility: ObservationVisibility;
    toggle: (kind: ObservationKind) => void;
    flightFilter: FlightFilter;
    setFlightFilter: (value: FlightFilter) => void;
    vesselFilter: FlightFilter;
    setVesselFilter: (value: FlightFilter) => void;
  };
  fires: { enabled: boolean; toggleEnabled: () => void };
  quality: { filter: LocationQualityFilter; setFilter: (value: LocationQualityFilter) => void };
  gnss: {
    level: 'all' | 'red';
    setLevel: (value: 'all' | 'red') => void;
    minimum: number;
    setMinimum: (value: number) => void;
  };
  conflicts: {
    group: ConflictGroup;
    setGroup: (value: ConflictGroup) => void;
    includeHistorical: boolean;
    setIncludeHistorical: (value: boolean) => void;
    includeUnreviewed: boolean;
    setIncludeUnreviewed: (value: boolean) => void;
    precision: ConflictPrecision;
    setPrecision: (value: ConflictPrecision) => void;
  };
}

const DEFAULT_CAMERA: LiveViewCamera = { center: [0, 20], zoom: 1.5, bearing: 0, pitch: 0 };
const round = (value: number, places: number) => Number(value.toFixed(places));

function capture(sources: LiveViewSources): LiveViewState {
  const camera = sources.engine.getCamera?.() ?? null;
  const cyber = useCyberFiltersStore.getState();
  const filters: LiveViewFilters = {
    quality: sources.quality.filter,
    flight: sources.observations.flightFilter,
    vessel: sources.observations.vesselFilter,
    gnss_level: sources.gnss.level,
    gnss_minimum: [5, 10, 25, 50].includes(sources.gnss.minimum)
      ? (sources.gnss.minimum as 5 | 10 | 25 | 50)
      : 5,
    cyber_kind: cyber.kind,
    cyber_query: cyber.query.slice(0, 100),
    conflict_group: sources.conflicts.group,
    conflict_historical: sources.conflicts.includeHistorical,
    conflict_unreviewed: sources.conflicts.includeUnreviewed,
    conflict_precision: sources.conflicts.precision,
  };
  return {
    version: 1,
    projection: sources.mode,
    camera: camera
      ? {
          center: [round(camera.center[0], 5), round(camera.center[1], 5)],
          zoom: round(camera.zoom, 3),
          bearing: round(camera.bearing, 2),
          pitch: round(camera.pitch, 2),
        }
      : DEFAULT_CAMERA,
    base_layer: sources.baseLayer,
    layers: [
      ...CATEGORIES.filter((category) => !sources.hidden.includes(category)),
      ...TRAFFIC.filter((kind) => sources.observations.visibility[kind]),
      ...(sources.fires.enabled ? ['fires'] : []),
      ...(sources.interference ? ['interference'] : []),
      ...(sources.terminator ? ['terminator'] : []),
    ],
    window_hours: sources.windowHours,
    nation: sources.country,
    filters,
    plan_id: usePlanMapFilterStore.getState().planId,
  };
}

function apply(sources: LiveViewSources, view: LiveViewState) {
  const shown = new Set(view.layers);
  for (const category of CATEGORIES)
    if (shown.has(category) === sources.hidden.includes(category)) sources.toggleCategory(category);
  for (const kind of TRAFFIC)
    if (shown.has(kind) !== sources.observations.visibility[kind])
      sources.observations.toggle(kind);
  if (shown.has('fires') !== sources.fires.enabled) sources.fires.toggleEnabled();
  if (shown.has('interference') !== sources.interference) sources.toggleInterference();
  if (shown.has('terminator') !== sources.terminator) sources.toggleTerminator();
  if (view.base_layer) sources.setBaseLayer(view.base_layer);
  sources.setMode(view.projection);
  sources.setWindow(view.window_hours);
  sources.setCountry(view.nation);
  const { filters } = view;
  sources.quality.setFilter(filters.quality ?? 'all');
  sources.observations.setFlightFilter(filters.flight ?? 'all');
  sources.observations.setVesselFilter(filters.vessel ?? 'all');
  sources.gnss.setLevel(filters.gnss_level ?? 'all');
  sources.gnss.setMinimum(filters.gnss_minimum ?? 5);
  sources.conflicts.setGroup(filters.conflict_group ?? 'all');
  sources.conflicts.setIncludeHistorical(filters.conflict_historical ?? false);
  sources.conflicts.setIncludeUnreviewed(filters.conflict_unreviewed ?? false);
  sources.conflicts.setPrecision(filters.conflict_precision ?? 'all');
  const cyber = useCyberFiltersStore.getState();
  cyber.setKind(filters.cyber_kind ?? 'all');
  cyber.setQuery(filters.cyber_query ?? '');
  // The plan filter re-checks access when it loads; a lost plan clears itself with a notice.
  const plans = usePlanMapFilterStore.getState();
  if (plans.planId !== view.plan_id) plans.select(view.plan_id);
}

export function useLiveViewControls(sources: LiveViewSources) {
  const latest = useRef(sources);
  useLayoutEffect(() => {
    latest.current = sources;
  });
  // After a projection change the camera waits for the engine's own projection effect,
  // which runs first because the engine hook is called earlier on the page.
  const pendingCamera = useRef<LiveViewCamera | null>(null);
  const { engine, mode } = sources;
  useEffect(() => {
    const camera = pendingCamera.current;
    if (!camera) return;
    pendingCamera.current = null;
    engine.restoreCamera?.(camera);
  }, [engine, mode]);
  return {
    capture: useCallback(() => capture(latest.current), []),
    apply: useCallback((view: LiveViewState) => {
      const current = latest.current;
      apply(current, view);
      if (view.projection === current.mode) current.engine.restoreCamera?.(view.camera);
      else pendingCamera.current = view.camera;
    }, []),
  };
}

export type LiveViewControls = ReturnType<typeof useLiveViewControls>;
