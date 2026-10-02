import { useState } from 'react';
import type { LiveEvent } from '@/lib/api/eventSchemas';
import type { LocalCollection } from '@/lib/map/geoJsonTypes';
import { previewAreaEvidence } from '@/lib/map/areaEvidencePreview';
import { exportLivePicture } from '@/lib/map/livePictureExport';

export function LivePictureExport({
  events,
  area,
}: {
  events: readonly LiveEvent[];
  area: LocalCollection | null;
}) {
  const [withinArea, setWithinArea] = useState(false);
  const download = (format: 'geojson' | 'kml') => {
    let selected = events;
    if (withinArea && area) {
      const preview = previewAreaEvidence(area, events, -Infinity, Infinity);
      selected = [...preview.inside, ...preview.approximate];
    }
    const blob = new Blob([exportLivePicture(selected, format)], {
      type: format === 'geojson' ? 'application/geo+json' : 'application/vnd.google-earth.kml+xml',
    });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `filtered-live-picture.${format}`;
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 0);
  };
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
          checked={withinArea && !!area}
          disabled={!area}
          onChange={(event) => setWithinArea(event.target.checked)}
        />{' '}
        Limit to the research boundary (approximate markers are uncertain area matches)
      </label>
      <div className="map-tool-actions">
        <button type="button" className="map-tool-secondary" onClick={() => download('geojson')}>
          Download live GeoJSON
        </button>
        <button type="button" className="map-tool-secondary" onClick={() => download('kml')}>
          Download live KML
        </button>
      </div>
    </section>
  );
}
