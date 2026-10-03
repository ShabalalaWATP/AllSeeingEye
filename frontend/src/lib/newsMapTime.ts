import type { LiveEvent } from '@/lib/api/eventSchemas';

interface CachedTime {
  indexed: boolean;
  value: string | null | undefined;
  raw: string | undefined;
  time: number;
}

// Stream/snapshot replacements get a new identity. Check the actual parsing inputs as well:
// public DTO callers may correct a record or its source-date declarations in place.
const parsedTimes = new WeakMap<LiveEvent, CachedTime>();

function indexingTime(value: string | null | undefined, raw: string | undefined): number {
  if (!value || !raw || !/^\d{14}$/.test(raw)) return NaN;
  const expected = `${raw.slice(0, 4)}-${raw.slice(4, 6)}-${raw.slice(6, 8)}T${raw.slice(8, 10)}:${raw.slice(10, 12)}:${raw.slice(12, 14)}Z`;
  const time = Date.parse(value);
  return time === Date.parse(expected) ? time : NaN;
}

/** A separate map clock must never turn an indexing date into a publication date. */
export function mapRecordTime(event: LiveEvent): number {
  const indexed = event.source_id === 'gdelt_news' && event.category === 'news';
  // Reselect on every call: eligibility, order or nested fields can change without a new array.
  const date = indexed
    ? event.source_dates?.find(
        (item) =>
          item.field === 'DATEADDED' &&
          item.method === 'gdelt-dateadded-utc-v1' &&
          item.role === 'unspecified' &&
          item.basis === 'source_spec' &&
          item.status === 'resolved' &&
          item.precision === 'instant',
      )
    : undefined;
  const value = indexed ? date?.value : event.published_at;
  const raw = date?.raw_text;
  const cached = parsedTimes.get(event);
  if (cached?.indexed === indexed && cached.value === value && cached.raw === raw)
    return cached.time;
  const time = indexed ? indexingTime(value, raw) : Date.parse(value ?? '');
  parsedTimes.set(event, { indexed, value, raw, time });
  return time;
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
