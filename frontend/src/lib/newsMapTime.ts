import type { LiveEvent } from '@/lib/api/eventSchemas';

/** A separate map clock must never turn an indexing date into a publication date. */
export function mapRecordTime(event: LiveEvent): number {
  if (event.source_id !== 'gdelt_news' || event.category !== 'news')
    return Date.parse(event.published_at ?? '');
  const date = event.source_dates?.find(
    (item) =>
      item.field === 'DATEADDED' &&
      item.method === 'gdelt-dateadded-utc-v1' &&
      item.role === 'unspecified' &&
      item.basis === 'source_spec' &&
      item.status === 'resolved' &&
      item.precision === 'instant',
  );
  if (!date?.value || !/^\d{14}$/.test(date.raw_text)) return NaN;
  const raw = date.raw_text;
  const expected = `${raw.slice(0, 4)}-${raw.slice(4, 6)}-${raw.slice(6, 8)}T${raw.slice(8, 10)}:${raw.slice(10, 12)}:${raw.slice(12, 14)}Z`;
  return Date.parse(date.value) === Date.parse(expected) ? Date.parse(date.value) : NaN;
}

export function filterMapWindow(
  events: LiveEvent[],
  hours: number | null,
  now: number,
): LiveEvent[] {
  if (hours === null) return events;
  const since = now - hours * 3_600_000;
  return events.filter((event) => {
    const at = mapRecordTime(event);
    return Number.isFinite(at) && at >= since;
  });
}
