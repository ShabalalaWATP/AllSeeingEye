/** Explicit WGS84 rectangles. Coordinates describe bounds, not measured ground accuracy. */
import type { MapBounds } from './MapEngine';
import type { LocalCollection, Position } from './geoJsonTypes';
import { parseLocalGeoJson } from './localGeoJson';

/** Compare canonical geometry rather than JSON key order returned by different serializers. */
export function areasEqual(first: object | null, second: object | null): boolean {
  if (first === second) return true;
  if (first === null || second === null) return false;
  const canonical = (value: object) =>
    JSON.stringify(parseLocalGeoJson(JSON.stringify(value)).canonical);
  return canonical(first) === canonical(second);
}

export function validateAreaBounds(bounds: MapBounds): MapBounds {
  for (const key of ['west', 'east', 'south', 'north'] as const) {
    const limit = key === 'west' || key === 'east' ? 180 : 90;
    if (!Number.isFinite(bounds[key]) || Math.abs(bounds[key]) > limit)
      throw new Error(`${key} must be a finite WGS84 coordinate between -${limit} and ${limit}.`);
  }
  const width =
    bounds.east >= bounds.west ? bounds.east - bounds.west : 360 - bounds.west + bounds.east;
  if (width <= 0 || bounds.north <= bounds.south)
    throw new Error(
      'Choose a non-zero rectangle with north greater than south and distinct east/west bounds.',
    );
  return { ...bounds };
}

function ring(west: number, east: number, south: number, north: number): Position[] {
  // Split long horizontal edges while retaining the whole specified longitude interval.
  const middle = east - west > 180 ? [(west + east) / 2] : [];
  return [
    [west, south],
    ...middle.map((lon) => [lon, south] as Position),
    [east, south],
    [east, north],
    ...middle.map((lon) => [lon, north] as Position),
    [west, north],
    [west, south],
  ];
}

export function rectangleArea(input: MapBounds): LocalCollection {
  const { west, east, south, north } = validateAreaBounds(input);
  const segments =
    west > east
      ? [
          [west, 180],
          [-180, east],
        ]
      : [[west, east]];
  const polygons = segments
    .filter(([left, right]) => left !== right)
    .map(([left, right]) => [ring(left ?? NaN, right ?? NaN, south, north)]);
  const geometry =
    polygons.length === 1
      ? { type: 'Polygon', coordinates: polygons[0] }
      : { type: 'MultiPolygon', coordinates: polygons };
  return parseLocalGeoJson(
    JSON.stringify({
      type: 'FeatureCollection',
      features: [
        {
          type: 'Feature',
          properties: { label: 'Selected area' },
          geometry,
        },
      ],
    }),
  ).canonical;
}

/** Two corners choose the shorter longitude span; keyboard bounds can select the wider span. */
export function boundsFromCorners(first: Position, second: Position): MapBounds {
  const west = Math.min(first[0], second[0]),
    east = Math.max(first[0], second[0]);
  return validateAreaBounds({
    west: east - west > 180 ? east : west,
    east: east - west > 180 ? west : east,
    south: Math.min(first[1], second[1]),
    north: Math.max(first[1], second[1]),
  });
}

export function areaClickPoint(event: unknown): Position | null {
  if (typeof event !== 'object' || event === null || !('lngLat' in event)) return null;
  const value = event.lngLat;
  if (typeof value !== 'object' || value === null || !('lng' in value) || !('lat' in value))
    return null;
  if (
    typeof value.lng !== 'number' ||
    typeof value.lat !== 'number' ||
    !Number.isFinite(value.lng) ||
    !Number.isFinite(value.lat) ||
    Math.abs(value.lat) > 90
  )
    return null;
  return [(((value.lng % 360) + 540) % 360) - 180, value.lat];
}
