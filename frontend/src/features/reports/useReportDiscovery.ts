import { useCallback } from 'react';

import { fetchDiscoveryPage, REPORT_PAGE_SIZE } from '@/lib/api/reportListing';
import { useScopedRequest } from '@/lib/hooks/useScopedRequest';
import { useScopedResource } from '@/lib/hooks/useScopedResource';

import { DISCOVERY_PAGES, type DiscoveryState } from './reportDiscovery';

/** One server page for the chosen filter; account or access changes discard stale rows. */
export function useReportDiscovery({ filter, page }: DiscoveryState) {
  const begin = useScopedRequest();
  const offset = (page - 1) * REPORT_PAGE_SIZE;
  const loader = useCallback(
    () => fetchDiscoveryPage(filter, offset, begin()),
    [begin, filter, offset],
  );
  const resource = useScopedResource(loader);
  return {
    ...resource,
    canPrevious: page > 1,
    canNext: resource.data?.has_more === true && page < DISCOVERY_PAGES,
  };
}
