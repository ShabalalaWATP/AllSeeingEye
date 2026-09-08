import proj4 from 'proj4';

import type { CursorPosition } from './MapEngine';

// OS's documented approximate Helmert alternative, without the OSTN15 shift grid:
// https://github.com/OrdnanceSurvey/os-transform#proj4js-alternative
const BNG =
  '+proj=tmerc +lat_0=49 +lon_0=-2 +k=0.9996012717 +x_0=400000 ' +
  '+y_0=-100000 +ellps=airy +towgs84=446.448,-125.157,542.06,0.15,0.247,0.842,-20.489 +units=m +no_defs';
const transform = proj4('EPSG:4326', BNG);
export const BNG_NOTE =
  'Approximate OSGB36 conversion, rounded to 10 m. No OSTN15 correction; not for surveying.';
export const BNG_MIN_ZOOM = 5;

/** National Grid extent, including surrounding water, not a country boundary mask. */
export function toBritishGrid({ lon, lat }: CursorPosition): [number, number] | null {
  if (!Number.isFinite(lon) || !Number.isFinite(lat) || lon < -9 || lon > 2 || lat < 49 || lat > 61)
    return null;
  const [east, north] = transform.forward([lon, lat]);
  return east >= 0 && east < 700000 && north >= 0 && north < 1300000 ? [east, north] : null;
}

export function fromBritishGrid(east: number, north: number): [number, number] {
  const [lon, lat] = transform.inverse([east, north]);
  return [lon, lat];
}

export function formatBritishGrid(position: CursorPosition): string | null {
  const point = toBritishGrid(position);
  if (!point) return null;
  return `BNG ≈ E ${Math.round(point[0] / 10) * 10} N ${Math.round(point[1] / 10) * 10} m`;
}

export interface GridLine {
  path: [number, number][];
  major: boolean;
}

/** Maximum 202 lines/18,602 vertices; no unbounded per-pixel or worldwide grid. */
export function britishGridLines(zoom: number): GridLine[] {
  if (!Number.isFinite(zoom) || zoom < BNG_MIN_ZOOM || zoom > 22) return [];
  const spacing = zoom >= 8 ? 10000 : 100000;
  const lines: GridLine[] = [];
  for (let east = 0; east <= 700000; east += spacing) {
    const path: [number, number][] = [];
    for (let north = 0; north <= 1300000; north += 10000) path.push(fromBritishGrid(east, north));
    lines.push({ path, major: east % 100000 === 0 });
  }
  for (let north = 0; north <= 1300000; north += spacing) {
    const path: [number, number][] = [];
    for (let east = 0; east <= 700000; east += 10000) path.push(fromBritishGrid(east, north));
    lines.push({ path, major: north % 100000 === 0 });
  }
  return lines;
}
