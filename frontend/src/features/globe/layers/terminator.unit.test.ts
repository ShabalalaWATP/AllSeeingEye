import { describe, expect, it } from 'vitest';

import {
  TERMINATOR_LAYER_ID,
  buildTerminatorLayer,
  nightPolygon,
  subsolarPoint,
} from './terminator';

describe('subsolarPoint', () => {
  it('puts the sun over the tropic of Cancer near Greenwich at the June solstice noon', () => {
    const sun = subsolarPoint(new Date('2026-06-21T12:00:00Z'));
    expect(sun.lat).toBeGreaterThan(23.3);
    expect(sun.lat).toBeLessThan(23.5);
    expect(Math.abs(sun.lon)).toBeLessThan(3);
  });

  it('puts the sun over the tropic of Capricorn near the antimeridian at the December solstice midnight', () => {
    const sun = subsolarPoint(new Date('2026-12-21T00:00:00Z'));
    expect(sun.lat).toBeGreaterThan(-23.5);
    expect(sun.lat).toBeLessThan(-23.3);
    expect(Math.abs(sun.lon)).toBeGreaterThan(175);
  });

  it('crosses the equator at the March equinox', () => {
    expect(Math.abs(subsolarPoint(new Date('2026-03-20T14:00:00Z')).lat)).toBeLessThan(1);
  });
});

describe('nightPolygon', () => {
  it('follows the terminator and closes over the dark pole', () => {
    const summer = nightPolygon({ lon: 0, lat: 20 });
    expect(summer).toHaveLength(183);
    expect(summer[90]![0]).toBe(0);
    expect(summer[90]![1]).toBeCloseTo(-70, 3);
    expect(summer[0]![1]).toBeCloseTo(70, 3);
    expect(summer.at(-1)).toEqual([-180, -89.9]);
    const winter = nightPolygon({ lon: 90, lat: -20 });
    expect(winter.at(-2)).toEqual([180, 89.9]);
    const equinox = nightPolygon({ lon: 0, lat: 0 }, 90);
    expect(equinox.every(([, lat]) => Number.isFinite(lat))).toBe(true);
    expect(equinox).toHaveLength(7);
  });
});

describe('buildTerminatorLayer', () => {
  it('builds one unpickable polygon layer', () => {
    const layer = buildTerminatorLayer(new Date('2026-06-21T12:00:00Z'));
    expect(layer.id).toBe(TERMINATOR_LAYER_ID);
    const props = layer.props as unknown as {
      pickable: boolean;
      data: { ring: [number, number][] }[];
      getPolygon: (night: { ring: [number, number][] }) => [number, number][];
    };
    expect(props.pickable).toBe(false);
    expect(props.data).toHaveLength(1);
    expect(props.getPolygon(props.data[0]!)).toHaveLength(183);
  });
});
