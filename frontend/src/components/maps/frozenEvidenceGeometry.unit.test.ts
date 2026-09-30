import { expect, it } from 'vitest';
import type { EvidenceItem } from '@/lib/api/reports';
import { report } from '@/test/fixtures';
import { parseLocalGeoJson } from '@/lib/map/localGeoJson';
import { geometryBounds } from '@/lib/map/geometryBounds';
import { prepareEvidenceGeometry } from './frozenEvidenceGeometry';

function circle(count: number) {
  const ring = Array.from({ length: count }, (_, i) => [
    Math.cos((i * 2 * Math.PI) / count),
    Math.sin((i * 2 * Math.PI) / count),
  ]);
  return [...ring, ring[0]!];
}
function item(label = 'E1', coordinates = [circle(300)]): EvidenceItem {
  return {
    ...report.version.evidence[0]!,
    label,
    geometry: {
      geometry: { type: 'Polygon', coordinates },
      sha256: 'frozen-hash',
      location_role: 'observation_footprint',
      precision: 'Scene coverage',
      method: 'STAC',
      source_id: 'catalogue',
      attribution: 'Catalogue',
    },
  };
}
it('renders a 301-position source without weakening annotation validation or changing originals', () => {
  const source = item();
  const snapshot = JSON.stringify(source);
  const prepared = prepareEvidenceGeometry([source]);
  expect(prepared.omissions).toEqual([]);
  expect(prepared.source.features[0]?.geometry).toEqual(source.geometry?.geometry);
  expect(JSON.stringify(source)).toBe(snapshot);
  expect(() => parseLocalGeoJson(JSON.stringify(prepared.source))).toThrow(/256/);
});
it('keeps unsupported topology in labelled omissions without repairing the original', () => {
  const source = item('E2', [
    [
      [0, 0],
      [1, 1],
      [1, 0],
      [0, 1],
      [0, 0],
    ],
  ]);
  const prepared = prepareEvidenceGeometry([source]);
  expect(prepared.source.features).toEqual([]);
  expect(prepared.omissions[0]).toMatchObject({
    label: 'E2',
    reason: expect.stringMatching(/intersects/),
  });
  expect(source.geometry?.sha256).toBe('frozen-hash');
});
it('shares topology work across records and does not reset the budget after failure', () => {
  const prepared = prepareEvidenceGeometry(
    Array.from({ length: 4 }, (_, i) => item(`E${i}`, [circle(900)])),
  );
  expect(prepared.source.features).toHaveLength(2);
  expect(prepared.omissions.map((entry) => entry.label)).toEqual(['E2', 'E3']);
  expect(prepared.omissions.every((entry) => entry.reason.includes('processing limit'))).toBe(true);
});
it('charges optional layers against the same feature allowance', () => {
  const points = {
    type: 'FeatureCollection' as const,
    features: Array.from({ length: 2000 }, (_, id) => ({
      type: 'Feature' as const,
      id,
      properties: { label: String(id) },
      geometry: { type: 'Point' as const, coordinates: [0, 0] as [number, number] },
    })),
  };
  const prepared = prepareEvidenceGeometry([item()], [], points);
  expect(prepared.source.features).toHaveLength(1);
  expect(prepared.aoi).toBeNull();
  expect(prepared.omissions[0]?.reason).toMatch(/2,000/);
});
it('fits split geometry around the seam rather than the opposite side of the globe', () => {
  expect(
    geometryBounds({
      type: 'MultiPoint',
      coordinates: [
        [179, 10],
        [-179, 12],
      ],
    }),
  ).toEqual({ west: 179, east: -179, south: 10, north: 12 });
});

it('does not cut through the interior when fitting a wide polygon', () => {
  expect(
    geometryBounds({
      type: 'Polygon',
      coordinates: [
        [
          [-170, 0],
          [-80, 10],
          [10, 10],
          [100, 10],
          [170, 0],
          [100, -10],
          [10, -10],
          [-80, -10],
          [-170, 0],
        ],
      ],
    }),
  ).toEqual({ west: -170, east: 170, south: -10, north: 10 });
});

it('bounds oversized input before geometry validation and keeps later omissions explicit', () => {
  const oversized = item();
  oversized.geometry!.geometry.coordinates = ['x'.repeat(5 * 1024 * 1024)];
  const prepared = prepareEvidenceGeometry([oversized, item('E2')]);
  expect(prepared.source.features).toHaveLength(0);
  expect(prepared.omissions[0]?.reason).toMatch(/5 MiB/);
  expect(prepared.omissions[1]?.reason).toMatch(/budget/);
});

it('retains valid polygon holes without rewriting winding or coordinates', () => {
  const source = item('E1', [circle(300), circle(30).map(([x, y]) => [x! / 2, y! / 2])]);
  const prepared = prepareEvidenceGeometry([source]);
  expect(prepared.omissions).toEqual([]);
  expect(prepared.source.features[0]?.geometry).toEqual(source.geometry?.geometry);
});
