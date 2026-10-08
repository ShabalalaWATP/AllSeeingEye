import { useId } from 'react';

import type { LiveEvent } from '@/lib/api/eventSchemas';
import type { LocalCollection } from '@/lib/map/geoJsonTypes';

import { useLivePictureExport } from './useLivePictureExport';
import type { LivePictureExportState } from './useLivePictureExport';

function counted(count: number, one: string, many: string): string {
  return `${count.toLocaleString('en-GB')} ${count === 1 ? one : many}`;
}

/** Plain text describing what a download would contain right now. */
export function describeLivePictureExport(
  state: Pick<
    LivePictureExportState,
    'canDownload' | 'featureCount' | 'eligibleCount' | 'excludedSourceCount'
  >,
): string {
  const excluded = `${counted(state.excludedSourceCount, 'source', 'sources')} excluded.`;
  if (!state.canDownload) {
    return `Nothing to export: no eligible USGS earthquake or NASA FIRMS events are loaded with the current filters. ${excluded}`;
  }
  const limited =
    state.eligibleCount > state.featureCount
      ? ` (limited from ${state.eligibleCount.toLocaleString('en-GB')} eligible)`
      : '';
  const features = counted(state.featureCount, 'eligible feature', 'eligible features');
  return `${features} will be exported${limited}. ${excluded}`;
}

export function LivePictureExport({
  events,
  area,
}: {
  events: readonly LiveEvent[];
  area: LocalCollection | null;
}) {
  const state = useLivePictureExport(events, area);
  const summaryId = useId();
  return (
    <section aria-label="Export live map picture" className="map-tool-section">
      <h3 className="map-tool-section-title">Export live map picture</h3>
      <p className="map-tool-help">
        Download up to 5,000 already loaded events after the current map filters. Only reviewed USGS
        earthquake and NASA FIRMS metadata is included. Other sources are listed as excluded in the
        file. Approximate markers keep their precision label.
      </p>
      <label className="map-tool-help">
        <input
          type="checkbox"
          checked={state.withinArea}
          disabled={!area}
          onChange={(event) => state.setWithinArea(event.target.checked)}
        />{' '}
        Limit to the research boundary (approximate markers are uncertain area matches)
      </label>
      <p id={summaryId} className="map-tool-help">
        {describeLivePictureExport(state)}
      </p>
      <div className="map-tool-actions">
        <button
          type="button"
          className="map-tool-secondary"
          disabled={!state.canDownload}
          aria-describedby={summaryId}
          onClick={() => state.download('geojson')}
        >
          Download live GeoJSON
        </button>
        <button
          type="button"
          className="map-tool-secondary"
          disabled={!state.canDownload}
          aria-describedby={summaryId}
          onClick={() => state.download('kml')}
        >
          Download live KML
        </button>
      </div>
    </section>
  );
}
