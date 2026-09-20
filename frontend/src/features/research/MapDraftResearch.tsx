import { Link } from 'react-router';
import { useAreaResearchDraft } from '@/lib/areaResearchDraft';
import { MapAreaResearchPanel } from '@/components/maps/MapAreaResearchPanel';
import { Alert } from '@/components/ui/Alert';

/** Geometry stays in scoped memory, never in a query string or browser history. */
export function MapDraftResearch() {
  const handoff = useAreaResearchDraft((state) => state.handoff);
  if (!handoff)
    return (
      <Alert tone="warning">
        This map draft is unavailable after a reload or access change. Reopen an area on the map to
        continue.{' '}
        <Link to="/" className="underline">
          Return to map
        </Link>
      </Alert>
    );
  return (
    <div className="space-y-4">
      <p className="text-sm text-muted">
        Your exact map boundary, question, research depth, source choices, fixed period and report
        preferences have been carried here. Review source support and approve disclosure before
        collection.
      </p>
      <MapAreaResearchPanel
        area={handoff.area}
        areaError={null}
        picking={false}
        onStopDrawing={() => undefined}
        fullPage
        initialPreferences={handoff.preferences}
      >
        <p className="map-tool-help">
          Exact boundary from the map. Coordinates have not been widened to a rectangle.
        </p>
        <Link to="/?tool=research" className="map-tool-text-button">
          Return to the map
        </Link>
      </MapAreaResearchPanel>
    </div>
  );
}
