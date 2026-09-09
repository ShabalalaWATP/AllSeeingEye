import { fetchEvents, type EventsQuery } from '@/lib/api/events';
import type { LiveEvent, StoreStats } from '@/lib/api/eventSchemas';
import { describeError } from '@/lib/api/errors';
import {
  MARITIME_SNAPSHOT_LIMIT,
  SATELLITE_SNAPSHOT_LIMIT,
  FIRMS_SNAPSHOT_LIMIT,
  AVIATION_SNAPSHOT_LIMIT,
  RESERVED_AIRCRAFT,
} from './events.coverage';

/** Supplemental snapshots stop busy categories from hiding ships or public spacecraft. */
export async function loadCoverageSupplements(
  events: LiveEvent[],
  stats: StoreStats,
  signal: AbortSignal,
  scope: Pick<EventsQuery, 'bbox' | 'sampling'> = {},
): Promise<{ events: LiveEvent[]; error: string | null; limited: boolean }> {
  const requests: { label: string; query: EventsQuery }[] = [];
  const count = (category: 'maritime' | 'space' | 'disaster' | 'aviation') =>
    stats.per_category.find((entry) => entry.category === category)?.count ?? 0;
  if (count('maritime') > events.filter((event) => event.category === 'maritime').length) {
    requests.push({
      label: 'maritime',
      query: { categories: ['maritime'], limit: MARITIME_SNAPSHOT_LIMIT },
    });
  }
  if (count('aviation') > 0) {
    if (count('aviation') > events.filter((event) => event.category === 'aviation').length)
      requests.push({
        label: 'aviation',
        query: { categories: ['aviation'], limit: AVIATION_SNAPSHOT_LIMIT },
      });
    requests.push({
      label: 'military aircraft',
      query: { categories: ['aviation'], military: true, limit: RESERVED_AIRCRAFT },
    });
  }
  if (count('maritime') > MARITIME_SNAPSHOT_LIMIT)
    requests.push({
      label: 'reported military vessel',
      query: { categories: ['maritime'], military: true, limit: MARITIME_SNAPSHOT_LIMIT },
    });
  if (count('space') > 0) {
    if (count('space') > events.filter((event) => event.category === 'space').length) {
      requests.push({
        label: 'satellite',
        query: { categories: ['space'], limit: SATELLITE_SNAPSHOT_LIMIT },
      });
    }
    requests.push({
      label: 'public military and crewed satellite',
      query: {
        sources: ['celestrak_skynet', 'celestrak_military', 'celestrak_stations'],
        limit: SATELLITE_SNAPSHOT_LIMIT,
      },
    });
  }
  if (count('disaster') > 0) {
    requests.push({
      label: 'FIRMS thermal detection',
      query: {
        sources: [
          'firms_viirs_noaa20',
          'firms_public_noaa20',
          'firms_viirs_noaa21',
          'firms_public_noaa21',
        ],
        limit: FIRMS_SNAPSHOT_LIMIT,
      },
    });
  }
  const results = await Promise.allSettled(
    requests.map(({ query }) => fetchEvents({ ...query, ...scope }, signal)),
  );
  const additional: LiveEvent[] = [];
  const errors: string[] = [];
  let limited = false;
  results.forEach((result, index) => {
    const request = requests[index];
    if (!request) return;
    if (result.status === 'fulfilled') {
      additional.push(...result.value);
      limited ||= result.value.length >= (request.query.limit ?? Infinity);
    } else {
      errors.push(
        `Additional ${request.label} coverage unavailable: ${describeError(result.reason)}`,
      );
    }
  });
  return { events: additional, error: errors.length ? errors.join(' ') : null, limited };
}
