import type { LiveEvent } from '@/lib/api/eventSchemas';

export type CoverageBounds = readonly [number, number, number, number];

export function insideCoverage(event: LiveEvent, bounds: CoverageBounds | null): boolean {
  if (!bounds) return true;
  if (!event.point) return false;
  const [west, south, east, north] = bounds;
  const { lon, lat } = event.point;
  return (
    lat >= south &&
    lat <= north &&
    (west <= east ? lon >= west && lon <= east : lon >= west || lon <= east)
  );
}

/** Round-robin occupied category/cells, preserving freshness within each cell. */
export function geographicOrder(events: readonly LiveEvent[]): LiveEvent[] {
  const cells = new Map<string, LiveEvent[]>();
  for (const event of events) {
    const point = event.point;
    const key = `${event.category}:${point ? `${Math.floor((point.lon + 180) / 30)}:${Math.floor((point.lat + 90) / 30)}` : 'unlocated'}`;
    const bucket = cells.get(key);
    if (bucket) bucket.push(event);
    else cells.set(key, [event]);
  }
  const result: LiveEvent[] = [];
  let active = [...cells.values()];
  for (let index = 0; active.length; index++) {
    const next: LiveEvent[][] = [];
    for (const bucket of active) {
      const event = bucket[index];
      if (event) result.push(event);
      if (bucket.length > index + 1) next.push(bucket);
    }
    active = next;
  }
  return result;
}
