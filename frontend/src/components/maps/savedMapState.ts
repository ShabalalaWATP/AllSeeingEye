import type { MapState, SavedMapView } from '@/lib/api/mapViews';
import { mapStateSchema } from '@/lib/api/mapViews';
import type { MapCamera } from '@/lib/map/MapEngine';
import type { LocalOverlay } from '@/lib/map/geoJsonTypes';
import { parseLocalGeoJson } from '@/lib/map/localGeoJson';
import type { EvidenceItem } from '@/lib/api/reports';

export const initialMapState = (): MapState =>
  mapStateSchema.parse({ camera: { longitude: 10, latitude: 30, zoom: 1.6 } });
export const toCamera = (state: MapState): MapCamera => ({
  center: [state.camera.longitude, state.camera.latitude],
  zoom: state.camera.zoom,
  bearing: state.camera.bearing,
  pitch: state.camera.pitch,
});
export const fromCamera = (camera: MapCamera): MapState['camera'] => ({
  longitude: camera.center[0],
  latitude: camera.center[1],
  zoom: camera.zoom,
  bearing: camera.bearing,
  pitch: camera.pitch,
});
export function localOverlay(value: MapState['overlays'][number]): LocalOverlay {
  return {
    ...parseLocalGeoJson(JSON.stringify(value.geometry)),
    source: value.source,
    datasetDate: value.dataset_date,
    attribution: value.attribution,
    precision: value.precision,
  };
}
export function savedOverlay(value: LocalOverlay, visible: boolean): MapState['overlays'][number] {
  return {
    geometry: { ...value.canonical },
    source: value.source,
    dataset_date: value.datasetDate,
    attribution: value.attribution,
    precision: value.precision,
    visible,
  };
}
export function mapRevisionLink(saved: Pick<SavedMapView, 'view' | 'revision'>) {
  return `/reports/${encodeURIComponent(saved.view.report_id)}?version=${saved.revision.report_version_number}&map_view=${encodeURIComponent(saved.view.id)}&map_revision=${encodeURIComponent(saved.revision.id)}`;
}
export function matchesMapFilters(item: EvidenceItem, state: MapState) {
  if (state.source_ids.length && !state.source_ids.includes(item.source_id)) return false;
  const published = item.published_at ? Date.parse(item.published_at) : NaN;
  if (!Number.isFinite(published)) return state.include_unknown_dates;
  return (
    (!state.published_since || published >= Date.parse(state.published_since)) &&
    (!state.published_until || published <= Date.parse(state.published_until))
  );
}
