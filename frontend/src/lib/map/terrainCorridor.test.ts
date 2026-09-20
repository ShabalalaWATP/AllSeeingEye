import { expect, it } from 'vitest';
import { createResearchCorridor } from './terrainCorridor';
import { areaContainsPoint } from './areaEvidencePreview';

it('creates a bounded research polygon around the entire path and both ends', () => {
  const area = createResearchCorridor(
    [
      [0, 51],
      [0.1, 51],
      [0.1, 51.05],
    ],
    1,
  );
  expect(area.features[0]?.geometry.type).toBe('Polygon');
  expect(areaContainsPoint(area, [0.05, 51])).toBe(true);
  expect(areaContainsPoint(area, [0.1, 51.04])).toBe(true);
  expect(areaContainsPoint(area, [1, 51])).toBe(false);
  expect(new TextEncoder().encode(JSON.stringify(area)).byteLength).toBeLessThan(16384);
  const geometry = area.features[0]!.geometry;
  if (geometry.type === 'Polygon') expect(geometry.coordinates[0]!.length).toBeLessThan(256);
});

it('rejects ambiguity, excessive work and invalid widths instead of widening to a rectangle', () => {
  expect(() =>
    createResearchCorridor(
      [
        [179.9, 0],
        [-179.9, 0],
      ],
      1,
    ),
  ).toThrow(/180/);
  expect(() =>
    createResearchCorridor(
      [
        [0, 81],
        [0.1, 81],
      ],
      1,
    ),
  ).toThrow(/80/);
  expect(() =>
    createResearchCorridor(
      [
        [0, 51],
        [0, 51],
      ],
      1,
    ),
  ).toThrow(/one metre/);
  expect(() =>
    createResearchCorridor(
      [
        [0, 51],
        [10, 51],
      ],
      1,
    ),
  ).toThrow(/200 km/);
  expect(() =>
    createResearchCorridor(
      [
        [0, 51],
        [0.1, 51],
      ],
      0,
    ),
  ).toThrow(/Distance/);
  expect(() =>
    createResearchCorridor(
      [
        [0, 51],
        [0.1, 51],
        [0, 51],
      ],
      1,
    ),
  ).toThrow(/turns too sharply/);
  expect(() =>
    createResearchCorridor(
      [
        [0, 0],
        [0.1, 0.1],
        [0.1, 0],
        [0, 0.1],
      ],
      0.1,
    ),
  ).toThrow(/intersects/);
});
