import type { Layer } from '@deck.gl/core';
import type { PathLayer } from '@deck.gl/layers';
import { Geodesic } from 'geographiclib-geodesic';
import { expect, it } from 'vitest';
import { analyseRfTerrain } from './rfTerrainAnalysis';
import { rfTerrainLayers } from './rfTerrainLayers';
import { evaluateRfTerrainProfile } from './rfTerrainProfile';
import { createRfTerrainRadials } from './rfTerrainSampling';
import { DEFAULT_RF_INPUTS } from './rfPlanning';
import {
  RF_STATUS_COLOURS,
  rfInterpolatedFootprint,
  rfPathPointStatus,
  rfPathSummary,
} from './rfTerrainPresentation';
import type { Position } from './geoJsonTypes';
import type { RfTerrainAnalysis, RfTerrainProfile, RfTerrainStatus } from './rfTerrainTypes';

const input = {
  ...DEFAULT_RF_INPUTS,
  transmitHeightM: 100,
  receiveHeightM: 100,
  transmitDbm: 40,
  sensitivityDbm: -120,
};
const positions: Position[] = [
  [0, 0],
  [0.005, 0],
  [0.01, 0],
  [0.015, 0],
  [0.02, 0],
];
const distances = [0, 500, 1000, 1500, 2000];
const profile = (heights: (number | null)[], power = input) =>
  evaluateRfTerrainProfile(power, positions, distances, heights);
const pathAnalysis = (path: RfTerrainProfile): RfTerrainAnalysis => ({
  kind: 'path',
  path,
  radials: [],
  origin: positions[0]!,
  receiver: positions.at(-1)!,
  maxDistanceKm: 2,
  warnings: [],
  sampleCount: 5,
  missingSamples: 0,
  belowSeaLevelSamples: 0,
});
const layer = (layers: Layer[], id: string) => layers.find((item) => item.id === id)!;
const labels = (layers: Layer[]) =>
  layer(layers, 'rf-terrain-labels').props.data as { label: string; point: Position }[];

it('marks the first interior obstruction and keeps the downstream direct ray red', () => {
  const result = profile([0, 150, 0, 0, 0]);
  expect(result.points[3]!.clearanceM).toBeGreaterThan(0);
  expect(rfPathSummary(result).firstBlocked).toBe(result.points[1]);
  expect(result.points.map((point) => rfPathPointStatus(result, point))).toEqual([
    'clear',
    'blocked',
    'blocked',
    'blocked',
    'blocked',
  ]);
  const layers = rfTerrainLayers(pathAnalysis(result), false);
  const segments = layer(layers, 'rf-terrain-paths').props.data as {
    status: RfTerrainStatus;
    path: Position[];
  }[];
  expect(segments.map((segment) => segment.status)).toEqual([
    'risk',
    'blocked',
    'blocked',
    'blocked',
  ]);
  expect(layer(layers, 'rf-terrain-stops').props.data).toEqual([
    { point: positions[1], status: 'blocked' },
  ]);
  expect(
    labels(layers).some((item) => item.label.includes('First sampled obstruction · 0.50 km')),
  ).toBe(true);
  expect(
    labels(layers).some((item) => item.label.includes('RX · 2.0 km · direct ray obstructed')),
  ).toBe(true);
  expect((layer(layers, 'rf-terrain-path-underlay') as PathLayer).props.getWidth).toBeGreaterThan(
    (layer(layers, 'rf-terrain-paths') as PathLayer).props.getWidth as number,
  );
  expect(layers.every((item) => item.props.pickable === false)).toBe(true);
  expect(RF_STATUS_COLOURS.blocked[0]).toBeGreaterThan(RF_STATUS_COLOURS.blocked[1] * 3);
});

it('does not confuse global weak power, Fresnel intrusion, endpoint clearance or missing terrain', () => {
  const weak = profile([0, 0, 0, 0, 0], { ...input, transmitDbm: -100 });
  expect(rfPathSummary(weak)).toEqual({ firstBlocked: null, firstRisk: null });
  expect(weak.points.map((point) => rfPathPointStatus(weak, point))).toEqual(Array(5).fill('risk'));
  const restricted = profile([0, 0, 0, 0, 0], { ...input, transmitHeightM: 5, receiveHeightM: 5 });
  expect(rfPathSummary(restricted).firstRisk).toBe(restricted.points[1]);
  expect(rfPathSummary(restricted).firstBlocked).toBeNull();
  expect(
    labels(rfTerrainLayers(pathAnalysis(restricted), true)).some((item) =>
      item.label.includes('Fresnel intrusion'),
    ),
  ).toBe(true);
  const endpoints = profile([0, 0, 0, 0, 0]);
  endpoints.points[0]!.clearanceM = -1;
  endpoints.points[0]!.fresnelClearanceM = -1;
  endpoints.points.at(-1)!.clearanceM = -1;
  endpoints.points.at(-1)!.fresnelClearanceM = -1;
  expect(rfPathSummary(endpoints)).toEqual({ firstBlocked: null, firstRisk: null });
  const unknown = profile([0, 150, null, 0, 0]);
  expect(rfPathSummary(unknown)).toEqual({ firstBlocked: null, firstRisk: null });
  expect(unknown.points.map((point) => rfPathPointStatus(unknown, point))).toEqual(
    Array(5).fill('unknown'),
  );
  const layers = rfTerrainLayers(pathAnalysis(unknown), true);
  expect(layer(layers, 'rf-terrain-stops').props.data).toEqual([]);
  expect(labels(layers).some((item) => item.label.includes('terrain unknown'))).toBe(true);
});

function radialAnalysis(origin: Position = [179.99, 0]) {
  const plan = createRfTerrainRadials(origin, 5, 4, 4);
  const elevations = Array<number | null>(plan.positions.length).fill(0);
  return { plan, elevations, analysis: analyseRfTerrain(input, plan, elevations) };
}

it('places radial failure markers on assessed receiver targets and greys the unassessed tail', () => {
  const { plan, elevations } = radialAnalysis();
  elevations[plan.profiles[0]!.indices[2]!] = 1000;
  const analysis = analyseRfTerrain(input, plan, elevations);
  const layers = rfTerrainLayers(analysis, true);
  const failed = analysis.radials[0]!;
  expect(failed.clearDistanceKm).toBe(2.5);
  expect(failed.stopDistanceKm).toBe(3.75);
  expect(layer(layers, 'rf-terrain-stops').props.data).toEqual([
    { point: failed.samples.at(-1)!.position, status: 'blocked' },
  ]);
  expect(
    labels(layers).some((item) =>
      item.label.includes('first failing target 3.8 km\nLast pass 2.5 km · beyond stop unassessed'),
    ),
  ).toBe(true);
  expect(labels(layers).every((item) => !item.label.includes('obstruction'))).toBe(true);
  expect(layer(layers, 'rf-terrain-unassessed').props.data).toHaveLength(4);
  expect(labels(layers).some((item) => item.label.includes('Survey limit · 5.0 km'))).toBe(true);
  elevations[plan.profiles[0]!.indices[1]!] = null;
  const missing = rfTerrainLayers(analyseRfTerrain(input, plan, elevations), true);
  expect(labels(missing).some((item) => item.label.includes('first unknown target'))).toBe(true);
  expect(labels(missing).some((item) => item.label.includes('No passing target established'))).toBe(
    true,
  );
});

it('adds an optional bounded dateline-safe illustrative footprint without filling unknown bearings', () => {
  const { analysis } = radialAnalysis();
  analysis.radials[0]!.clearDistanceKm = 2;
  const rings = rfInterpolatedFootprint(analysis);
  expect(rings).toHaveLength(4);
  expect(rings.every((ring) => ring.length === 9)).toBe(true);
  for (const [index, ring] of rings.entries()) {
    expect(
      Math.max(...ring.map(([lon]) => lon)) - Math.min(...ring.map(([lon]) => lon)),
    ).toBeLessThan(1);
    for (const point of ring.slice(1, -1)) {
      const distance =
        (Geodesic.WGS84.Inverse(analysis.origin[1], analysis.origin[0], point[1], point[0]).s12 ??
          0) / 1000;
      expect(distance).toBeCloseTo(index === 0 || index === 3 ? 2 : 5, 5);
    }
  }
  const withBubble = rfTerrainLayers(analysis, true, true);
  const withoutBubble = rfTerrainLayers(analysis, true);
  expect(layer(withBubble, 'rf-terrain-interpolated-footprint').props.data).toHaveLength(4);
  expect(layer(withoutBubble, 'rf-terrain-interpolated-footprint').props.data).toEqual([]);
  expect(layer(withBubble, 'rf-terrain-paths').props.data).toEqual(
    layer(withoutBubble, 'rf-terrain-paths').props.data,
  );
  expect(labels(withBubble).some((item) => item.label.includes('Interpolated estimate'))).toBe(
    true,
  );
  analysis.radials[0]!.status = 'unknown';
  expect(rfInterpolatedFootprint(analysis)).toHaveLength(2);
  analysis.radials[0]!.status = 'clear';
  analysis.radials[0]!.clearDistanceKm = 0;
  expect(rfInterpolatedFootprint(analysis)).toHaveLength(2);
  expect(rfInterpolatedFootprint(pathAnalysis(profile([0, 0, 0, 0, 0])))).toEqual([]);
  expect(rfInterpolatedFootprint({ ...analysis, radials: analysis.radials.slice(0, 3) })).toEqual(
    [],
  );
});

it('clips unsupported polar map positions while retaining globe geometry', () => {
  const analysis = pathAnalysis(profile([0, 150, 0, 0, 0]));
  analysis.origin = [0, 86];
  analysis.receiver = [0.02, 86];
  analysis.path!.points = analysis.path!.points.map((point) => ({
    ...point,
    position: [point.position[0], 86],
  }));
  const map = rfTerrainLayers(analysis, true),
    globe = rfTerrainLayers(analysis, false);
  expect(layer(map, 'rf-terrain-paths').props.data).toEqual([]);
  expect(layer(map, 'rf-terrain-labels').props.data).toEqual([]);
  expect(layer(globe, 'rf-terrain-paths').props.data).toHaveLength(4);
  expect(layer(globe, 'rf-terrain-labels').props.data).toHaveLength(3);
});
