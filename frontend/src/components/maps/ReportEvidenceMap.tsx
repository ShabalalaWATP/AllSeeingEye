import { useCallback, useEffect, useMemo, useRef, useState, useSyncExternalStore } from 'react';
import type { EvidenceItem } from '@/lib/api/reports';
import { useAuthStore } from '@/stores/auth';
import { subscribeWorkspaceAccess, workspaceRevision } from '@/lib/workspaceAccess';
import { Alert } from '@/components/ui/Alert';
import { MapTimelineHeader } from './MapTimelineHeader';
import { MapResearchLaunchLink } from './MapResearchLaunchLink';
import { MapFilters } from './MapFilters';
import { MapEvidenceList } from './MapEvidenceList';
import { MapOverlaySet } from './MapOverlaySet';
import { MapAreaSelection } from './MapAreaSelection';
import { useAreaSelection } from './useAreaSelection';
import { areasEqual } from '@/lib/map/areaGeometry';
import { SavedMapControls } from './SavedMapControls';
import { useSavedMapViews } from './useSavedMapViews';
import { initialMapState, fromCamera, matchesMapFilters } from './savedMapState';
import type { MapState, SavedMapView } from '@/lib/api/mapViews';
import type { MapBounds, MapCamera } from '@/lib/map/MapEngine';
import { FootprintSearchPanel } from './FootprintSearchPanel';
import type { LocalCollection } from '@/lib/map/geoJsonTypes';
import { geometryIsPolar } from '@/lib/map/localGeoJson';
import { hasEvidencePoint, hasLegacyEvidencePoint, mapTimelineDay } from './evidenceGeometry';
import { MapDisplayVersionNotice } from './MapDisplayVersionNotice';
import { MapGeometryOmissions } from './MapGeometryOmissions';
import { prepareEvidenceGeometry } from './frozenEvidenceGeometry';

import { MapMeasurementPanel } from './MapMeasurementPanel';
import { useReportMeasurement } from './useReportMeasurement';
import { ReportMapRenderer } from './ReportMapRenderer';

const PAGE_SIZE = 20;
export interface ReportEvidenceMapProps {
  reportId: string;
  version: number;
  initialTimeBasis?: MapState['time_basis'];
  evidence: readonly EvidenceItem[];
  onSelectEvidence?: (label: string) => void;
  savedView?: SavedMapView | undefined;
  scopeLabel?: string;
  canCreateView?: boolean;
  canManageView?: (view: { created_by: string; team_id: string | null }) => boolean;
}
/** Authorised frozen evidence only: no shared event store or live stream. */
export default function ReportEvidenceMap({
  reportId,
  version,
  initialTimeBasis = 'publication',
  evidence,
  onSelectEvidence,
  savedView,
  scopeLabel = 'this personal view',
  canCreateView = false,
  canManageView = () => false,
}: ReportEvidenceMapProps) {
  const actor = useAuthStore(
    (state) =>
      `${state.status}:${state.user?.id ?? ''}:${state.user?.role ?? ''}:${state.user?.is_active ?? false}`,
  );
  const revision = useSyncExternalStore(subscribeWorkspaceAccess, workspaceRevision);
  const [authority] = useState({ actor, revision, reportId, version });
  const valid =
    authority.actor === actor &&
    authority.revision === revision &&
    authority.reportId === reportId &&
    authority.version === version &&
    actor.startsWith('authenticated:') &&
    actor.endsWith(':true');
  const [footprints, setFootprints] = useState<LocalCollection | null>(null);
  const [state, setState] = useState<MapState>(
    () => savedView?.revision.state ?? { ...initialMapState(), time_basis: initialTimeBasis },
  );
  const saved = useSavedMapViews(reportId, version, savedView);
  const areaChanged = useMemo(
    () => !areasEqual(state.aoi, saved.active?.revision.state.aoi ?? null),
    [state.aoi, saved.active?.revision.state.aoi],
  );
  const updateArea = useCallback(
    (aoi: MapState['aoi']) => setState((value) => ({ ...value, aoi })),
    [],
  );
  const areaSelection = useAreaSelection(updateArea);
  const resetArea = areaSelection.cancel;
  const viewport = useRef<(() => MapBounds | null) | null>(null);
  const viewportReady = useCallback((read: (() => MapBounds | null) | null) => {
    viewport.current = read;
  }, []);
  const readViewport = useCallback(() => viewport.current?.() ?? null, []);
  const [focusRequest, setFocusRequest] = useState<{ label: string; sequence: number } | null>(
    null,
  );
  const captureCamera = useCallback(
    (camera: MapCamera) => setState((value) => ({ ...value, camera: fromCamera(camera) })),
    [],
  );
  useEffect(() => {
    const clear = () => {
      setState(initialMapState());
      setFootprints(null);
      resetArea();
    };
    const offAccess = subscribeWorkspaceAccess(clear);
    const offAuth = useAuthStore.subscribe((state, previous) => {
      if (
        state.status !== previous.status ||
        state.user?.id !== previous.user?.id ||
        state.user?.role !== previous.user?.role ||
        state.user?.is_active !== previous.user?.is_active
      )
        clear();
    });
    return () => {
      offAccess();
      offAuth();
    };
  }, [resetArea]);
  const [opened, setOpened] = useState(false);
  const measurement = useReportMeasurement(state, setState, opened);
  const projection = state.projection;
  const selected = state.selected_evidence;
  const setProjection = (projection: MapState['projection']) =>
    setState((value) => ({ ...value, projection }));
  const [page, setPage] = useState(0);
  const days = useMemo(
    () =>
      [
        ...new Set(
          evidence
            .map((item) => mapTimelineDay(item, state.time_basis))
            .filter((value): value is string => value !== null),
        ),
      ].sort(),
    [evidence, state.time_basis],
  );
  const sources = useMemo(
    () => [...new Map(evidence.map((item) => [item.source_id, item.source_name])).entries()],
    [evidence],
  );
  const { source_ids, published_since, published_until, include_unknown_dates, time_basis } = state;
  const filtered = useMemo(
    () =>
      evidence.filter((item) =>
        matchesMapFilters(item, {
          source_ids,
          published_since,
          published_until,
          include_unknown_dates,
          time_basis,
        }),
      ),
    [evidence, source_ids, published_since, published_until, include_unknown_dates, time_basis],
  );
  const current = Math.min(page, Math.max(0, Math.ceil(filtered.length / PAGE_SIZE) - 1));
  const prepared = useMemo(
    () =>
      prepareEvidenceGeometry(
        filtered,
        state.overlays,
        state.aoi,
        footprints,
        state.display_transform,
      ),
    [filtered, state.overlays, state.aoi, footprints, state.display_transform],
  );
  const chosen = filtered.find((item) => item.label === selected);
  const select = useCallback((label: string) => {
    setState((value) => ({ ...value, selected_evidence: label }));
    setFocusRequest((value) => ({ label, sequence: (value?.sequence ?? 0) + 1 }));
  }, []);
  if (!valid)
    return (
      <Alert tone="warning">
        Account or access changed. Reload the authorised report before reopening its map.
      </Alert>
    );
  const supportsPoint =
    state.display_transform === 'ase-geojson-display-v1'
      ? hasLegacyEvidencePoint
      : hasEvidencePoint;
  const polar =
    prepared.source.features.filter((feature) => geometryIsPolar(feature.geometry)).length +
    filtered.filter((item) => supportsPoint(item) && Math.abs(item.lat ?? 0) > 85.05112878).length +
    prepared.overlays.reduce(
      (sum, overlay) =>
        sum +
        overlay.display.features.filter((feature) => geometryIsPolar(feature.geometry)).length,
      0,
    ) +
    (prepared.aoi?.features.filter((feature) => geometryIsPolar(feature.geometry)).length ?? 0) +
    (prepared.footprints?.features.filter((feature) => geometryIsPolar(feature.geometry)).length ??
      0);
  return (
    <section
      aria-label="Saved evidence map and timeline"
      className="space-y-4 rounded-md border border-line p-4"
    >
      <MapTimelineHeader version={version} timeBasis={state.time_basis} />
      <MapDisplayVersionNotice
        version={state.display_transform}
        onUpgrade={() =>
          setState((value) => ({ ...value, display_transform: 'ase-geojson-display-v2' }))
        }
      />
      <MapFilters
        state={state}
        onChange={(value) => {
          setState(value);
          setPage(0);
        }}
        days={days}
        sources={sources}
      />
      <p className="text-xs text-muted">
        {filtered.length} records · {filtered.filter(supportsPoint).length} supported positions ·{' '}
        {prepared.source.features.length} supported source geometries. Hollow rings are approximate
        locations, not measured uncertainty areas. Country-only and unknown locations remain in the
        list.
      </p>
      <MapGeometryOmissions omissions={prepared.omissions} />
      <MapOverlaySet
        preparedFirst={prepared.firstOverlay}
        overlays={state.overlays}
        onChange={(overlays) =>
          setState((value) => ({
            ...value,
            overlays: typeof overlays === 'function' ? overlays(value.overlays) : overlays,
          }))
        }
      />
      <MapAreaSelection
        selection={{
          ...areaSelection,
          start: () => {
            measurement.setPicking(false);
            areaSelection.start();
          },
        }}
        hasArea={!!state.aoi}
        opened={opened}
        readViewport={readViewport}
        changed={areaChanged}
      />
      <MapResearchLaunchLink
        saved={saved.active}
        changed={areaChanged || areaSelection.dirty || areaSelection.picking}
      />
      <MapMeasurementPanel
        key={measurement.resetSequence}
        value={{ ...measurement, canPick: measurement.canPick && !areaSelection.picking }}
        persistenceNote="Save the map to retain these coordinates and the calculation method in its revision. Incomplete sketches can also be saved."
      />
      <FootprintSearchPanel onChange={setFootprints} />
      <SavedMapControls
        saved={saved}
        state={state}
        scopeLabel={scopeLabel}
        canCreate={canCreateView}
        canEdit={!!saved.active && canManageView(saved.active.view)}
        blocked={
          areaSelection.dirty
            ? 'Apply or discard the area draft before saving the map.'
            : footprints?.features.length
              ? 'Clear the temporary catalogue footprints before saving. Catalogue source-version receipts are not yet captured in saved views.'
              : null
        }
      />
      <ReportMapRenderer
        opened={opened}
        onOpened={(value) => {
          setOpened(value);
          if (!value) {
            setFocusRequest(null);
            measurement.setPicking(false);
          }
        }}
        onProjection={setProjection}
        polar={polar}
        canvas={{
          sourceGeometry: prepared.source,
          legacyDisplay: state.display_transform === 'ase-geojson-display-v1',
          footprints: prepared.footprints,
          overlays: prepared.overlays,
          aoi: prepared.aoi,
          areaMode: areaSelection.picking,
          onAreaPoint: areaSelection.pick,
          measurement: state.measurement,
          measurementMode: measurement.picking && !areaSelection.picking,
          onMeasurementPoint: ([lon, lat]) => measurement.add(lon, lat),
          onViewportReady: viewportReady,
          camera: state.camera,
          onCamera: captureCamera,
          basemap: state.basemap,
          focusRequest,
          evidence: filtered,
          projection,
          selected: chosen?.label ?? null,
          onSelect: select,
        }}
      />
      <MapEvidenceList
        timeBasis={state.time_basis}
        filtered={filtered}
        current={current}
        setPage={setPage}
        chosen={chosen}
        select={select}
        onSelectEvidence={onSelectEvidence}
      />
    </section>
  );
}
