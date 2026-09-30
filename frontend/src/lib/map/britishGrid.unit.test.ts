import { describe, expect, it } from 'vitest';

import { britishGridLines, formatBritishGrid, fromBritishGrid, toBritishGrid } from './britishGrid';

describe('British National Grid', () => {
  it('matches the independent Ordnance Survey os-transform worked example within approximate datum tolerance', () => {
    // https://github.com/OrdnanceSurvey/os-transform#usage
    const point = toBritishGrid({ lat: 54.42480998276385, lon: -2.96793742245737 });
    expect(point).not.toBeNull();
    expect(Math.abs(point![0] - 337297)).toBeLessThan(5);
    expect(Math.abs(point![1] - 503695)).toBeLessThan(5);
    const [lon, lat] = fromBritishGrid(337297, 503695);
    expect(Math.abs(lon - -2.96793742245737)).toBeLessThan(0.0001);
    expect(Math.abs(lat - 54.42480998276385)).toBeLessThan(0.0001);
    expect(formatBritishGrid({ lat: 54.42480998276385, lon: -2.96793742245737 })).toMatch(
      /^BNG ≈ E 337300 N 503700 m$/,
    );
  });

  it.each([
    { lon: 37.6, lat: 55.7 },
    { lon: 0, lat: 0 },
    { lon: NaN, lat: 55 },
    { lon: -8.9, lat: 49 },
  ])('refuses outside or invalid coordinates %j', (position) => {
    expect(toBritishGrid(position)).toBeNull();
    expect(formatBritishGrid(position)).toBeNull();
  });

  it('bounds grid workload and hides it at world zoom', () => {
    for (const zoom of [0, 4.9, 23, NaN]) expect(britishGridLines(zoom)).toEqual([]);
    expect(britishGridLines(5)).toHaveLength(22);
    const detailed = britishGridLines(8);
    expect(detailed).toHaveLength(202);
    expect(detailed.reduce((sum, line) => sum + line.path.length, 0)).toBe(18602);
    expect(britishGridLines(22)).toEqual(detailed);
    for (const line of detailed)
      for (const point of line.path) {
        expect(point.every(Number.isFinite)).toBe(true);
        expect(point[0]).toBeGreaterThan(-15);
        expect(point[0]).toBeLessThan(5);
        expect(point[1]).toBeGreaterThan(49);
        expect(point[1]).toBeLessThan(62);
      }
  });
});
