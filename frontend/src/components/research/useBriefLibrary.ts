import { useCallback, useState, useSyncExternalStore } from 'react';

import { BRIEF_PAGE_SIZE, fetchBriefs } from '@/lib/api/researchBriefs';
import { useScopedRequest } from '@/lib/hooks/useScopedRequest';
import { useScopedResource } from '@/lib/hooks/useScopedResource';
import { subscribeWorkspaceAccess, workspaceRevision } from '@/lib/workspaceAccess';
import { useAuthStore } from '@/stores/auth';

/** Pagination belongs to the current authority; changed access always restarts at page one. */
export function useBriefLibrary() {
  const actor = useAuthStore(
    (state) => `${state.status}:${state.user?.id}:${state.user?.role}:${state.user?.is_active}`,
  );
  const access = useSyncExternalStore(subscribeWorkspaceAccess, workspaceRevision);
  const key = `${actor}:${access}`;
  const [page, setPage] = useState({ key, offset: 0 });
  const offset = page.key === key ? page.offset : 0;
  const begin = useScopedRequest();
  const loader = useCallback(() => fetchBriefs(begin(), offset), [begin, offset]);
  const resource = useScopedResource(loader);
  const canNext = resource.data?.items.length === BRIEF_PAGE_SIZE && offset < 10_000;
  return {
    ...resource,
    pageNumber: offset / BRIEF_PAGE_SIZE + 1,
    canPrevious: offset > 0,
    canNext,
    previous: () => setPage({ key, offset: Math.max(0, offset - BRIEF_PAGE_SIZE) }),
    next: () => {
      if (canNext && !resource.loading) setPage({ key, offset: offset + BRIEF_PAGE_SIZE });
    },
  };
}
