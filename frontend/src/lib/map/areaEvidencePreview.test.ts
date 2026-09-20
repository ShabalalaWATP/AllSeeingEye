import { expect, it } from 'vitest';
import { liveEvent } from '@/test/fixtures.events';
import { rectangleArea } from './areaGeometry';
import { previewAreaEvidence } from './areaEvidencePreview';

const since = Date.parse('2026-09-05T00:00:00Z');
const until = since + 86400000;
const area = rectangleArea({ west: 0, east: 2, south: 0, north: 2 });
const inside = liveEvent({ point: { lon: 1, lat: 1 } });

it('separates precise containment from approximate, country and unlocated evidence', () => {
  const result = previewAreaEvidence(
    area,
    [
      inside,
      liveEvent({ id: 'edge', point: { lon: 0, lat: 1 } }),
      liveEvent({ id: 'outside', point: { lon: 3, lat: 1 } }),
      liveEvent({ id: 'city', point: { lon: 1, lat: 1 }, geo_confidence: 'city' }),
      liveEvent({ id: 'country', point: { lon: 1, lat: 1 }, geo_confidence: 'country' }),
      liveEvent({ id: 'approx-outside', point: { lon: 3, lat: 1 }, geo_confidence: 'city' }),
      liveEvent({ id: 'none', point: null, geo_confidence: 'none' }),
      liveEvent({ id: 'old', published_at: '2026-09-04T23:59:59Z' }),
      liveEvent({ id: 'end', published_at: '2026-09-06T00:00:00Z' }),
      liveEvent({ id: 'unknown', published_at: null }),
    ],
    since,
    until,
  );
  expect(result.inside.map((event) => event.id)).toEqual(['e1', 'edge']);
  expect(result.approximate).toHaveLength(1);
  expect(result.approximateOutside).toBe(1);
  expect(result.country).toBe(1);
  expect(result.unlocated).toBe(1);
  expect(result.outside).toBe(1);
  expect(result.outOfPeriod).toBe(2);
  expect(result.unknownTime).toBe(1);
});

it('respects polygon holes and pre-split antimeridian areas', () => {
  const withHole = structuredClone(area);
  const geometry = withHole.features[0]!.geometry;
  if (geometry.type !== 'Polygon') throw new Error('Expected polygon');
  geometry.coordinates.push([
    [0.5, 0.5],
    [1.5, 0.5],
    [1.5, 1.5],
    [0.5, 1.5],
    [0.5, 0.5],
  ]);
  expect(previewAreaEvidence(withHole, [inside], since, until).inside).toHaveLength(0);
  const split = rectangleArea({ west: 179, east: -179, south: -1, north: 1 });
  const events = [179.5, -179.5, 0].map((lon, id) =>
    liveEvent({ id: String(id), point: { lon, lat: 0 } }),
  );
  expect(previewAreaEvidence(split, events, since, until).inside).toHaveLength(2);
});
