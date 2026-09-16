import { lazy, Suspense, useMemo } from 'react';
import type { SavedMapView } from '@/lib/api/mapViews';
import type { EvidenceItem } from '@/lib/api/reports';
import { matchesMapFilters } from './savedMapState';
import { prepareEvidenceGeometry } from './frozenEvidenceGeometry';
import { MapGeometryOmissions } from './MapGeometryOmissions';
const Canvas = lazy(() => import('./EvidenceMapCanvas'));
const ignore = () => undefined;
export type MapCapture = (signal: AbortSignal) => Promise<Blob>;
export function MapImagePreview({
  saved,
  evidence,
  includeAnnotations,
  onCaptureReady,
}: {
  saved: SavedMapView;
  evidence: readonly EvidenceItem[];
  includeAnnotations: boolean;
  onCaptureReady: (capture: MapCapture | null) => void;
}) {
  const state = saved.revision.state;
  const filtered = useMemo(
    () => evidence.filter((item) => matchesMapFilters(item, state)),
    [evidence, state],
  );
  const prepared = useMemo(
    () =>
      prepareEvidenceGeometry(
        filtered,
        includeAnnotations ? state.overlays : [],
        includeAnnotations ? state.aoi : null,
        null,
        state.display_transform,
      ),
    [filtered, includeAnnotations, state],
  );
  return (
    <section aria-label="Map export preview" className="space-y-2">
      <p className="text-sm">
        Saved revision {saved.revision.number}, report version{' '}
        {saved.revision.report_version_number}.
        {includeAnnotations
          ? ' Includes saved private annotations.'
          : ' Derived redacted view: private overlays, area and measurement omitted.'}{' '}
        Unsaved edits and temporary catalogue footprints are excluded. Frozen evidence locations
        remain included and may still be sensitive.
      </p>
      <p className="text-xs text-muted">
        1200 x 800 pixels. Amber points and outlines show frozen evidence; hollow rings indicate
        approximate positions.
        {includeAnnotations &&
          ' Teal outlines show local overlays, white outlines show the research area and measurement lines show the saved sketch.'}{' '}
        Unsupported geometries are omitted. Flat maps omit polar geometry beyond +/-85.05112878 degrees.
        Country-only and unknown locations are not plotted.
      </p>
      <MapGeometryOmissions omissions={prepared.omissions} />
      <div
        className="overflow-auto rounded border border-line"
        aria-label="Fixed size export viewport"
      >
        <Suspense fallback={<p role="status">Loading map renderer...</p>}>
          <Canvas
            key={`${saved.revision.id}:${includeAnnotations}`}
            captureEnabled
            onCaptureReady={onCaptureReady}
            evidence={filtered}
            sourceGeometry={prepared.source}
            overlays={prepared.overlays}
            aoi={prepared.aoi}
            measurement={includeAnnotations ? state.measurement : null}
            camera={state.camera}
            basemap={state.basemap}
            projection={state.projection}
            legacyDisplay={state.display_transform === 'ase-geojson-display-v1'}
            selected={state.selected_evidence}
            focusRequest={null}
            onCamera={ignore}
            onSelect={ignore}
          />
        </Suspense>
      </div>
    </section>
  );
}
