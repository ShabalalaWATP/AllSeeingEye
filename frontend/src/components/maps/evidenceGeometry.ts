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
  if (basis === 'recorded_time' && item.project) return null;
  const value =
    basis !== 'publication' && item.observation ? item.observation.acquired_at : item.published_at;
  return value && Number.isFinite(Date.parse(value)) ? value : null;
}
export function mapEvidenceDay(item: EvidenceItem, basis: MapState['time_basis']): string | null {
  const timestamp = mapEvidenceTimestamp(item, basis);
  if (timestamp === null) return null;
  const date = new Date(timestamp);
  return Number.isFinite(date.getTime()) ? date.toISOString().slice(0, 10) : null;
}

export function projectYearBounds(item: EvidenceItem): [number, number] | null {
  const year = item.project?.commitment_year;
  if (year == null) return null;
  const start = `${String(year).padStart(4, '0')}-01-01T00:00:00Z`;
  const end = `${String(year + 1).padStart(4, '0')}-01-01T00:00:00Z`;
  return [Date.parse(start), Date.parse(end)];
}

export function mapTimelineDay(item: EvidenceItem, basis: MapState['time_basis']): string | null {
  if (basis === 'recorded_time' && item.project) {
    const year = item.project.commitment_year;
    return year == null ? null : `${String(year).padStart(4, '0')}-12-31`;
  }
  return mapEvidenceDay(item, basis);
}

export function mapEvidenceDateLabel(item: EvidenceItem, basis: MapState['time_basis']): string {
  if (basis === 'recorded_time' && item.project) {
    const year = item.project.commitment_year;
    return year == null ? 'Commitment year unknown' : `Commitment year ${year}, exact date unknown`;
  }
  const kind = basis !== 'publication' && item.observation ? 'Acquired' : 'Published';
  return `${kind} ${mapEvidenceDay(item, basis) ?? 'date unknown'}`;
}
