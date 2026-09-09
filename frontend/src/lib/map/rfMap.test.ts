import { expect, it } from 'vitest';
import { Geodesic } from 'geographiclib-geodesic';
import { DEFAULT_RF_INPUTS } from './rfPlanning';
import { RF_PRESETS } from './rfPresets';
import { rfMapEstimate, rfMapLayers, rfRangeRing } from './rfMap';
import type { Position } from './geoJsonTypes';

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
    'rf-estimate-paths',
    'rf-estimate-sites',
    'rf-estimate-label',
  ]);
  expect(layers[0]?.props.data).toHaveLength(2);
  expect(layers[1]?.props.data).toHaveLength(2);
  expect(layers.every((layer) => layer.props.pickable === false)).toBe(true);
  expect(estimate.label).toContain('no terrain model');
  expect(rfMapLayers(null, true)).toEqual([]);
  const polar = rfMapLayers(rfMapEstimate(DEFAULT_RF_INPUTS, [0, 90]), true);
  expect(polar[0]?.props.data).toEqual([]);
  expect(polar[1]?.props.data).toEqual([]);
  expect(polar[2]?.props.data).toEqual([]);
});

it('keeps all illustrative radio presets in the supported terrestrial model', () => {
  expect(RF_PRESETS.length).toBeGreaterThanOrEqual(10);
  for (const preset of RF_PRESETS) {
    const estimate = rfMapEstimate(preset.values, [0, 51]);
    expect(estimate.radiusKm).toBeGreaterThan(0);
    expect(Number.isFinite(estimate.radiusKm)).toBe(true);
  }
});
