import { describe, expect, it } from 'vitest';
import { drawingWatchArea } from './areaWatchGeometry';

describe('drawing watch bounds', () => {
  it('encloses curved rectangle edges and keeps the shorter dateline crossing', () => {
    const rectangle = drawingWatchArea('rectangle', [
      [-20, 50],
      [20, 60],
    ]);
    expect(rectangle.source).toBe('shape');
    expect(rectangle.bounds.west).toBeLessThan(-20);
    expect(rectangle.bounds.east).toBeGreaterThan(20);
    expect(rectangle.bounds.south).toBeLessThan(50);
    // The drawn northern geodesic reaches 61.521175 N, beyond the two corner latitudes.
    // [0, 61] is visibly inside the sketch and must remain inside the indicator.
    expect(rectangle.bounds.north).toBeGreaterThan(61.521175);
    expect(rectangle.bounds.south < 61 && rectangle.bounds.north > 61).toBe(true);
    const dateline = drawingWatchArea('rectangle', [
      [170, -10],
      [-170, 10],
    ]).bounds;
    expect(dateline.west).toBeGreaterThan(169);
    expect(dateline.west).toBeLessThan(170);
    expect(dateline.east).toBeLessThan(-169);
    expect(dateline.east).toBeGreaterThan(-170);
    expect(dateline.south).toBeLessThan(-10);
    expect(dateline.north).toBeGreaterThan(10);
  });
  it('retains exact circle geometry and refuses unsplit crossing polygons', () => {
    const circle = drawingWatchArea('circle', [
      [0, 50],
      [0.1, 50],
    ]);
    expect(circle.source).toBe('shape');
    expect(circle.bounds.west).toBeLessThan(-0.09);
    expect(circle.bounds.east).toBeGreaterThan(0.1);
    expect(circle.bounds.south).toBeLessThan(50);
    expect(circle.bounds.north).toBeGreaterThan(50);
    expect(circle.geometry?.features[0]?.geometry.type).toBe('Polygon');
    expect(() =>
      drawingWatchArea('polygon', [
        [179, 1],
        [-179, 1],
        [-179, 3],
      ]),
    ).toThrow('rectangle');
  });
  it('rejects paths, incomplete, zero-area, invalid and oversized sketches', () => {
    expect(() =>
      drawingWatchArea('path', [
        [0, 0],
        [1, 1],
      ]),
    ).toThrow('Paths');
    expect(() =>
      drawingWatchArea('polygon', [
        [0, 0],
        [1, 1],
      ]),
    ).toThrow('Finish');
    expect(() => drawingWatchArea('rectangle', [[0, 0]])).toThrow('Finish');
    expect(() =>
      drawingWatchArea('rectangle', [
        [0, 0],
        [0, 1],
      ]),
    ).toThrow('non-zero');
    expect(() =>
      drawingWatchArea('polygon', [
        [0, 0],
        [0, 1],
        [0, 2],
      ]),
    ).toThrow('non-zero');
    expect(() =>
      drawingWatchArea('circle', [
        [0, 0],
        [30, 0],
      ]),
    ).toThrow('1,000');
    expect(() =>
      drawingWatchArea('rectangle', [
        [NaN, 0],
        [1, 1],
      ]),
    ).toThrow('longitude');
    expect(() =>
      drawingWatchArea(
        'polygon',
        Array.from({ length: 33 }, () => [0, 1]),
      ),
    ).toThrow('32');
    expect(() =>
      drawingWatchArea('polygon', [
        [-170, 0],
        [0, 10],
        [170, 0],
      ]),
    ).toThrow('smaller');
    expect(() =>
      drawingWatchArea('circle', [
        [0, 89.5],
        [5, 89.5],
      ]),
    ).toThrow('pole');
  });
});
