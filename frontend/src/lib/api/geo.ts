import { apiCall } from './client';
import { countriesResponseSchema } from './geoSchemas';
import type { Country } from './geoSchemas';

export async function fetchCountries(): Promise<Country[]> {
  const page = await apiCall('/api/countries', { schema: countriesResponseSchema });
  return page.items;
}

const MIN_ZOOM = 1;
const MAX_ZOOM = 6;

/** A zoom that fits the bounds in a typical viewport; large nations stay on the globe. */
export function zoomForBounds(bounds: Country['bounds']): number {
  const [west, south, east, north] = bounds;
  const span = Math.max(east - west, (north - south) * 1.5, 1);
  return Math.max(MIN_ZOOM, Math.min(MAX_ZOOM, Math.floor(Math.log2(360 / span))));
}
