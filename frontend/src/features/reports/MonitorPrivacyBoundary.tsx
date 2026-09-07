import { Fragment, useSyncExternalStore } from 'react';
import type { ReactNode } from 'react';
import { useAuthStore } from '@/stores/auth';
import { subscribeWorkspaceAccess, workspaceRevision } from '@/lib/workspaceAccess';

/** Discard private forms and historical selections when their authority or parent changes. */
export function MonitorPrivacyBoundary({
  scope,
  children,
}: {
  scope: string;
  children: ReactNode;
}) {
  const actor = useAuthStore(
    (state) => `${state.status}:${state.user?.id}:${state.user?.role}:${state.user?.is_active}`,
  );
  const access = useSyncExternalStore(subscribeWorkspaceAccess, workspaceRevision);
  return <Fragment key={`${actor}:${access}:${scope}`}>{children}</Fragment>;
}
