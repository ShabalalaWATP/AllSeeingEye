import { expect, it } from 'vitest';
import { Geodesic } from 'geographiclib-geodesic';
import type { PathLayer } from '@deck.gl/layers';
import { DEFAULT_RF_INPUTS } from './rfPlanning';
import { RF_PRESETS } from './rfPresets';
import { rfMapEstimate, rfMapLayers, rfRangeRing } from './rfMap';
import type { Position } from './geoJsonTypes';
import { rfReferencePoint } from './rfReferenceGeometry';
import type { RfReferencePath } from './rfReferenceGeometry';
import { RF_STATUS_COLOURS } from './rfTerrainPresentation';

function layerData<T>(layers: ReturnType<typeof rfMapLayers>, id: string): T[] {
  return layers.find((layer) => layer.id === id)?.props.data as T[];
}

it('caps the illustrative circle at both the horizon and sensitivity distance', () => {
  const horizonLimited = rfMapEstimate(DEFAULT_RF_INPUTS, [0, 51]);
  expect(horizonLimited.radiusKm).toBe(horizonLimited.horizonKm);
  const powerLimited = rfMapEstimate({ ...DEFAULT_RF_INPUTS, transmitDbm: -30 }, [0, 51]);
  expect(powerLimited.radiusKm).toBe(powerLimited.sensitivityDistanceKm);
  expect(powerLimited.radiusKm).toBeLessThan(horizonLimited.radiusKm);
  expect(() =>
    rfMapEstimate({ ...DEFAULT_RF_INPUTS, transmitHeightM: 0, receiveHeightM: 0 }, [0, 51]),
  ).toThrow(/below 1 metre/);
  expect(() => rfMapEstimate(DEFAULT_RF_INPUTS, [181, 0])).toThrow(/longitude/);
});

it.each<Position>([
  [179.9, 0],
  [30, 89.9],
  [-0.1, 51.5],
])('builds a bounded geodesic circle around %s', (lon, lat) => {
  const estimate = rfMapEstimate(DEFAULT_RF_INPUTS, [lon, lat]);
  const ring = rfRangeRing(estimate);
  expect(ring).toHaveLength(73);
  expect(ring[0]?.[0]).toBeCloseTo(ring[72]?.[0] ?? NaN, 8);
  for (const [x, y] of ring) {
    expect(Math.abs(x)).toBeLessThanOrEqual(180);
    expect(Math.abs(y)).toBeLessThanOrEqual(90);
    expect(Geodesic.WGS84.Inverse(lat, lon, y, x).s12).toBeCloseTo(estimate.radiusKm * 1000, 4);
  }
});

it('renders an optional path and labelled sites without intercepting map clicks', () => {
  const estimate = rfMapEstimate(DEFAULT_RF_INPUTS, [0, 51], [0.1, 51]);
  const layers = rfMapLayers(estimate, true);
  expect(layers.map((layer) => layer.id)).toEqual([
    'rf-estimate-path-underlay',
    'rf-estimate-paths',
    'rf-estimate-limit',
    'rf-estimate-sites',
    'rf-estimate-label',
  ]);
  expect(layerData(layers, 'rf-estimate-paths')).toHaveLength(2);
  expect(layerData(layers, 'rf-estimate-sites')).toHaveLength(2);
  expect(layers.every((layer) => layer.props.pickable === false)).toBe(true);
  expect(estimate.label).toContain('no terrain model');
  expect(rfMapLayers(null, true)).toEqual([]);
  const polar = rfMapLayers(rfMapEstimate(DEFAULT_RF_INPUTS, [0, 90]), true);
  expect(polar.every((layer) => Array.from(layer.props.data as unknown[]).length === 0)).toBe(true);
});

it('marks the exact model limit and clearly distinguishes the path beyond it', () => {
  const origin: Position = [-0.1, 51.5];
  const estimate = rfMapEstimate(DEFAULT_RF_INPUTS, origin, rfReferencePoint(origin, 80, 50));
  const layers = rfMapLayers(estimate, false);
  const paths = layerData<RfReferencePath>(layers, 'rf-estimate-paths');
  const inside = paths.find(({ status }) => status === 'inside')!;
  const outside = paths.find(({ status }) => status === 'outside')!;
  const boundary = layerData<Position>(layers, 'rf-estimate-limit')[0]!;
  expect(inside.path.at(-1)?.[0]).toBeCloseTo(boundary[0], 10);
  expect(outside.path[0]?.[1]).toBeCloseTo(boundary[1], 10);
  expect(Geodesic.WGS84.Inverse(origin[1], origin[0], boundary[1], boundary[0]).s12).toBeCloseTo(
    estimate.radiusKm * 1000,
    5,
  );
  const pathLayer = layers.find(
    (layer) => layer.id === 'rf-estimate-paths',
  )! as PathLayer<RfReferencePath>;
  const colour = pathLayer.props.getColor as unknown as (path: RfReferencePath) => number[];
  expect(colour(inside)).toEqual(RF_STATUS_COLOURS.clear);
  expect(colour(outside)).toEqual(RF_STATUS_COLOURS.blocked);
  const width = pathLayer.props.getWidth as (path: RfReferencePath) => number;
  expect(width(inside)).toBeGreaterThanOrEqual(4);
  const underlay = layers.find(
    (layer) => layer.id === 'rf-estimate-path-underlay',
  )! as PathLayer<RfReferencePath>;
  expect(underlay.props.getWidth).toBe(7);
  const labels = layerData<{ label: string }>(layers, 'rf-estimate-label');
  expect(labels.map(({ label }) => label)).toEqual([
    'TX · 0 km\nTerrain not checked',
    `Ideal limit · ${estimate.radiusKm.toFixed(1)} km\nRadio horizon`,
    'RX · 50.0 km\nBeyond ideal limit',
  ]);
  expect(labels.every(({ label }) => !label.toLowerCase().includes('blocked'))).toBe(true);
});

it('labels a sensitivity limit in metres and does not claim an obstructed path', () => {
  const estimate = rfMapEstimate({ ...DEFAULT_RF_INPUTS, transmitDbm: -30 }, [0, 51], [0, 51]);
  const layers = rfMapLayers(estimate, true);
  expect(
    layerData<RfReferencePath>(layers, 'rf-estimate-paths').map(({ status }) => status),
  ).toEqual(['boundary']);
  const labels = layerData<{ label: string }>(layers, 'rf-estimate-label');
  expect(labels[1]?.label).toMatch(/Ideal limit · \d+ m\nReceiver sensitivity/);
  expect(labels[2]?.label).toBe('RX · 0 m\nInside ideal limit');
  expect(estimate.label).toMatch(/\d+ m · no terrain model/);
});

it('keeps the omnidirectional bubble optional, static, bounded and click-through', () => {
  const estimate = rfMapEstimate(DEFAULT_RF_INPUTS, [179.99, 5]);
  const without = rfMapLayers(estimate, true);
  expect(without.some(({ id }) => id === 'rf-estimate-bubble')).toBe(false);
  const layers = rfMapLayers(estimate, true, true);
  const fill = layerData<Position[]>(layers, 'rf-estimate-bubble');
  expect(fill).toHaveLength(72);
  expect(fill.every((polygon) => polygon.length === 4)).toBe(true);
  for (const polygon of fill) {
    const longitudes = polygon.map(([lon]) => lon);
    expect(Math.max(...longitudes) - Math.min(...longitudes)).toBeLessThan(1);
  }
  const paths = layerData<RfReferencePath>(layers, 'rf-estimate-paths');
  expect(paths.filter(({ status }) => status === 'range')).toHaveLength(3);
  expect(paths.every(({ path }) => path.length === 73)).toBe(true);
  expect(layers.every(({ props }) => props.pickable === false && !props.transitions)).toBe(true);
  const pathLayer = layers.find(
    ({ id }) => id === 'rf-estimate-paths',
  )! as PathLayer<RfReferencePath>;
  const width = pathLayer.props.getWidth as (path: RfReferencePath) => number;
  const colour = pathLayer.props.getColor as unknown as (path: RfReferencePath) => number[];
  expect(width(paths.find(({ status }) => status === 'range')!)).toBe(1);
  const rangeColour = colour(paths.find(({ status }) => status === 'range')!);
  expect(rangeColour[3]).toBeLessThan(RF_STATUS_COLOURS.clear[3]);
  const labels = layerData<{ label: string }>(layers, 'rf-estimate-label');
  expect(labels).toHaveLength(2);
});

it('preserves polar outlines on the globe and avoids unsafe bubble fills', () => {
  const estimate = rfMapEstimate(DEFAULT_RF_INPUTS, [0, 90]);
  const globe = rfMapLayers(estimate, false, true);
  expect(layerData(globe, 'rf-estimate-bubble')).toEqual([]);
  expect(layerData(globe, 'rf-estimate-paths')).toHaveLength(4);
  expect(layerData(globe, 'rf-estimate-sites')).toEqual([[0, 90]]);
  const flat = rfMapLayers(estimate, true, true);
  expect(flat.every(({ props }) => (props.data as unknown[]).length === 0)).toBe(true);
});

it('keeps all illustrative radio presets in the supported terrestrial model', () => {
  expect(RF_PRESETS.length).toBeGreaterThanOrEqual(10);
  for (const preset of RF_PRESETS) {
    const estimate = rfMapEstimate(preset.values, [0, 51]);
    expect(estimate.radiusKm).toBeGreaterThan(0);
    expect(Number.isFinite(estimate.radiusKm)).toBe(true);
  }
});
