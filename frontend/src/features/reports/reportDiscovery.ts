/**
 * Filters for the one saved-report view. The filter and page live in the address, so
 * back and forward navigation and a return from a report keep the reader's place.
 */
import { REPORT_PAGE_SIZE, type DiscoveryFilter, type ReportOrigin } from '@/lib/api/reportListing';

/** Server discovery covers the latest 1,000 matching reports, so 20 pages of 50. */
export const DISCOVERY_PAGES = 1000 / REPORT_PAGE_SIZE;

// Typed as complete records: a new server origin must be named here before it appears.
export const ORIGIN_LABELS: Record<ReportOrigin, string> = {
  research: 'Research',
  subscription: 'Subscription update',
  geolocation: 'Geolocation assessment',
};

export const FILTER_LABELS: Record<DiscoveryFilter, string> = {
  requested: 'All requested work',
  research: 'Research',
  subscription: 'Subscription updates',
  geolocation: 'Geolocation assessments',
};

const NO_MATCH: Record<ReportOrigin, string> = {
  research: 'No research reports match this filter.',
  subscription: 'No subscription updates match this filter.',
  geolocation: 'No geolocation assessments match this filter.',
};

export const DISCOVERY_FILTERS = Object.keys(FILTER_LABELS) as DiscoveryFilter[];

function isFilter(value: string | null): value is DiscoveryFilter {
  return value !== null && DISCOVERY_FILTERS.some((filter) => filter === value);
}

export interface DiscoveryState {
  filter: DiscoveryFilter;
  page: number;
}

/** Unknown or out-of-range values fall back to all requested work, first page. */
export function readDiscovery(params: URLSearchParams): DiscoveryState {
  const origin = params.get('origin');
  const page = Number(params.get('page') ?? '1');
  return {
    filter: isFilter(origin) ? origin : 'requested',
    page: Number.isInteger(page) && page >= 1 && page <= DISCOVERY_PAGES ? page : 1,
  };
}

export function discoveryParams(state: DiscoveryState): URLSearchParams {
  const params = new URLSearchParams();
  if (state.filter !== 'requested') params.set('origin', state.filter);
  if (state.page > 1) params.set('page', String(state.page));
  return params;
}

export function originLabel(origin: ReportOrigin): string {
  return ORIGIN_LABELS[origin];
}

export function noMatchText(filter: DiscoveryFilter): string {
  return filter === 'requested'
    ? 'No saved reports yet. Ask a question to create your first report.'
    : NO_MATCH[filter];
}
