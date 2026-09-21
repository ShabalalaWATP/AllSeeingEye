import { useCallback, useState, useSyncExternalStore } from 'react';

import { fetchReportPage, REPORT_PAGE_SIZE, type ReportOrigin } from '@/lib/api/reportListing';
import { useScopedRequest } from '@/lib/hooks/useScopedRequest';
import { useScopedResource } from '@/lib/hooks/useScopedResource';
import { subscribeWorkspaceAccess, workspaceRevision } from '@/lib/workspaceAccess';
import { useAuthStore } from '@/stores/auth';

/** Page changes retain the chosen section; account or access changes restart its list. */
export function useSavedReports(origin: ReportOrigin) {
  const actor = useAuthStore(
    (state) => `${state.status}:${state.user?.id}:${state.user?.role}:${state.user?.is_active}`,
  );
  const access = useSyncExternalStore(subscribeWorkspaceAccess, workspaceRevision);
  const key = `${actor}:${access}:${origin}`;
  const [page, setPage] = useState({ key, offset: 0 });
  const offset = page.key === key ? page.offset : 0;
  const begin = useScopedRequest();
  const loader = useCallback(
    () => fetchReportPage(origin, offset, begin()),
    [begin, offset, origin],
  );
  const resource = useScopedResource(loader);
  const canNext = resource.data?.has_more === true;
  return {
    ...resource,
    pageNumber: offset / REPORT_PAGE_SIZE + 1,
    canPrevious: offset > 0,
    canNext,
    previous: () => setPage({ key, offset: Math.max(0, offset - REPORT_PAGE_SIZE) }),
    next: () => {
      if (canNext && !resource.loading) setPage({ key, offset: offset + REPORT_PAGE_SIZE });
    },
  };
}
