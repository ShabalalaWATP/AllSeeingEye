import type { TerrainElevations } from '@/lib/api/terrain';
import type { Position } from './geoJsonTypes';
import type { RfTerrainSamplePlan } from './rfTerrainTypes';

interface TerrainBatch {
  plan: RfTerrainSamplePlan;
  elevations: TerrainElevations;
}
interface Sample {
  distanceM: number;
  position: Position;
  heightM: number;
}
const TOLERANCE_M = 0.000001;
const sourceKey = (source: { provider: string; zoom: number; attribution_url: string }) =>
  JSON.stringify([source.provider, source.zoom, source.attribution_url]);

/** Preserve both passes' sampled evidence within the final radius, without new DEM work. */
export function mergeRfTerrainSamples(first: TerrainBatch, second: TerrainBatch): TerrainBatch {
  if (
    first.plan.kind !== 'radial' ||
    second.plan.kind !== 'radial' ||
    JSON.stringify(first.plan.origin) !== JSON.stringify(second.plan.origin) ||
    first.plan.profiles.length !== second.plan.profiles.length ||
    sourceKey(first.elevations) !== sourceKey(second.elevations) ||
    first.elevations.elevations_m.length !== first.plan.positions.length ||
    second.elevations.elevations_m.length !== second.plan.positions.length
  )
    throw new Error('Terrain passes do not share a compatible sampling source.');
  const originHeight = first.elevations.elevations_m[0];
  const secondOriginHeight = second.elevations.elevations_m[0];
  if (
    originHeight === undefined ||
    secondOriginHeight === undefined ||
    !Number.isFinite(originHeight) ||
    !Number.isFinite(secondOriginHeight) ||
    Math.abs(originHeight - secondOriginHeight) > TOLERANCE_M
  )
    throw new Error('Terrain passes disagree about transmitter elevation.');
  const positions: Position[] = [first.plan.origin];
  const heights = [originHeight];
  const limitM = second.plan.maxDistanceKm * 1000;
  const profiles = second.plan.profiles.map((profile) => {
    const earlier = first.plan.profiles.find(
      (item) => item.bearingDegrees === profile.bearingDegrees,
    );
    if (!earlier) throw new Error('Terrain passes have different sampled bearings.');
    const samples: Sample[] = [];
    for (const [batch, line] of [
      [first, earlier],
      [second, profile],
    ] as const) {
      for (let offset = 1; offset < line.indices.length; offset++) {
        const index = line.indices[offset];
        const distanceM = line.distancesM[offset];
        if (index === undefined || distanceM === undefined)
          throw new Error('Terrain pass contains incomplete sample indices.');
        if (distanceM > limitM + TOLERANCE_M) continue;
        const position = batch.plan.positions[index];
        const heightM = batch.elevations.elevations_m[index];
        if (!position || heightM === undefined || !Number.isFinite(heightM))
          throw new Error('Terrain pass contains missing sample heights.');
        samples.push({ distanceM: Math.min(distanceM, limitM), position, heightM });
      }
    }
    samples.sort((a, b) => a.distanceM - b.distanceM);
    const unique: Sample[] = [];
    for (const sample of samples) {
      const previous = unique.at(-1);
      if (previous && Math.abs(previous.distanceM - sample.distanceM) <= TOLERANCE_M) {
        // Every radial point can later become a receiver site. A higher conflicting
        // elevation is not always conservative, so retain the first screen instead.
        if (Math.abs(previous.heightM - sample.heightM) > TOLERANCE_M)
          throw new Error('Terrain passes disagree about a repeated sample elevation.');
      } else unique.push(sample);
    }
    const indices = [0],
      distancesM = [0];
    for (const sample of unique) {
      indices.push(positions.length);
      distancesM.push(sample.distanceM);
      positions.push(sample.position);
      heights.push(sample.heightM);
    }
    return { bearingDegrees: profile.bearingDegrees, indices, distancesM };
  });
  if (positions.length > 817 || profiles.some((profile) => profile.indices.length > 35))
    throw new Error('Combined terrain evidence exceeds the two-pass budget.');
  return {
    plan: { ...second.plan, positions, profiles },
    elevations: {
      ...second.elevations,
      elevations_m: heights,
      attribution: [...new Set([first.elevations.attribution, second.elevations.attribution])].join(
        ' ',
      ),
      resolution_m: Math.max(first.elevations.resolution_m, second.elevations.resolution_m),
      limitations: [...new Set([first.elevations.limitations, second.elevations.limitations])].join(
        ' ',
      ),
    },
  };
}
