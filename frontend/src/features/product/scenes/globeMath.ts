/**
 * Geometry for the story's dotted globe: the packaged land mask, an even spread of
 * points over the sphere and an orthographic projection. Pure functions only, so the
 * renderer stays thin and the maths is unit tested.
 */
import { LAND_MASK_BASE64, LAND_MASK_COLUMNS, LAND_MASK_ROWS } from './landMask.generated';

export interface GeoPoint {
  lat: number;
  lon: number;
}

export interface SpherePoint extends GeoPoint {
  sinLat: number;
  cosLat: number;
  lonRad: number;
}

export interface Projected {
  x: number;
  y: number;
  /** Cosine of the angle from the view centre: above 0 is on the visible face. */
  depth: number;
}

const DEG = Math.PI / 180;
let decoded: Uint8Array | null = null;

function maskBytes(): Uint8Array {
  if (decoded !== null) return decoded;
  const binary = atob(LAND_MASK_BASE64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i += 1) bytes[i] = binary.charCodeAt(i);
  decoded = bytes;
  return bytes;
}

export function isLand(lat: number, lon: number): boolean {
  const row = Math.min(LAND_MASK_ROWS - 1, Math.max(0, Math.floor(90 - lat)));
  const wrapped = (((lon + 180) % 360) + 360) % 360;
  const column = Math.min(LAND_MASK_COLUMNS - 1, Math.floor(wrapped));
  const index = row * LAND_MASK_COLUMNS + column;
  return (((maskBytes()[index >> 3] ?? 0) >> (index & 7)) & 1) === 1;
}

export function toSphere(point: GeoPoint): SpherePoint {
  const latRad = point.lat * DEG;
  return { ...point, sinLat: Math.sin(latRad), cosLat: Math.cos(latRad), lonRad: point.lon * DEG };
}

/** Points spread evenly over the sphere (a Fibonacci lattice). */
export function fibonacciSphere(count: number): GeoPoint[] {
  const points: GeoPoint[] = [];
  const golden = Math.PI * (3 - Math.sqrt(5));
  for (let i = 0; i < count; i += 1) {
    const y = 1 - (2 * (i + 0.5)) / count;
    const lat = Math.asin(y) / DEG;
    const lon = (((((i * golden) / DEG) % 360) + 360) % 360) - 180;
    points.push({ lat, lon });
  }
  return points;
}

export function landPoints(count: number): SpherePoint[] {
  return fibonacciSphere(count)
    .filter((point) => isLand(point.lat, point.lon))
    .map(toSphere);
}

export interface View {
  /** Centre longitude and latitude of the visible face, in degrees. */
  lon: number;
  lat: number;
  radius: number;
  cx: number;
  cy: number;
}

export function project(point: SpherePoint, view: View): Projected {
  const lat0 = view.lat * DEG;
  const sin0 = Math.sin(lat0);
  const cos0 = Math.cos(lat0);
  const dLon = point.lonRad - view.lon * DEG;
  const cosDLon = Math.cos(dLon);
  return {
    x: view.cx + view.radius * point.cosLat * Math.sin(dLon),
    y: view.cy - view.radius * (cos0 * point.sinLat - sin0 * point.cosLat * cosDLon),
    depth: sin0 * point.sinLat + cos0 * point.cosLat * cosDLon,
  };
}

/** A small deterministic generator, so the illustrative scene is identical every visit. */
export function seededRandom(seed: number): () => number {
  let state = seed >>> 0;
  return () => {
    state = (state + 0x6d2b79f5) >>> 0;
    let t = state;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/** Points along the great circle from a to b, for flight and cable arcs. */
export function greatCircle(a: GeoPoint, b: GeoPoint, steps: number): GeoPoint[] {
  const [la1, lo1, la2, lo2] = [a.lat * DEG, a.lon * DEG, b.lat * DEG, b.lon * DEG];
  const d =
    2 *
    Math.asin(
      Math.sqrt(
        Math.sin((la2 - la1) / 2) ** 2 +
          Math.cos(la1) * Math.cos(la2) * Math.sin((lo2 - lo1) / 2) ** 2,
      ),
    );
  if (d === 0) return [a, b];
  const points: GeoPoint[] = [];
  for (let i = 0; i <= steps; i += 1) {
    const f = i / steps;
    const A = Math.sin((1 - f) * d) / Math.sin(d);
    const B = Math.sin(f * d) / Math.sin(d);
    const x = A * Math.cos(la1) * Math.cos(lo1) + B * Math.cos(la2) * Math.cos(lo2);
    const y = A * Math.cos(la1) * Math.sin(lo1) + B * Math.cos(la2) * Math.sin(lo2);
    const z = A * Math.sin(la1) + B * Math.sin(la2);
    points.push({ lat: Math.atan2(z, Math.hypot(x, y)) / DEG, lon: Math.atan2(y, x) / DEG });
  }
  return points;
}
