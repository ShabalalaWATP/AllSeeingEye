import { expect, it } from 'vitest';
import { splitLine, validatePolygon } from './geoJsonTopology';
import type { Position } from './geoJsonTypes';

const rectangle = (left: number, bottom: number, right: number, top: number): Position[] => [
  [left, bottom],
  [right, bottom],
  [right, top],
  [left, top],
  [left, bottom],
];

it('rejects an empty line instead of creating display geometry with a missing endpoint', () => {
  expect(() => splitLine([])).toThrow('Incomplete geometry.');
});

it('keeps ordinary segments, including a half-world span, in their original order', () => {
  const line: Position[] = [
    [-90, 1],
    [90, 2],
    [100, 3],
  ];
  expect(splitLine(line)).toEqual([line]);
});

it('splits a westward antimeridian crossing with the interpolated seam latitude', () => {
  expect(
    splitLine([
      [-170, 10],
      [170, 30],
    ]),
  ).toEqual([
    [
      [-170, 10],
      [-180, 20],
    ],
    [
      [180, 20],
      [170, 30],
    ],
  ]);
});

it.each([180, -180])(
  'keeps equivalent seam longitudes together when starting at %s',
  (longitude) => {
    expect(
      splitLine([
        [longitude, 10],
        [-longitude, 20],
      ]),
    ).toEqual([
      [
        [longitude, 10],
        [longitude, 20],
      ],
    ]);
  },
);

it('accepts disjoint collinear edges of a concave polygon without a false intersection', () => {
  const notched: Position[] = [
    [0, 0],
    [4, 0],
    [4, 1],
    [2, 1],
    [2, 2],
    [4, 2],
    [4, 3],
    [0, 3],
    [0, 0],
  ];
  expect(() => validatePolygon([notched])).not.toThrow();
});

it('rejects duplicate adjacent vertices before accepting an otherwise closed boundary', () => {
  const ring = rectangle(0, 0, 10, 10);
  ring.unshift([0, 0]);
  expect(() => validatePolygon([ring])).toThrow('duplicate consecutive positions');
});

it('rejects a closed collinear triangle because it encloses no supported area', () => {
  expect(() =>
    validatePolygon([
      [
        [0, 0],
        [1, 1],
        [2, 2],
        [0, 0],
      ],
    ]),
  ).toThrow('no supported area');
});

it.each([false, true])(
  'rejects nested holes regardless of their input order, reversed=%s',
  (reversed) => {
    const holes = [rectangle(2, 2, 8, 8), rectangle(3, 3, 4, 4)];
    expect(() =>
      validatePolygon([rectangle(0, 0, 10, 10), ...(reversed ? holes.reverse() : holes)]),
    ).toThrow('Nested or overlapping polygon holes');
  },
);

it('rejects a hole that starts inside but touches the outer boundary', () => {
  const touching: Position[] = [
    [2, 2],
    [10, 2],
    [8, 4],
    [2, 2],
  ];
  expect(() => validatePolygon([rectangle(0, 0, 10, 10), touching])).toThrow(
    'rings touch or intersect',
  );
});

it('allows multiple separate holes without changing or reordering the saved rings', () => {
  const rings = [rectangle(0, 0, 10, 10), rectangle(1, 1, 2, 2), rectangle(7, 7, 8, 8)];
  const original = structuredClone(rings);
  expect(() => validatePolygon(rings)).not.toThrow();
  expect(rings).toEqual(original);
});
