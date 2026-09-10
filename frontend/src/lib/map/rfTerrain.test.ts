import { expect, it } from 'vitest';
import { Geodesic } from 'geographiclib-geodesic';
import { analyseRfTerrain } from './rfTerrainAnalysis';
import { rfTerrainLayers } from './rfTerrainLayers';
import {
  evaluateRfTerrainProfile,
  knifeEdgeLossDb,
  RF_EFFECTIVE_EARTH_RADIUS_M,
} from './rfTerrainProfile';
import { createRfTerrainPath, createRfTerrainRadials } from './rfTerrainSampling';
import { DEFAULT_RF_INPUTS } from './rfPlanning';
import type { Position } from './geoJsonTypes';

const powerful = {
  ...DEFAULT_RF_INPUTS,
  transmitHeightM: 100,
  receiveHeightM: 100,
  transmitDbm: 40,
  sensitivityDbm: -120,
};
const profilePoints: Position[] = [
  [0, 0],
  [0.005, 0],
  [0.01, 0],
];
const distances = [0, 500, 1000];

it('bounds geodesic sampling and shares a single radial origin', () => {
  const path = createRfTerrainPath([0, 51], [1, 51]);
  const expected = Geodesic.WGS84.Inverse(51, 0, 51, 1).s12 ?? 0;
  expect(path.positions).toHaveLength(Math.ceil(expected / 100) + 1);
  expect(path.positions[0]).toEqual([0, 51]);
  expect(path.positions.at(-1)).toEqual([1, 51]);
  expect(path.profiles[0]?.distancesM[1]).toBeCloseTo(expected / (path.positions.length - 1), 6);
  const radial = createRfTerrainRadials([0, 51], 50);
  expect(radial.positions).toHaveLength(409);
  expect(radial.profiles).toHaveLength(24);
  expect(
    radial.profiles.every((profile) => profile.indices[0] === 0 && profile.indices.length === 18),
  ).toBe(true);
  const end = radial.positions.at(-1)!;
  expect(Geodesic.WGS84.Inverse(51, 0, end[1], end[0]).s12).toBeCloseTo(50_000, 4);
});

it('wraps dateline samples and rejects excessive work or unsupported coordinates', () => {
  const path = createRfTerrainPath([179.9, 0], [-179.9, 0], 5);
  expect(path.maxDistanceKm).toBeLessThan(30);
  expect(path.positions.every(([lon]) => lon >= -180 && lon <= 180)).toBe(true);
  expect(() => createRfTerrainPath([0, 0], [10, 0])).toThrow(/200 km/);
  expect(() => createRfTerrainPath([0, 0], [0, 0])).toThrow(/1 metre/);
  expect(() => createRfTerrainPath([0, 0], [0.1, 0], 770)).toThrow(/samples/);
  expect(() => createRfTerrainRadials([0, 0], 51)).toThrow(/50 km/);
  expect(() => createRfTerrainRadials([0, 0], 10, 25)).toThrow(/bearings/);
  expect(() => createRfTerrainRadials([0, 0], 10, 24, 18)).toThrow(/steps/);
  expect(() => createRfTerrainRadials([0, 86], 10)).toThrow(/latitude/);
  expect(() => createRfTerrainRadials([0, 84], 50)).toThrow(/64 tiles/);
});

it('uses MSL ground plus AGL antenna heights, k=4/3 curvature and Fresnel clearance', () => {
  const result = evaluateRfTerrainProfile(
    { ...powerful, transmitHeightM: 20, receiveHeightM: 20 },
    profilePoints,
    distances,
    [100, 100, 100],
  );
  expect(result.status).toBe('clear');
  expect(result.points[1]?.rayHeightM).toBe(120);
  expect(result.points[1]?.earthBulgeM).toBeCloseTo(
    (500 * 500) / (2 * RF_EFFECTIVE_EARTH_RADIUS_M),
    8,
  );
  expect(result.minimumLosClearanceM).toBeCloseTo(
    20 - (500 * 500) / (2 * RF_EFFECTIVE_EARTH_RADIUS_M),
    8,
  );
  expect(result.points[1]?.fresnel60M).toBeCloseTo(0.6 * Math.sqrt((299792458 / 900e6) * 250), 8);
  expect(result.diffractionLossDb).toBe(0);
  expect(result.obstructionIndex).toBeNull();
  expect(result.marginDb).toBeGreaterThan(0);
});

it('distinguishes obstruction, Fresnel restriction and insufficient received power', () => {
  const low = { ...powerful, transmitHeightM: 5, receiveHeightM: 5 };
  const restricted = evaluateRfTerrainProfile(low, profilePoints, distances, [0, 0, 0]);
  expect(restricted.status).toBe('risk');
  expect(restricted.minimumLosClearanceM).toBeGreaterThan(0);
  expect(restricted.minimumFresnelClearanceM).toBeLessThan(0);
  const blocked = evaluateRfTerrainProfile(low, profilePoints, distances, [0, 30, 0]);
  expect(blocked.status).toBe('blocked');
  expect(blocked.diffractionLossDb).toBeGreaterThan(6);
  expect(blocked.obstructionIndex).toBe(1);
  const weak = evaluateRfTerrainProfile(
    { ...powerful, transmitDbm: -100 },
    profilePoints,
    distances,
    [0, 0, 0],
  );
  expect(weak.status).toBe('risk');
  expect(weak.marginDb).toBeLessThan(0);
});

it('calibrates the isolated knife-edge approximation and retains unknown terrain', () => {
  expect(knifeEdgeLossDb(-1)).toBe(0);
  expect(knifeEdgeLossDb(0)).toBeCloseTo(6.032852, 5);
  expect(knifeEdgeLossDb(1)).toBeCloseTo(13.925729, 5);
  expect(() => knifeEdgeLossDb(Infinity)).toThrow(/finite/);
  const unknown = evaluateRfTerrainProfile(powerful, profilePoints, distances, [0, null, 0]);
  expect(unknown.status).toBe('unknown');
  expect(unknown.marginDb).toBeNull();
  expect(unknown.points[1]?.elevationM).toBeNull();
  expect(unknown.points[1]?.rayHeightM).toBe(100);
  expect(
    evaluateRfTerrainProfile(powerful, profilePoints, distances, [null, 0, 0]).points.every(
      (point) => point.rayHeightM === null,
    ),
  ).toBe(true);
});

it('preserves below-sea-level values and warns about bathymetry instead of silently changing terrain', () => {
  const plan = createRfTerrainPath([0, 0], [0.01, 0], 3);
  const result = analyseRfTerrain(powerful, plan, [-20, -20, -20]);
  expect(result.belowSeaLevelSamples).toBe(3);
  expect(result.path?.points.map((point) => point.elevationM)).toEqual([-20, -20, -20]);
  expect(result.path?.points[0]?.rayHeightM).toBe(80);
  expect(result.warnings.join(' ')).toMatch(/bathymetry/);
  const missing = analyseRfTerrain(powerful, plan, [0, null, 0]);
  expect(missing.missingSamples).toBe(1);
  expect(missing.path?.status).toBe('unknown');
  expect(() => analyseRfTerrain(powerful, plan, [0, 0])).toThrow(/match/);
});

it('stops radial silhouettes at the first failing prefix without inventing recovery beyond it', () => {
  const plan = createRfTerrainRadials([0, 51], 5, 4, 4);
  const elevations = Array<number | null>(plan.positions.length).fill(0);
  const indices = plan.profiles[0]!.indices;
  elevations[indices[2]!] = 1000;
  const result = analyseRfTerrain(powerful, plan, elevations);
  expect(result.radials[0]?.clearDistanceKm).toBe(1.25);
  expect(result.radials[0]?.stopDistanceKm).toBe(2.8125);
  expect(result.radials[0]?.status).toBe('blocked');
  expect(result.radials[0]?.samples).toHaveLength(2);
  expect(result.radials[1]?.clearDistanceKm).toBe(5);
  expect(result.radials[1]?.stopDistanceKm).toBeNull();
  elevations[indices[1]!] = null;
  const missing = analyseRfTerrain(powerful, plan, elevations);
  expect(missing.radials[0]?.clearDistanceKm).toBe(0);
  expect(missing.radials[0]?.status).toBe('unknown');
});

it('creates static bounded terrain overlays with gaps between sampled bearings', () => {
  const plan = createRfTerrainRadials([179.99, 0], 5, 4, 4);
  const analysis = analyseRfTerrain(powerful, plan, Array<number>(plan.positions.length).fill(0));
  const layers = rfTerrainLayers(analysis, true);
  expect(layers).toHaveLength(11);
  expect(layers.every((layer) => !layer.props.pickable)).toBe(true);
  const sectors = layers.find((layer) => layer.id === 'rf-terrain-sampled-sectors');
  expect(sectors?.props.data).toHaveLength(4);
  for (const ring of sectors?.props.data as Position[][]) {
    expect(ring).toHaveLength(3);
    expect(
      Math.max(...ring.map(([lon]) => lon)) - Math.min(...ring.map(([lon]) => lon)),
    ).toBeLessThan(1);
  }
  const radialPaths = layers.find((layer) => layer.id === 'rf-terrain-paths');
  expect(radialPaths?.props.data).toHaveLength(12);
  expect(
    layers.find((layer) => layer.id === 'rf-terrain-interpolated-footprint')?.props.data,
  ).toEqual([]);
  expect(rfTerrainLayers(null, false)).toEqual([]);
});
