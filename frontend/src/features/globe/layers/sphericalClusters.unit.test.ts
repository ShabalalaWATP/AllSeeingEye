import { expect, it } from 'vitest';
import { liveEvent } from '@/test/fixtures';
import { clusterEvents } from './clusters';

const point = (id: string, lon: number, lat: number) =>
  liveEvent({ id, category: 'news', point: { lon, lat } });

it('groups observations across the date line and keeps the centre at the date line', () => {
  const events = [point('a', 179.6, 0.1), point('b', -179.6, 0.1), point('c', 180, 0.2)];
  const result = clusterEvents(events, 3);
  expect(result.clusters).toHaveLength(1);
  expect(result.clusters[0]).toMatchObject({ count: 3, category: 'news' });
  expect(Math.abs(result.clusters[0]!.lon)).toBeCloseTo(180, 3);
  expect(result.clusters[0]!.lat).toBeCloseTo(0.1333, 3);
  expect(result.loose).toEqual([]);
  expect(events[1]!.point!.lon).toBe(-179.6);
});

it.each([89, -89])(
  'groups nearby observations around latitude %s without inventing an equatorial centre',
  (lat) => {
    const result = clusterEvents(
      [point('a', -120, lat), point('b', 0, lat), point('c', 120, lat)],
      3,
    );
    expect(result.clusters).toHaveLength(1);
    expect(result.clusters[0]!.lat).toBeCloseTo(Math.sign(lat) * 90, 5);
    expect(Number.isFinite(result.clusters[0]!.lon)).toBe(true);
  },
);

it('keeps category boundaries and counts every located observation exactly once', () => {
  const events = Array.from({ length: 5000 }, (_, index) => {
    const event = point(String(index), index % 2 ? -179.8 : 179.8, (index % 3) * 0.1);
    return { ...event, category: index % 2 ? ('news' as const) : ('conflict' as const) };
  });
  const result = clusterEvents(events, 6);
  expect(result.clusters).toHaveLength(2);
  expect(result.clusters.reduce((sum, item) => sum + item.count, result.loose.length)).toBe(5000);
  expect(new Set(result.clusters.map((item) => item.category)).size).toBe(2);
  const reversed = clusterEvents([...events].reverse(), 6);
  expect(reversed.clusters.map((item) => item.id).sort()).toEqual(
    result.clusters.map((item) => item.id).sort(),
  );
});

it.each([0, -1, Number.NaN, Number.POSITIVE_INFINITY, 180])(
  'rejects invalid angular cell width %s',
  (width) => {
    expect(() => clusterEvents([], width)).toThrow(RangeError);
  },
);
