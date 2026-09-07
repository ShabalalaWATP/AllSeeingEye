import type { EvidenceItem } from '@/lib/api/reports';

export function hasEvidencePoint(item: EvidenceItem): boolean {
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
  if (item.geo_confidence === 'country') return 'Country only, not plotted';
  if (!hasEvidencePoint(item)) return 'Location unavailable or precision unknown';
  return item.geo_confidence === 'exact'
    ? 'Source-reported exact position'
    : `Approximate ${item.geo_confidence === 'city' ? 'city' : 'administrative area'}`;
}
export function publicationDay(item: EvidenceItem): string | null {
  if (item.published_at === null) return null;
  const date = new Date(item.published_at);
  return Number.isFinite(date.getTime()) ? date.toISOString().slice(0, 10) : null;
}
