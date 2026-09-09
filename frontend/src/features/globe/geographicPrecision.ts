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
  if (locationQuality(event) === 'propagated')
    return 'Propagated orbital estimate, not an observed position';
  if (event.geo_confidence === 'country') return 'Country only, no incident position';
  if (!isMappedEvent(event)) return 'Location unavailable or precision unknown';
  if (event.geo_confidence === 'city') return 'Approximate city location';
  if (event.geo_confidence === 'admin1') return 'Approximate administrative area';
  return 'Source-reported exact position, not independently verified';
}

export type LocationQuality = 'reported' | 'approximate' | 'propagated' | 'unplotted';
export type LocationQualityFilter = 'all' | LocationQuality;

export const QUALITY_LABELS: Record<LocationQualityFilter, string> = {
  all: 'All location qualities',
  reported: 'Source-reported exact',
  approximate: 'Approximate',
  propagated: 'Propagated satellite',
  unplotted: 'Not plotted',
};

/** Geometry validity wins over a subtype: unknown locations never acquire a marker. */
export function locationQuality(event: LiveEvent): LocationQuality {
  if (!isMappedEvent(event)) return 'unplotted';
  if (
    event.category === 'space' &&
    (['satellite', 'satellite_position'].includes(event.subtype) ||
      event.attributes.position_kind === 'propagated')
  )
    return 'propagated';
  return event.geo_confidence === 'exact' ? 'reported' : 'approximate';
}
