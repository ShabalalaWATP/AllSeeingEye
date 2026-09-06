import type { Position } from './geoJsonTypes';
function at<T>(items: T[], index: number): T {
  const value = items[index];
  if (value === undefined) throw new Error('Incomplete geometry.');
  return value;
}

function side(a: Position, b: Position, c: Position) {
  return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]);
}
function onSegment(a: Position, b: Position, c: Position) {
  return (
    Math.abs(side(a, b, c)) < 1e-10 &&
    c[0] >= Math.min(a[0], b[0]) &&
    c[0] <= Math.max(a[0], b[0]) &&
    c[1] >= Math.min(a[1], b[1]) &&
    c[1] <= Math.max(a[1], b[1])
  );
}
function crosses(a: Position, b: Position, c: Position, d: Position) {
  return (
    (side(a, b, c) * side(a, b, d) < 0 && side(c, d, a) * side(c, d, b) < 0) ||
    onSegment(a, b, c) ||
    onSegment(a, b, d) ||
    onSegment(c, d, a) ||
    onSegment(c, d, b)
  );
}
function inside(point: Position, ring: Position[]) {
  let result = false;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const a = at(ring, i),
      b = at(ring, j);
    if (
      a[1] > point[1] !== b[1] > point[1] &&
      point[0] < ((b[0] - a[0]) * (point[1] - a[1])) / (b[1] - a[1]) + a[0]
    )
      result = !result;
  }
  return result;
}
/** Reject ambiguous topology; bounded rings avoid quadratic work on large uploads. */
export function validatePolygon(rings: Position[][]): void {
  if (rings.reduce((sum, ring) => sum + ring.length, 0) > 256)
    throw new Error('Each polygon is limited to 256 vertices. Simplify it before import.');
  for (const ring of rings) {
    if (
      ring.length < 4 ||
      at(ring, 0)[0] !== at(ring, ring.length - 1)[0] ||
      at(ring, 0)[1] !== at(ring, ring.length - 1)[1]
    )
      throw new Error('Polygon rings must contain at least four positions and be closed.');
    let area = 0;
    for (let i = 0; i < ring.length - 1; i++) {
      const a = at(ring, i),
        b = at(ring, i + 1);
      if (Math.abs(a[0] - b[0]) > 180)
        throw new Error('Polygon crosses the antimeridian. Supply a pre-split MultiPolygon.');
      if (a[0] === b[0] && a[1] === b[1])
        throw new Error('Polygon contains duplicate consecutive positions.');
      area += a[0] * b[1] - b[0] * a[1];
      for (let j = i + 2; j < ring.length - 1; j++) {
        if (i === 0 && j === ring.length - 2) continue;
        if (crosses(a, b, at(ring, j), at(ring, j + 1)))
          throw new Error('Polygon ring intersects itself.');
      }
    }
    if (Math.abs(area) < 1e-10) throw new Error('Polygon has no supported area.');
  }
  for (let i = 1; i < rings.length; i++) {
    const hole = at(rings, i);
    if (!inside(at(hole, 0), at(rings, 0)))
      throw new Error('Polygon hole lies outside its outer ring.');
    for (let j = 0; j < i; j++) {
      const other = at(rings, j);
      if (j > 0 && (inside(at(hole, 0), other) || inside(at(other, 0), hole)))
        throw new Error('Nested or overlapping polygon holes are unsupported.');
      for (let k = 0; k < hole.length - 1; k++)
        for (let l = 0; l < other.length - 1; l++) {
          if (crosses(at(hole, k), at(hole, k + 1), at(other, l), at(other, l + 1)))
            throw new Error('Polygon rings touch or intersect.');
        }
    }
  }
}

/** RFC7946 straight coordinate interpolation, not an inferred geodesic route. */
export function splitLine(line: Position[]): Position[][] {
  const result: Position[][] = [];
  let part: Position[] = [at(line, 0)];
  for (let i = 1; i < line.length; i++) {
    const a = at(line, i - 1),
      b = at(line, i);
    if (Math.abs(b[0] - a[0]) <= 180) {
      part.push(b);
      continue;
    }
    const shifted = b[0] + (b[0] > a[0] ? -360 : 360);
    const seam = shifted > 180 ? 180 : -180;
    if (shifted === a[0]) {
      part.push([a[0], b[1]]);
      continue;
    }
    const lat = a[1] + ((b[1] - a[1]) * (seam - a[0])) / (shifted - a[0]);
    part.push([seam, lat]);
    result.push(part);
    part = [[-seam, lat], b];
  }
  result.push(part);
  return result;
}
