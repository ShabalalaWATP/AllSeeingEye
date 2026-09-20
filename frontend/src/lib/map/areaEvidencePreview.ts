import type { LiveEvent } from '@/lib/api/eventSchemas';
import type { LocalCollection, Position } from './geoJsonTypes';

/** Coordinate-linear containment for validated, antimeridian-split RFC7946 polygons. */
function ringContains(point: Position, ring: Position[]): 'inside' | 'outside' | 'boundary' {
  let inside = false;
  for (let index = 1; index < ring.length; index++) {
    const a = ring[index - 1];
    const b = ring[index];
    if (!a || !b) continue;
    const cross = (b[0] - a[0]) * (point[1] - a[1]) - (b[1] - a[1]) * (point[0] - a[0]);
    if (
      Math.abs(cross) < 1e-10 &&
      point[0] >= Math.min(a[0], b[0]) &&
      point[0] <= Math.max(a[0], b[0]) &&
      point[1] >= Math.min(a[1], b[1]) &&
      point[1] <= Math.max(a[1], b[1])
    )
      return 'boundary';
    if (
      a[1] > point[1] !== b[1] > point[1] &&
      point[0] < ((b[0] - a[0]) * (point[1] - a[1])) / (b[1] - a[1]) + a[0]
    )
      inside = !inside;
  }
  return inside ? 'inside' : 'outside';
}
function polygonContains(point: Position, rings: Position[][]) {
  const outer = rings[0];
  if (!outer || ringContains(point, outer) === 'outside') return false;
  // Polygon boundaries (including hole edges) are included, matching area coverage semantics.
  return !rings.slice(1).some((ring) => ringContains(point, ring) === 'inside');
}
export function areaContainsPoint(area: LocalCollection, point: Position): boolean {
  if (!point.every(Number.isFinite) || Math.abs(point[0]) > 180 || Math.abs(point[1]) > 90)
    return false;
  return area.features.some(({ geometry }) =>
    geometry.type === 'Polygon'
      ? polygonContains(point, geometry.coordinates)
      : geometry.type === 'MultiPolygon' &&
        geometry.coordinates.some((polygon) => polygonContains(point, polygon)),
  );
}

/** A deterministic view of already loaded records, never a coverage or collection claim. */
export function previewAreaEvidence(
  area: LocalCollection,
  events: readonly LiveEvent[],
  since: number,
  until: number,
) {
  const result = {
    inside: [] as LiveEvent[],
    approximate: [] as LiveEvent[],
    approximateOutside: 0,
    outside: 0,
    country: 0,
    unlocated: 0,
    unknownTime: 0,
    outOfPeriod: 0,
  };
  for (const event of events) {
    const time = Date.parse(event.published_at ?? '');
    if (!Number.isFinite(time)) {
      result.unknownTime++;
      continue;
    }
    if (time < since || time >= until) {
      result.outOfPeriod++;
      continue;
    }
    if (event.geo_confidence === 'country') {
      result.country++;
      continue;
    }
    if (
      !event.point ||
      event.geo_confidence === 'none' ||
      !Number.isFinite(event.point.lon) ||
      !Number.isFinite(event.point.lat) ||
      Math.abs(event.point.lon) > 180 ||
      Math.abs(event.point.lat) > 90
    ) {
      result.unlocated++;
      continue;
    }
    const contained = areaContainsPoint(area, [event.point.lon, event.point.lat]);
    if (event.geo_confidence === 'exact') {
      if (contained) result.inside.push(event);
      else result.outside++;
    } else if (contained) result.approximate.push(event);
    else result.approximateOutside++;
  }
  const sort = (left: LiveEvent, right: LiveEvent) =>
    Date.parse(right.published_at ?? '') - Date.parse(left.published_at ?? '') ||
    left.id.localeCompare(right.id);
  result.inside.sort(sort);
  result.approximate.sort(sort);
  return result;
}
