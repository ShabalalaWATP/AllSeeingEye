import { _GlobeView as GlobeView } from '@deck.gl/core';
import { expect, it } from 'vitest';

/** Real projection maths: deck9.3 ignored bearing/pitch, drifting away from a rotated basemap. */
function viewport(bearing: number, pitch = 0) {
  const viewState = { longitude: 0, latitude: 0, zoom: 2, bearing, pitch };
  const result = new GlobeView().makeViewport({
    width: 1000,
    height: 800,
    viewState,
  });
  if (!result) throw new Error('Expected globe viewport');
  return result;
}

it('rotates geographic overlays with a south-up globe instead of leaving them north-up', () => {
  const north = viewport(0).project([10, 10]);
  const south = viewport(180).project([10, 10]);
  expect(north[0]).toBeGreaterThan(500);
  expect(north[1]).toBeLessThan(400);
  expect(south[0]).toBeLessThan(500);
  expect(south[1]).toBeGreaterThan(400);
  expect(north[0]! + south[0]!).toBeCloseTo(1000, 5);
  expect(north[1]! + south[1]!).toBeCloseTo(800, 5);
});

it('projects and unprojects pitched globe positions without the old flat camera assumption', () => {
  const tilted = viewport(45, 40);
  const point = tilted.project([5, 8]);
  expect(point).not.toEqual(viewport(45).project([5, 8]));
  const roundtrip = tilted.unproject(point);
  expect(roundtrip[0]).toBeCloseTo(5, 5);
  expect(roundtrip[1]).toBeCloseTo(8, 5);
});
