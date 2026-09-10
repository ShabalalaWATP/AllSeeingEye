import type { TerrainElevations } from '@/lib/api/terrain';
import type { Position } from './geoJsonTypes';

export const RF_TERRAIN_CACHE_TTL_MS = 5 * 60 * 1000;
const MAX_BATCHES = 2;
interface CachedBatch {
  elevations: TerrainElevations;
  expiresAt: number;
}

/** Exact geometry only: a changed radio can reuse DEM, a changed site cannot borrow it. */
export class RfElevationCache {
  private readonly batches = new Map<string, CachedBatch>();

  constructor(private readonly now: () => number = Date.now) {}

  clear(): void {
    this.batches.clear();
  }

  get(positions: readonly Position[]): TerrainElevations | null {
    const key = JSON.stringify(positions);
    const cached = this.batches.get(key);
    if (!cached) return null;
    if (cached.expiresAt <= this.now()) {
      this.batches.delete(key);
      return null;
    }
    // Promote for eviction, retaining the original expiry and observation metadata.
    this.batches.delete(key);
    this.batches.set(key, cached);
    return cached.elevations;
  }

  put(positions: readonly Position[], elevations: TerrainElevations): void {
    if (
      positions.length < 1 ||
      positions.length > 1000 ||
      elevations.elevations_m.length !== positions.length ||
      elevations.elevations_m.some((height) => !Number.isFinite(height))
    )
      throw new Error('Terrain cache requires a complete finite sample batch.');
    const key = JSON.stringify(positions);
    this.batches.delete(key);
    this.batches.set(key, { elevations, expiresAt: this.now() + RF_TERRAIN_CACHE_TTL_MS });
    while (this.batches.size > MAX_BATCHES) {
      const oldest = this.batches.keys().next().value;
      if (oldest === undefined) break;
      this.batches.delete(oldest);
    }
  }
}
