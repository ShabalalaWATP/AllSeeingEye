import type { Camera } from '@/lib/api/cameras';
import type { MapBounds } from '@/lib/map/MapEngine';
import { cameraVectors } from './cameraVectors';

export interface CameraCluster {
  id: string;
  longitude: number;
  latitude: number;
  count: number;
}
interface Cell {
  first: Camera;
  count: number;
  x: number;
  y: number;
  z: number;
}
export const CAMERA_MARKER_BUDGET = 2000;

function inBounds(camera: Camera, bounds: MapBounds | null): boolean {
  if (!bounds) return true;
  if (camera.latitude < bounds.south || camera.latitude > bounds.north) return false;
  if (bounds.east - bounds.west >= 360) return true;
  const span = (((bounds.east - bounds.west) % 360) + 360) % 360;
  const offset = (((camera.longitude - bounds.west) % 360) + 360) % 360;
  return offset <= span;
}

/** Spherical bins preserve date-line and polar coverage. Every record contributes,
 * with wider bins when needed instead of discarding geographically ordered rows. */
export function clusterCameras(
  cameras: readonly Camera[],
  zoom: number,
  selectedId: string | null,
  bounds: MapBounds | null = null,
) {
  const radians = Math.PI / 180;
  const selected =
    selectedId === null ? undefined : cameras.find((camera) => camera.id === selectedId);
  const vectors = cameraVectors(cameras);
  const indices: number[] = [];
  cameras.forEach((camera, index) => {
    if (camera.id !== selectedId && inBounds(camera, bounds)) indices.push(index);
  });
  let degrees = Math.max(0.002, 24 / 2 ** Math.max(0, Math.min(16, zoom)));
  let cells = new Map<number, Cell>();
  do {
    cells = new Map();
    const step = 2 * Math.sin((degrees * radians) / 2);
    // Smallest supported cell is 0.002 degrees. Three shifted unit-vector
    // coordinates therefore pack below 2^48, safely inside exact JS integers.
    // Numeric keys avoid allocating 75,000 coordinate strings on every settled pan.
    const offset = Math.ceil(1 / step);
    const width = 2 * offset + 1;
    for (const index of indices) {
      const camera = cameras[index];
      if (!camera) continue;
      const x = vectors[index * 3] ?? 0;
      const y = vectors[index * 3 + 1] ?? 0;
      const z = vectors[index * 3 + 2] ?? 0;
      const key =
        ((Math.round(x / step) + offset) * width + Math.round(y / step) + offset) * width +
        Math.round(z / step) +
        offset;
      const cell = cells.get(key) ?? { first: camera, count: 0, x: 0, y: 0, z: 0 };
      cell.count++;
      cell.x += x;
      cell.y += y;
      cell.z += z;
      cells.set(key, cell);
      // Occupied-cell count only increases within a pass. Once over budget,
      // examining the other cameras cannot make this resolution usable.
      // Restart coarser immediately; the accepted final pass still visits all rows.
      if (cells.size > CAMERA_MARKER_BUDGET - (selected ? 1 : 0)) break;
    }
    degrees = Math.min(90, degrees * 2);
  } while (cells.size > CAMERA_MARKER_BUDGET - (selected ? 1 : 0));
  const loose: Camera[] = selected ? [selected] : [];
  const clusters: CameraCluster[] = [];
  for (const [id, cell] of cells) {
    if (cell.count === 1) {
      loose.push(cell.first);
      continue;
    }
    const horizontal = Math.hypot(cell.x, cell.y);
    clusters.push({
      id: String(id),
      count: cell.count,
      longitude: horizontal / cell.count < 1e-12 ? 0 : Math.atan2(cell.y, cell.x) / radians,
      latitude: Math.atan2(cell.z, horizontal) / radians,
    });
  }
  return { loose, clusters };
}
