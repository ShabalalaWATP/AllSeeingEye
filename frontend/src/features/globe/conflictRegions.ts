import type { ConflictCard } from '@/lib/api/trackers';
import type { Position } from '@/lib/map/geoJsonTypes';

export type RegionStatus = 'all' | 'war' | 'tension';
export interface ConflictRegion {
  card: ConflictCard;
  centre: Position;
  bounds: [number, number, number, number];
}
export function conflictRegions(cards: readonly ConflictCard[]): ConflictRegion[] {
  return cards.slice(0, 100).flatMap((card) => {
    const [west, south, east, north] = card.conflict.bbox;
    if (
      !['war', 'tension'].includes(card.conflict.status) ||
      west === undefined ||
      south === undefined ||
      east === undefined ||
      north === undefined ||
      ![west, south, east, north].every(Number.isFinite) ||
      west < -180 ||
      east > 180 ||
      south < -85 ||
      north > 85 ||
      west >= east ||
      south >= north
    )
      return [];
    return [
      {
        card,
        centre: [(west + east) / 2, (south + north) / 2] as Position,
        bounds: [west, south, east, north] as [number, number, number, number],
      },
    ];
  });
}
export function filterConflictRegions(
  regions: ConflictRegion[],
  query: string,
  status: RegionStatus,
  country: string | null,
) {
  const words = query.trim().toLowerCase().split(/\s+/).filter(Boolean);
  return regions.filter(
    ({ card: { conflict } }) =>
      (status === 'all' || conflict.status === status) &&
      (!country || conflict.countries.includes(country)) &&
      words.every((word) =>
        `${conflict.name} ${conflict.countries.join(' ')} ${conflict.belligerents.join(' ')}`
          .toLowerCase()
          .includes(word),
      ),
  );
}
export function regionLabel(region: ConflictRegion): string {
  return region.card.conflict.status === 'war' ? 'War region (curated)' : 'Tension area (curated)';
}
