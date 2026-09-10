import type { ResearchPlan } from '@/lib/api/researchPlan';
import type { MapState } from '@/lib/api/mapViews';
import { geometryBounds } from '@/lib/map/geometryBounds';
import { parseLocalGeoJson } from '@/lib/map/localGeoJson';
import { initialMapState } from './savedMapState';

/** Restore the frozen collection boundary, not current map filters or live locations. */
export function researchMapState(
  timeBasis: MapState['time_basis'],
  area?: ResearchPlan['area'],
): MapState {
  const state = { ...initialMapState(), time_basis: timeBasis };
  if (!area) return state;
  try {
    const aoi = parseLocalGeoJson(JSON.stringify(area.geometry)).canonical;
    const geometry = aoi.features[0]?.geometry;
    if (
      aoi.features.length !== 1 ||
      !geometry ||
      !['Polygon', 'MultiPolygon'].includes(geometry.type)
    )
      return state;
    const bounds = geometryBounds(geometry);
    const width =
      bounds.east >= bounds.west ? bounds.east - bounds.west : bounds.east + 360 - bounds.west;
    return {
      ...state,
      aoi: { ...aoi },
      camera: {
        ...state.camera,
        longitude: ((bounds.west + width / 2 + 540) % 360) - 180,
        latitude: (bounds.south + bounds.north) / 2,
        zoom: Math.max(
          0,
          Math.min(12, Math.log2(180 / Math.max(width, bounds.north - bounds.south, 0.01))),
        ),
      },
    };
  } catch {
    // Malformed legacy area metadata must not prevent access to the report's evidence.
    return state;
  }
}
