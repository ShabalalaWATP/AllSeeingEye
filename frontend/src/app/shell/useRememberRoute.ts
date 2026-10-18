import { useEffect } from 'react';
import { useLocation } from 'react-router';

import { rememberAdminRoute, rememberResearchRoute } from '@/stores/workspaceReturn';

/** Records the current route as the place the other workspace's switch returns to. */
export function useRememberRoute(workspace: 'research' | 'admin'): void {
  const { pathname, search } = useLocation();
  useEffect(() => {
    if (workspace === 'admin') rememberAdminRoute(pathname, search);
    else rememberResearchRoute(pathname, search);
  }, [workspace, pathname, search]);
}
