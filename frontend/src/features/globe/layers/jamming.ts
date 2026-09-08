/**
 * The GNSS interference layer: one translucent square per cell where aircraft report poor
 * position accuracy, amber for a modest share and red for a large one.
 */
import { SolidPolygonLayer } from '@deck.gl/layers';
import type { Layer } from '@deck.gl/core';

import type { JamCell } from '@/lib/api/aviation';

const AMBER: [number, number, number, number] = [245, 181, 63, 90];
const RED: [number, number, number, number] = [255, 90, 90, 110];

/** The cell's outline as a closed ring, lon and lat. */
export function cellPolygon(cell: JamCell): [number, number][] {
  const half = cell.size / 2;
  return [
    [cell.lon - half, cell.lat - half],
    [cell.lon + half, cell.lat - half],
    [cell.lon + half, cell.lat + half],
    [cell.lon - half, cell.lat + half],
    [cell.lon - half, cell.lat - half],
  ];
}

/** Only amber and red cells are drawn; green cells would cover the sky in noise. */
export function buildJamLayer(
  cells: readonly JamCell[],
  onPick?: (cell: JamCell) => void,
): Layer | null {
  const flagged = cells.filter((cell) => cell.level !== 'green');
  if (flagged.length === 0) return null;
  return new SolidPolygonLayer<JamCell>({
    id: 'gnss-interference',
    data: flagged,
    pickable: onPick !== undefined,
    onClick: (info: { object?: JamCell }) => {
      if (info.object) onPick?.(info.object);
      return true;
    },
    getPolygon: (cell) => cellPolygon(cell),
    getFillColor: (cell) => (cell.level === 'red' ? RED : AMBER),
  });
}
