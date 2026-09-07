import type { EvidenceItem } from '@/lib/api/reports';
import type { MapState } from '@/lib/api/mapViews';

export function hasEvidencePoint(item: EvidenceItem): boolean {
  return !item.geometry && hasLegacyEvidencePoint(item);
}
export function hasLegacyEvidencePoint(item: EvidenceItem): boolean {
  return (
    typeof item.lon === 'number' &&
    typeof item.lat === 'number' &&
    Number.isFinite(item.lon) &&
    Number.isFinite(item.lat) &&
    Math.abs(item.lon) <= 180 &&
    Math.abs(item.lat) <= 90 &&
    ['exact', 'city', 'admin1'].includes(item.geo_confidence ?? '')
  );
}
export function evidencePrecision(item: EvidenceItem): string {
  if (item.geometry) return item.geometry.precision;
  if (item.geo_confidence === 'country') return 'Country only, not plotted';
  if (!hasEvidencePoint(item)) return 'Location unavailable or precision unknown';
  return item.geo_confidence === 'exact'
    ? 'Source-reported exact position'
    : `Approximate ${item.geo_confidence === 'city' ? 'city' : 'administrative area'}`;
}
export function publicationDay(item: EvidenceItem): string | null {
  return mapEvidenceDay(item, 'publication');
}
export function mapEvidenceTimestamp(
  item: EvidenceItem,
  basis: MapState['time_basis'],
): string | null {
  const value =
    basis === 'acquisition_or_publication' && item.observation
      ? item.observation.acquired_at
      : item.published_at;
  return value && Number.isFinite(Date.parse(value)) ? value : null;
}
export function mapEvidenceDay(item: EvidenceItem, basis: MapState['time_basis']): string | null {
  const timestamp = mapEvidenceTimestamp(item, basis);
  if (timestamp === null) return null;
  const date = new Date(timestamp);
  return Number.isFinite(date.getTime()) ? date.toISOString().slice(0, 10) : null;
}
