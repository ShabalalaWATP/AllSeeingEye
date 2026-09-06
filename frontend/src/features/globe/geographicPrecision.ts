import type { LiveEvent } from '@/lib/api/eventSchemas';

/** Country centres and unknown-precision points never represent mapped incidents. */
export function isMappedEvent(event: LiveEvent): boolean {
  const point = event.point;
  return (
    point !== null &&
    Number.isFinite(point.lon) &&
    Number.isFinite(point.lat) &&
    Math.abs(point.lon) <= 180 &&
    Math.abs(point.lat) <= 90 &&
    ['exact', 'city', 'admin1'].includes(event.geo_confidence)
  );
}

export function precisionLabel(event: LiveEvent): string {
  if (event.geo_confidence === 'country') return 'Country only, no incident position';
  if (!isMappedEvent(event)) return 'Location unavailable or precision unknown';
  if (event.geo_confidence === 'city') return 'Approximate city location';
  if (event.geo_confidence === 'admin1') return 'Approximate administrative area';
  return 'Source-reported exact position, not independently verified';
}
