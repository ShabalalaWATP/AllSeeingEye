/** Shared, bounded display preparation. Original frozen evidence is never rewritten. */
import type { EvidenceItem } from '@/lib/api/reports';
import type { MapState } from '@/lib/api/mapViews';
import type { LocalCollection, LocalOverlay } from '@/lib/map/geoJsonTypes';
import {
  geometryVertices,
  MAX_GEOJSON_BYTES,
  MAX_GEOJSON_FEATURES,
  MAX_GEOJSON_VERTICES,
  parseLocalGeoJson,
} from '@/lib/map/localGeoJson';
import { topologyBudget } from '@/lib/map/geoJsonTopology';

export interface GeometryOmission {
  label: string;
  reason: string;
}
export interface PreparedEvidenceGeometry {
  source: LocalCollection;
  overlays: LocalOverlay[];
  aoi: LocalCollection | null;
  footprints: LocalCollection | null;
  omissions: GeometryOmission[];
  firstOverlay: LocalOverlay | null;
}

export function prepareEvidenceGeometry(
  evidence: readonly EvidenceItem[],
  overlays: MapState['overlays'] = [],
  aoi: unknown = null,
  footprints: LocalCollection | null = null,
  displayTransform: MapState['display_transform'] = 'ase-geojson-display-v2',
): PreparedEvidenceGeometry {
  const result: PreparedEvidenceGeometry = {
    source: { type: 'FeatureCollection', features: [] },
    overlays: [],
    aoi: null,
    footprints: null,
    omissions: [],
    firstOverlay: null,
  };
  const chargeTopology = topologyBudget();
  let bytes = 0,
    features = 0,
    originalVertices = 0,
    displayVertices = 0;
  const prepare = (raw: unknown, label: string, profile: 'annotation' | 'source') => {
    try {
      if (
        bytes >= MAX_GEOJSON_BYTES ||
        features >= MAX_GEOJSON_FEATURES ||
        originalVertices >= MAX_GEOJSON_VERTICES ||
        displayVertices >= MAX_GEOJSON_VERTICES
      )
        throw new Error('The shared map geometry budget was reached.');
      const text = JSON.stringify(raw);
      bytes += new TextEncoder().encode(text).byteLength;
      if (bytes > MAX_GEOJSON_BYTES) throw new Error('The shared map limit of 5 MiB was reached.');
      // Count attempted features before validation so invalid inputs cannot reset admission.
      const count = (raw as LocalCollection).features.length;
      features += count;
      if (features > MAX_GEOJSON_FEATURES)
        throw new Error('The shared map limit of 2,000 features was reached.');
      const parsed = parseLocalGeoJson(text, profile, chargeTopology, () => {
        if (++originalVertices > MAX_GEOJSON_VERTICES)
          throw new Error('The shared map limit of 100,000 vertices was reached.');
      });
      displayVertices += parsed.display.features.reduce(
        (sum, feature) => sum + geometryVertices(feature.geometry),
        0,
      );
      if (originalVertices > MAX_GEOJSON_VERTICES || displayVertices > MAX_GEOJSON_VERTICES)
        throw new Error('The shared map limit of 100,000 vertices was reached.');
      return parsed;
    } catch (error) {
      result.omissions.push({
        label,
        reason: error instanceof Error ? error.message : 'Unsupported source geometry.',
      });
      return null;
    }
  };
  // Give cited source geometry priority over optional display layers.
  for (const item of displayTransform === 'ase-geojson-display-v2' ? evidence : []) {
    if (!item.geometry) continue;
    const parsed = prepare(
      {
        type: 'FeatureCollection',
        features: [
          { type: 'Feature', properties: { label: item.label }, geometry: item.geometry.geometry },
        ],
      },
      item.label,
      'source',
    );
    if (parsed) {
      for (const feature of parsed.display.features)
        result.source.features.push({ ...feature, id: result.source.features.length });
    }
  }
  for (const [index, overlay] of overlays.entries()) {
    if (!overlay.visible) continue;
    const parsed = prepare(
      overlay.geometry,
      `Overlay ${index + 1}: ${overlay.source}`,
      'annotation',
    );
    if (parsed) {
      const displayed: LocalOverlay = {
        ...parsed,
        source: overlay.source,
        datasetDate: overlay.dataset_date,
        attribution: overlay.attribution,
        precision: overlay.precision,
      };
      result.overlays.push(displayed);
      if (index === 0) result.firstOverlay = displayed;
    }
  }
  if (aoi) result.aoi = prepare(aoi, 'Research area', 'annotation')?.display ?? null;
  if (footprints)
    result.footprints =
      prepare(footprints, 'Temporary catalogue footprints', 'source')?.display ?? null;
  return result;
}
