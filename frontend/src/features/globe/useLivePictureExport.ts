import { useMemo, useState } from 'react';

import type { LiveEvent } from '@/lib/api/eventSchemas';
import { previewAreaEvidence } from '@/lib/map/areaEvidencePreview';
import type { LocalCollection } from '@/lib/map/geoJsonTypes';
import { livePictureCollection, serialiseLivePicture } from '@/lib/map/livePictureExport';

export type LivePictureFormat = 'geojson' | 'kml';

export interface LivePictureExportState {
  withinArea: boolean;
  setWithinArea: (value: boolean) => void;
  /** Features that the download will contain, after the 5,000 event limit. */
  featureCount: number;
  /** Eligible events before the limit, so a truncated export can say so. */
  eligibleCount: number;
  excludedSourceCount: number;
  canDownload: boolean;
  download: (format: LivePictureFormat) => void;
}

const MEDIA_TYPES: Record<LivePictureFormat, string> = {
  geojson: 'application/geo+json',
  kml: 'application/vnd.google-earth.kml+xml',
};

/** Builds the export once per input change so the panel can show what a download holds. */
export function useLivePictureExport(
  events: readonly LiveEvent[],
  area: LocalCollection | null,
): LivePictureExportState {
  const [withinArea, setWithinArea] = useState(false);
  const boundary = withinArea ? area : null;

  const collection = useMemo(() => {
    let selected = events;
    if (boundary !== null) {
      const preview = previewAreaEvidence(boundary, events, -Infinity, Infinity);
      selected = [...preview.inside, ...preview.approximate];
    }
    return livePictureCollection(selected);
  }, [events, boundary]);

  const featureCount = collection.features.length;
  const download = (format: LivePictureFormat) => {
    if (featureCount === 0) return;
    const blob = new Blob([serialiseLivePicture(collection, format)], {
      type: MEDIA_TYPES[format],
    });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `filtered-live-picture.${format}`;
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 0);
  };

  return {
    withinArea: boundary !== null,
    setWithinArea,
    featureCount,
    eligibleCount: collection.metadata.eligible_count,
    excludedSourceCount: collection.metadata.excluded_sources.length,
    canDownload: featureCount > 0,
    download,
  };
}
