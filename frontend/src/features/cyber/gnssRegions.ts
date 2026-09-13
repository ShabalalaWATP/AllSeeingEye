/**
 * Groups aircraft-derived GNSS accuracy cells into named regions for reading, not
 * for attribution. Cells outside every box report as "Elsewhere". Boxes are
 * [west, south, east, north] in degrees; the first matching box wins.
 */
import type { JamCell } from '@/lib/api/aviation';

export interface JamRegion {
  key: string;
  label: string;
  box: readonly [number, number, number, number] | null;
}

const ELSEWHERE: JamRegion = { key: 'elsewhere', label: 'Elsewhere', box: null };

export const JAM_REGIONS: readonly JamRegion[] = [
  { key: 'baltic', label: 'Baltic Sea, Kaliningrad and Baltic states', box: [9, 53, 31, 61] },
  { key: 'black_sea', label: 'Black Sea, Crimea and southern Ukraine', box: [27, 40, 42, 47] },
  { key: 'ukraine', label: 'Ukraine and its border regions', box: [22, 47, 41, 53] },
  { key: 'east_med', label: 'Eastern Mediterranean and Levant', box: [25, 30, 42, 40] },
  { key: 'red_sea', label: 'Red Sea and Horn of Africa', box: [32, 10, 52, 30] },
  { key: 'gulf', label: 'Persian Gulf and Gulf of Oman', box: [44, 22, 62, 32] },
  { key: 'north_sea', label: 'North Sea, UK and Norway', box: [-11, 49, 9, 71] },
  { key: 'russia_west', label: 'Western Russia and Belarus', box: [27, 53, 60, 70] },
  { key: 'central_europe', label: 'Central and southern Europe', box: [-10, 35, 27, 53] },
  { key: 'korea', label: 'Korean Peninsula and Japan', box: [124, 30, 146, 46] },
  { key: 'south_asia', label: 'South Asia and Myanmar', box: [60, 5, 101, 35] },
  ELSEWHERE,
];

export interface JamRegionSummary {
  key: string;
  label: string;
  cells: number;
  red: number;
  amber: number;
  observations: number;
  worstShare: number;
}

export interface JamSummary {
  total: number;
  red: number;
  amber: number;
  observations: number;
  regions: JamRegionSummary[];
  worst: JamCell[];
}

function inBox(cell: JamCell, box: readonly [number, number, number, number]): boolean {
  const [west, south, east, north] = box;
  return cell.lon >= west && cell.lon <= east && cell.lat >= south && cell.lat <= north;
}

export function regionFor(cell: JamCell): JamRegion {
  return JAM_REGIONS.find((region) => region.box && inBox(cell, region.box)) ?? ELSEWHERE;
}

/** Amber and red cells only; green cells are not interference candidates. */
export function summariseJamCells(cells: readonly JamCell[], worstLimit = 6): JamSummary {
  const flagged = cells.filter((cell) => cell.level === 'amber' || cell.level === 'red');
  const byRegion = new Map<string, JamRegionSummary>();
  for (const region of JAM_REGIONS) {
    byRegion.set(region.key, {
      key: region.key,
      label: region.label,
      cells: 0,
      red: 0,
      amber: 0,
      observations: 0,
      worstShare: 0,
    });
  }
  for (const cell of flagged) {
    const row = byRegion.get(regionFor(cell).key);
    if (!row) continue;
    row.cells += 1;
    if (cell.level === 'red') row.red += 1;
    else row.amber += 1;
    row.observations += cell.good + cell.bad;
    row.worstShare = Math.max(row.worstShare, cell.percent_bad);
  }
  const regions = [...byRegion.values()]
    .filter((row) => row.cells > 0)
    .sort((a, b) => b.red - a.red || b.cells - a.cells || a.label.localeCompare(b.label));
  const worst = [...flagged]
    .sort((a, b) => b.percent_bad - a.percent_bad || b.bad - a.bad)
    .slice(0, worstLimit);
  return {
    total: flagged.length,
    red: flagged.filter((cell) => cell.level === 'red').length,
    amber: flagged.filter((cell) => cell.level === 'amber').length,
    observations: flagged.reduce((sum, cell) => sum + cell.good + cell.bad, 0),
    regions,
    worst,
  };
}

export function formatCellPosition(cell: JamCell): string {
  const lat = `${Math.abs(cell.lat).toFixed(1)}°${cell.lat >= 0 ? 'N' : 'S'}`;
  const lon = `${Math.abs(cell.lon).toFixed(1)}°${cell.lon >= 0 ? 'E' : 'W'}`;
  return `${lat} ${lon}`;
}
