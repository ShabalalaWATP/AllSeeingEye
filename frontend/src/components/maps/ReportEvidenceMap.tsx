import {
  lazy,
  Suspense,
  useCallback,
  useEffect,
  useMemo,
  useState,
  useSyncExternalStore,
} from 'react';
import type { EvidenceItem } from '@/lib/api/reports';
import { useAuthStore } from '@/stores/auth';
import { subscribeWorkspaceAccess, workspaceRevision } from '@/lib/workspaceAccess';
import { Alert, LoadingNote } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { MapFilters } from './MapFilters';
import { MapEvidenceList } from './MapEvidenceList';
import { MapOverlaySet } from './MapOverlaySet';
import { SavedMapControls } from './SavedMapControls';
import { useSavedMapViews } from './useSavedMapViews';
import { initialMapState, localOverlay, fromCamera, matchesMapFilters } from './savedMapState';
import type { MapState, SavedMapView } from '@/lib/api/mapViews';
import type { MapCamera } from '@/lib/map/MapEngine';
import { FootprintSearchPanel } from './FootprintSearchPanel';
import type { LocalCollection } from '@/lib/map/geoJsonTypes';
import { geometryIsPolar, parseLocalGeoJson } from '@/lib/map/localGeoJson';
import { hasEvidencePoint, publicationDay } from './evidenceGeometry';

const Canvas = lazy(() =>
  import('./EvidenceMapCanvas').catch(() => ({
    default: () => (
      <Alert tone="warning">
        The map renderer could not load. Use the evidence list or reload the page.
      </Alert>
    ),
  })),
);
const PAGE_SIZE = 20;
export interface ReportEvidenceMapProps {
  reportId: string;
  version: number;
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
    () => savedView?.revision.state ?? initialMapState(),
  );
  const saved = useSavedMapViews(reportId, version, savedView);
  const overlays = useMemo(
    () => state.overlays.filter((item) => item.visible).map(localOverlay),
    [state.overlays],
  );
  const aoi = useMemo(
    () => (state.aoi ? parseLocalGeoJson(JSON.stringify(state.aoi)).display : null),
    [state.aoi],
  );
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
  }, []);
  const [opened, setOpened] = useState(false);
  const projection = state.projection;
  const selected = state.selected_evidence;
  const setProjection = (projection: MapState['projection']) =>
    setState((value) => ({ ...value, projection }));
  const [page, setPage] = useState(0);
  const days = useMemo(
    () =>
      [
        ...new Set(evidence.map(publicationDay).filter((value): value is string => value !== null)),
      ].sort(),
    [evidence],
  );
  const sources = useMemo(
    () => [...new Map(evidence.map((item) => [item.source_id, item.source_name])).entries()],
    [evidence],
  );
  const filtered = useMemo(
    () => evidence.filter((item) => matchesMapFilters(item, state)),
    [evidence, state],
  );
  const current = Math.min(page, Math.max(0, Math.ceil(filtered.length / PAGE_SIZE) - 1));
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
  const polar =
    filtered.filter((item) => hasEvidencePoint(item) && Math.abs(item.lat ?? 0) > 85.05112878)
      .length +
    overlays.reduce(
      (sum, overlay) =>
        sum +
        overlay.display.features.filter((feature) => geometryIsPolar(feature.geometry)).length,
      0,
    ) +
    (aoi?.features.filter((feature) => geometryIsPolar(feature.geometry)).length ?? 0) +
    (footprints?.features.filter((feature) => geometryIsPolar(feature.geometry)).length ?? 0);
  return (
    <section
      aria-label="Saved evidence map and timeline"
      className="space-y-4 rounded-md border border-line p-4"
    >
      <header>
        <h2 className="text-lg font-semibold">Map and timeline</h2>
        <p className="mt-1 text-sm text-muted">
          Frozen evidence from version {version}. Publication dates describe reporting time, not
          necessarily when an event happened. Optional catalogue and local overlays remain separate
          from saved evidence.
        </p>
      </header>
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
        {filtered.length} records · {filtered.filter(hasEvidencePoint).length} supported positions.
        Hollow rings are approximate locations, not measured uncertainty areas. Country-only and
        unknown locations remain in the list.
      </p>
      <MapOverlaySet
        overlays={state.overlays}
        onChange={(overlays) =>
          setState((value) => ({
            ...value,
            overlays: typeof overlays === 'function' ? overlays(value.overlays) : overlays,
          }))
        }
      />
      {state.aoi && (
        <p className="text-xs text-muted">
          This revision includes a saved research-area polygon, shown as a reference outline. It
          does not change report evidence or launch collection.
        </p>
      )}
      <FootprintSearchPanel onChange={setFootprints} />
      <SavedMapControls
        saved={saved}
        state={state}
        scopeLabel={scopeLabel}
        canCreate={canCreateView}
        canEdit={!!saved.active && canManageView(saved.active.view)}
        blocked={
          footprints?.features.length
            ? 'Clear the temporary catalogue footprints before saving. Catalogue source-version receipts are not yet captured in saved views.'
            : null
        }
      />
      {!opened ? (
        <div className="space-y-2">
          <p className="text-xs text-muted">
            Opening the map requests public basemap tiles from an external provider, which can
            disclose the viewed area and your network address. Evidence text is not sent to the tile
            provider.
          </p>
          <Button variant="secondary" onClick={() => setOpened(true)}>
            Open evidence map
          </Button>
        </div>
      ) : (
        <>
          <div className="flex flex-wrap gap-2" aria-label="Evidence map projection">
            <Button
              variant="secondary"
              aria-pressed={projection === 'globe'}
              onClick={() => setProjection('globe')}
            >
              Globe
            </Button>
            <Button
              variant="secondary"
              aria-pressed={projection === 'mercator'}
              onClick={() => setProjection('mercator')}
            >
              Flat map
            </Button>
            <Button
              variant="ghost"
              onClick={() => {
                setOpened(false);
                setFocusRequest(null);
              }}
            >
              Close evidence map
            </Button>
          </div>
          {projection === 'mercator' && polar > 0 && (
            <Alert tone="warning">
              {polar} polar records cannot be displayed in Mercator. Use Globe or select them in the
              list; original coordinates are unchanged.
            </Alert>
          )}
          <Suspense fallback={<LoadingNote label="Loading saved evidence map" />}>
            <Canvas
              footprints={footprints}
              overlays={overlays}
              aoi={aoi}
              camera={state.camera}
              onCamera={captureCamera}
              basemap={state.basemap}
              focusRequest={focusRequest}
              evidence={filtered}
              projection={projection}
              selected={chosen?.label ?? null}
              onSelect={select}
            />
          </Suspense>
        </>
      )}
      <MapEvidenceList
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
