import type { Camera } from '@/lib/api/cameras';

// Catalogue arrays are immutable. A weak key lets replaced catalogues and their
// vector buffers be collected together rather than retaining an additional cache.
const cache = new WeakMap<readonly Camera[], Float64Array>();

export function cameraVectors(cameras: readonly Camera[]): Float64Array {
  const existing = cache.get(cameras);
  if (existing) return existing;
  const vectors = new Float64Array(cameras.length * 3);
  const radians = Math.PI / 180;
  cameras.forEach((camera, index) => {
    const lat = camera.latitude * radians;
    const lon = camera.longitude * radians;
    vectors[index * 3] = Math.cos(lat) * Math.cos(lon);
    vectors[index * 3 + 1] = Math.cos(lat) * Math.sin(lon);
    vectors[index * 3 + 2] = Math.sin(lat);
  });
  cache.set(cameras, vectors);
  return vectors;
}
