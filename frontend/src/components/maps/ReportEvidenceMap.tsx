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
import { SelectField } from '@/components/ui/Field';
import { FootprintSearchPanel } from './FootprintSearchPanel';
import { LocalGeoJsonOverlay } from './LocalGeoJsonOverlay';
import type { LocalCollection, LocalOverlay } from '@/lib/map/geoJsonTypes';
import { geometryIsPolar } from '@/lib/map/localGeoJson';
import { evidencePrecision, hasEvidencePoint, publicationDay } from './evidenceGeometry';

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
}
/** Authorised frozen evidence only: no shared event store or live stream. */
export default function ReportEvidenceMap({
  reportId,
  version,
  evidence,
  onSelectEvidence,
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
  const [overlay, setOverlay] = useState<LocalOverlay | null>(null);
  const [overlayVisible, setOverlayVisible] = useState(true);
  useEffect(() => {
    const clear = () => {
      setOverlay(null);
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
  const [projection, setProjection] = useState<'globe' | 'mercator'>('globe');
  const [source, setSource] = useState('');
  const [day, setDay] = useState('');
  const [selected, setSelected] = useState<string | null>(null);
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
    () =>
      evidence.filter(
        (item) =>
          (!source || item.source_id === source) &&
          (!day || (publicationDay(item) !== null && (publicationDay(item) ?? '') <= day)),
      ),
    [evidence, source, day],
  );
  const current = Math.min(page, Math.max(0, Math.ceil(filtered.length / PAGE_SIZE) - 1));
  const chosen = filtered.find((item) => item.label === selected);
  const select = useCallback((label: string) => {
    setSelected(label);
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
    (overlayVisible
      ? (overlay?.display.features.filter((feature) => geometryIsPolar(feature.geometry)).length ??
        0)
      : 0) +
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
      <div className="grid gap-3 sm:grid-cols-2">
        <SelectField
          label="Publication timeline (UTC)"
          value={day}
          onChange={(event) => {
            setDay(event.target.value);
            setPage(0);
          }}
          options={[
            { value: '', label: 'All publication dates' },
            ...days.map((value) => ({ value, label: `Published through ${value}` })),
          ]}
        />
        <SelectField
          label="Evidence source"
          value={source}
          onChange={(event) => {
            setSource(event.target.value);
            setPage(0);
          }}
          options={[
            { value: '', label: 'All sources' },
            ...sources.map(([value, label]) => ({ value, label })),
          ]}
        />
      </div>
      <p className="text-xs text-muted">
        {filtered.length} records · {filtered.filter(hasEvidencePoint).length} supported positions.
        Hollow rings are approximate locations, not measured uncertainty areas. Country-only and
        unknown locations remain in the list.
      </p>
      {day && (
        <p className="text-xs text-muted">
          Records without a valid publication date are excluded from this date filter. Choose All
          publication dates to inspect them.
        </p>
      )}
      <LocalGeoJsonOverlay
        overlay={overlay}
        visible={overlayVisible}
        onChange={setOverlay}
        onVisible={setOverlayVisible}
      />
      <FootprintSearchPanel onChange={setFootprints} />
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
            <Button variant="ghost" onClick={() => setOpened(false)}>
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
              overlay={overlayVisible ? overlay : null}
              evidence={filtered}
              projection={projection}
              selected={chosen?.label ?? null}
              onSelect={select}
            />
          </Suspense>
        </>
      )}
      {filtered.length === 0 ? (
        <p>No saved evidence matches these filters.</p>
      ) : (
        <ul aria-label="Map evidence" className="grid gap-2 sm:grid-cols-2">
          {filtered.slice(current * PAGE_SIZE, (current + 1) * PAGE_SIZE).map((item) => (
            <li key={item.label}>
              <button
                type="button"
                aria-pressed={chosen?.label === item.label}
                onClick={() => select(item.label)}
                className="min-h-11 w-full rounded border border-line p-3 text-left text-sm hover:bg-surface-2 focus-visible:outline-2 focus-visible:outline-ember"
              >
                <span className="font-medium">
                  {item.label}: {item.title}
                </span>
                <span className="mt-1 block text-xs text-muted">
                  {publicationDay(item) ?? 'Publication date unknown'} · {evidencePrecision(item)}
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
      {filtered.length > PAGE_SIZE && (
        <nav aria-label="Map evidence pages" className="flex items-center gap-3">
          <Button variant="secondary" disabled={current === 0} onClick={() => setPage(current - 1)}>
            Previous
          </Button>
          <span>
            {current + 1} / {Math.ceil(filtered.length / PAGE_SIZE)}
          </span>
          <Button
            variant="secondary"
            disabled={(current + 1) * PAGE_SIZE >= filtered.length}
            onClick={() => setPage(current + 1)}
          >
            Next
          </Button>
        </nav>
      )}
      {chosen && (
        <aside aria-label="Selected map evidence" className="space-y-2 border-t border-line pt-3">
          <h3 className="font-medium">
            {chosen.label}: {chosen.title}
          </h3>
          <p className="text-sm">{chosen.summary ?? 'No saved excerpt available.'}</p>
          <p className="text-xs text-muted">
            {chosen.source_name} · Grade {chosen.grade} · {evidencePrecision(chosen)}
          </p>
          {onSelectEvidence && (
            <Button variant="secondary" onClick={() => onSelectEvidence(chosen.label)}>
              Inspect citation {chosen.label}
            </Button>
          )}
        </aside>
      )}
    </section>
  );
}
