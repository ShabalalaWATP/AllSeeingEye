import type { Position } from './geoJsonTypes';
import { measurementPoint } from './measurements';
import { calculateRf } from './rfPlanning';
import type { RfInputs } from './rfPlanning';
import type { RfTerrainProfile } from './rfTerrainTypes';
import { RF_PHYSICAL_REFERENCE, type RfEngineeringSettings } from './rfEngineering';
import { RF_TERRAIN_MAX_PATH_SAMPLES } from './rfTerrainSampling';

export const RF_EFFECTIVE_EARTH_RADIUS_M = (4 / 3) * 6_371_000;

/** Single knife-edge approximation from ITU-R P.526-16 §4.1, not its full terrain methods.
 * https://www.itu.int/rec/R-REC-P.526/en
 */
export function knifeEdgeLossDb(v: number): number {
  if (!Number.isFinite(v)) throw new Error('Knife-edge parameter must be finite.');
  return v <= -0.78 ? 0 : Math.max(0, 6.9 + 20 * Math.log10(Math.hypot(v - 0.1, 1) + v - 0.1));
}

/** Coarse sampled terrain screen with standard k=4/3 curvature and 60% Fresnel clearance.
 * Ground heights remain in the supplied DEM datum; antenna heights are added above ground.
 * Only the most obstructing sampled edge contributes loss. No clutter/multi-edge/ITM model.
 */
export function evaluateRfTerrainProfile(
  input: RfInputs,
  positions: readonly Position[],
  distancesM: readonly number[],
  elevationsM: readonly (number | null)[],
  settings: RfEngineeringSettings = RF_PHYSICAL_REFERENCE,
): RfTerrainProfile {
  if (
    positions.length < 3 ||
    positions.length > RF_TERRAIN_MAX_PATH_SAMPLES ||
    positions.length !== distancesM.length ||
    positions.length !== elevationsM.length
  )
    throw new Error(
      `Terrain profiles require 3 to ${RF_TERRAIN_MAX_PATH_SAMPLES} aligned samples.`,
    );
  positions.forEach((point) => measurementPoint(...point));
  const total = distancesM.at(-1) ?? NaN;
  if (
    !Number.isFinite(total) ||
    total < 1 ||
    total > 200_000 ||
    distancesM[0] !== 0 ||
    distancesM.some(
      (distance, index) =>
        !Number.isFinite(distance) ||
        distance < 0 ||
        (index > 0 && distance <= (distancesM[index - 1] ?? Infinity)),
    )
  )
    throw new Error('Terrain distances must increase from zero over a 1 metre to 200 km path.');
  const free = calculateRf({ ...input, distanceKm: total / 1000 }, settings);
  const wavelength = 299_792_458 / (input.frequencyMHz * 1e6);
  const ground = elevationsM.map((value) =>
    value !== null && Number.isFinite(value) ? value : null,
  );
  const start = ground[0] ?? null,
    end = ground.at(-1) ?? null;
  const points = positions.map((position, index) => {
    const distanceM = distancesM[index] ?? 0;
    const elevationM = ground[index] ?? null;
    const earthBulgeM = (distanceM * (total - distanceM)) / (2 * settings.earthFactor * 6_371_000);
    const obstacleHeightM =
      index === 0 || index === positions.length - 1 ? 0 : settings.obstacleHeightM;
    const rayHeightM =
      start === null || end === null
        ? null
        : start +
          input.transmitHeightM +
          ((end + input.receiveHeightM - start - input.transmitHeightM) * distanceM) / total;
    const clearanceM =
      rayHeightM === null || elevationM === null
        ? null
        : rayHeightM - elevationM - earthBulgeM - obstacleHeightM;
    const fresnel60M = 0.6 * Math.sqrt((wavelength * distanceM * (total - distanceM)) / total);
    return {
      position,
      distanceM,
      elevationM,
      obstacleHeightM,
      earthBulgeM,
      rayHeightM,
      clearanceM,
      fresnel60M,
      fresnelClearanceM: clearanceM === null ? null : clearanceM - fresnel60M,
    };
  });
  const base = {
    distanceKm: total / 1000,
    points,
    freeSpaceLossDb: free.freeSpaceLossDb,
    reserveDb: settings.reserveDb,
  };
  if (ground.some((value) => value === null))
    return {
      ...base,
      status: 'unknown',
      diffractionLossDb: null,
      receivedDbm: null,
      marginDb: null,
      planningMarginDb: null,
      minimumLosClearanceM: null,
      minimumFresnelClearanceM: null,
      obstructionIndex: null,
    };
  let maximumV = -Infinity,
    obstructionIndex: number | null = null;
  let minimumLosClearanceM = Infinity,
    minimumFresnelClearanceM = Infinity;
  for (const [index, point] of points.entries()) {
    if (index === 0 || index === points.length - 1) continue;
    const clearance = point.clearanceM ?? 0;
    minimumLosClearanceM = Math.min(minimumLosClearanceM, clearance);
    minimumFresnelClearanceM = Math.min(minimumFresnelClearanceM, point.fresnelClearanceM ?? 0);
    const v = (-Math.SQRT2 * clearance) / (point.fresnel60M / 0.6);
    if (v > maximumV) {
      maximumV = v;
      obstructionIndex = index;
    }
  }
  const diffractionLossDb = knifeEdgeLossDb(maximumV);
  const receivedDbm = free.receivedDbm - diffractionLossDb;
  const marginDb = receivedDbm - input.sensitivityDbm;
  const planningMarginDb = marginDb - settings.reserveDb;
  const status =
    minimumLosClearanceM <= 0
      ? 'blocked'
      : minimumFresnelClearanceM < 0 || planningMarginDb < 0
        ? 'risk'
        : 'clear';
  return {
    ...base,
    status,
    diffractionLossDb,
    receivedDbm,
    marginDb,
    planningMarginDb,
    minimumLosClearanceM,
    minimumFresnelClearanceM,
    obstructionIndex: diffractionLossDb > 0 ? obstructionIndex : null,
  };
}
