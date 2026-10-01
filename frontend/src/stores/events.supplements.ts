import { fetchEvents, type EventsQuery } from '@/lib/api/events';
import type { Category, LiveEvent, StoreStats } from '@/lib/api/eventSchemas';
import { describeError } from '@/lib/api/errors';
import {
  MARITIME_SNAPSHOT_LIMIT,
  SATELLITE_SNAPSHOT_LIMIT,
  FIRMS_SNAPSHOT_LIMIT,
  AVIATION_SNAPSHOT_LIMIT,
  RESERVED_AIRCRAFT,
} from './events.coverage';

interface SupplementRequest {
  label: string;
  /** The partition the request refreshes, so a partial refresh skips unrelated ones. */
  category: Category;
  query: EventsQuery;
}

/**
 * Supplemental snapshots stop busy categories from hiding ships or public spacecraft.
 * `only` limits them to the partitions a bulk update touched.
 */
export async function loadCoverageSupplements(
  events: LiveEvent[],
  stats: StoreStats,
  signal: AbortSignal,
  scope: Pick<EventsQuery, 'bbox' | 'sampling'> = {},
  only: ReadonlySet<Category> | null = null,
): Promise<{ events: LiveEvent[]; error: string | null; limited: boolean }> {
  const requests: SupplementRequest[] = [];
  const count = (category: 'maritime' | 'space' | 'disaster' | 'aviation') =>
    stats.per_category.find((entry) => entry.category === category)?.count ?? 0;
  if (count('maritime') > events.filter((event) => event.category === 'maritime').length) {
    requests.push({
      label: 'maritime',
      category: 'maritime',
      query: { categories: ['maritime'], limit: MARITIME_SNAPSHOT_LIMIT },
    });
  }
  if (count('aviation') > 0) {
    if (count('aviation') > events.filter((event) => event.category === 'aviation').length)
      requests.push({
        label: 'aviation',
        category: 'aviation',
        query: { categories: ['aviation'], limit: AVIATION_SNAPSHOT_LIMIT },
      });
    requests.push({
      label: 'military aircraft',
      category: 'aviation',
      query: { categories: ['aviation'], military: true, limit: RESERVED_AIRCRAFT },
    });
  }
  if (count('maritime') > MARITIME_SNAPSHOT_LIMIT)
    requests.push({
      label: 'reported military vessel',
      category: 'maritime',
      query: { categories: ['maritime'], military: true, limit: MARITIME_SNAPSHOT_LIMIT },
    });
  if (count('space') > 0) {
    if (count('space') > events.filter((event) => event.category === 'space').length) {
      requests.push({
        label: 'satellite',
        category: 'space',
        query: { categories: ['space'], limit: SATELLITE_SNAPSHOT_LIMIT },
      });
    }
    requests.push({
      label: 'public military and crewed satellite',
      category: 'space',
      query: {
        sources: ['celestrak_skynet', 'celestrak_military', 'celestrak_stations'],
        limit: SATELLITE_SNAPSHOT_LIMIT,
      },
    });
  }
  if (count('disaster') > 0) {
    requests.push({
      label: 'FIRMS thermal detection',
      category: 'disaster',
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
  const additional: LiveEvent[] = [];
  const errors: string[] = [];
  let limited = false;
  // The server admits two event reads per user. Use one slot for this snapshot,
  // leaving room for another panel instead of rejecting later catalogues with 429.
  for (const request of requests) {
    if (only !== null && !only.has(request.category)) continue;
    signal.throwIfAborted();
    try {
      const result = await fetchEvents({ ...request.query, ...scope }, signal);
      signal.throwIfAborted();
      additional.push(...result);
      limited ||= result.length >= (request.query.limit ?? Infinity);
    } catch (failure) {
      signal.throwIfAborted();
      errors.push(`Additional ${request.label} coverage unavailable: ${describeError(failure)}`);
    }
  }
  return { events: additional, error: errors.length ? errors.join(' ') : null, limited };
}
