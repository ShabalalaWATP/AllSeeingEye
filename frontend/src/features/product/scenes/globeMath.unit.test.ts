import { describe, expect, it } from 'vitest';

import {
  fibonacciSphere,
  greatCircle,
  isLand,
  landPoints,
  project,
  seededRandom,
  toSphere,
} from './globeMath';
import { buildScene } from './sceneData';

describe('land mask', () => {
  it('knows land from sea at familiar places', () => {
    expect(isLand(52.5, -1.5)).toBe(true); // England
    expect(isLand(0, 20)).toBe(true); // Central Africa
    expect(isLand(-25, 134)).toBe(true); // Australia
    expect(isLand(30, -40)).toBe(false); // North Atlantic
    expect(isLand(-10, -120)).toBe(false); // South Pacific
  });

  it('wraps longitudes and clamps latitudes', () => {
    expect(isLand(52.5, 358.5)).toBe(isLand(52.5, -1.5));
    expect(() => isLand(120, 0)).not.toThrow();
  });
});

describe('sphere geometry', () => {
  it('spreads the requested number of points over the whole sphere', () => {
    const points = fibonacciSphere(1000);
    expect(points).toHaveLength(1000);
    expect(Math.min(...points.map((p) => p.lat))).toBeLessThan(-85);
    expect(Math.max(...points.map((p) => p.lat))).toBeGreaterThan(85);
    const land = landPoints(4000).length / 4000;
    expect(land).toBeGreaterThan(0.25);
    expect(land).toBeLessThan(0.4);
  });

  it('projects the view centre to the middle of the disc, facing the viewer', () => {
    const view = { lon: 40, lat: 10, radius: 100, cx: 200, cy: 150 };
    const centre = project(toSphere({ lat: 10, lon: 40 }), view);
    expect(centre.x).toBeCloseTo(200);
    expect(centre.y).toBeCloseTo(150);
    expect(centre.depth).toBeCloseTo(1);
    expect(project(toSphere({ lat: -10, lon: -140 }), view).depth).toBeCloseTo(-1);
  });

  it('follows great circles between their end points', () => {
    const path = greatCircle({ lat: 51.5, lon: -0.1 }, { lat: 40.7, lon: -74 }, 20);
    expect(path).toHaveLength(21);
    expect(path[0]!.lat).toBeCloseTo(51.5);
    expect(path[20]!.lon).toBeCloseTo(-74);
    // The London to New York route bends north of both cities.
    expect(Math.max(...path.map((p) => p.lat))).toBeGreaterThan(51.5);
  });
});

describe('illustrative scene', () => {
  it('is identical on every visit', () => {
    const a = seededRandom(7);
    const b = seededRandom(7);
    expect([a(), a(), a()]).toEqual([b(), b(), b()]);
    expect(JSON.stringify(buildScene())).toBe(JSON.stringify(buildScene()));
  });

  it('draws something for every story layer', () => {
    for (const layer of buildScene()) {
      const shapes = layer.points.length + layer.routes.length + (layer.kind === 'orbits' ? 1 : 0);
      expect(shapes, layer.id).toBeGreaterThan(0);
    }
  });
});
