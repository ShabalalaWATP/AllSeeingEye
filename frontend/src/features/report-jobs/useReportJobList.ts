import { useCallback, useState, useSyncExternalStore } from 'react';
import { useSearchParams } from 'react-router';
import {
  fetchReportJobPage,
  type ReportJobPage,
  type ReportJobStatusGroup,
} from '@/lib/api/reportJobs';
import { useOwnershipScope } from '@/lib/hooks/useOwnershipScope';
import { subscribeWorkspaceAccess, workspaceRevision } from '@/lib/workspaceAccess';
import { useAuthStore } from '@/stores/auth';
import { jobRunning } from './jobLabels';
import { useJobPolling } from './useJobPolling';

const GROUPS: readonly ReportJobStatusGroup[] = ['all', 'attention', 'running', 'finished'];
const pageRunning = (page: ReportJobPage) => page.items.some(jobRunning);

export const parseStatusGroup = (value: string | null): ReportJobStatusGroup =>
  GROUPS.find((group) => group === value) ?? 'all';

/**
 * Filters, including an administrator's explicit "All users" scope, live in the address so
 * links can open a view; the cursor trail does not. It belongs to one filter, ownership scope
 * and account/access state, and resets when any of them changes.
 */
export function useReportJobList() {
  const [params, setParams] = useSearchParams();
  const status = parseStatusGroup(params.get('status'));
  const includeBriefings = params.get('briefings') === '1';
  const ownership = useOwnershipScope();
  const owners = ownership.scope;
  const actor = useAuthStore((state) => `${state.user?.id}:${state.user?.role}`);
  const revision = useSyncExternalStore(subscribeWorkspaceAccess, workspaceRevision);
  const scope = `${status}:${includeBriefings}:${owners}:${actor}:${revision}`;
  const [trail, setTrail] = useState<{ scope: string; cursors: string[] }>({
    scope,
    cursors: [],
  });
  const cursors = trail.scope === scope ? trail.cursors : [];
  const cursor = cursors.at(-1) ?? null;
  const loader = useCallback(
    (signal: AbortSignal) =>
      fetchReportJobPage({ status, includeBriefings, cursor, scope: owners }, signal),
    [status, includeBriefings, cursor, owners],
  );
  const resource = useJobPolling(loader, pageRunning);
  const nextCursor = resource.data?.next_cursor ?? null;

  const changeFilter = (changes: { status?: ReportJobStatusGroup; briefings?: boolean }) =>
    setParams(
      (previous) => {
        const next = new URLSearchParams(previous);
        const group = changes.status ?? status;
        if (group === 'all') next.delete('status');
        else next.set('status', group);
        if (changes.briefings ?? includeBriefings) next.set('briefings', '1');
        else next.delete('briefings');
        return next;
      },
      { replace: true },
    );
  return {
    ...resource,
    status,
    includeBriefings,
    ownership,
    page: cursors.length + 1,
    setStatus: (value: ReportJobStatusGroup) => changeFilter({ status: value }),
    setBriefings: (value: boolean) => changeFilter({ briefings: value }),
    older: nextCursor ? () => setTrail({ scope, cursors: [...cursors, nextCursor] }) : null,
    newer: cursors.length ? () => setTrail({ scope, cursors: cursors.slice(0, -1) }) : null,
    newest: () => setTrail({ scope, cursors: [] }),
  };
}
export type ReportJobList = ReturnType<typeof useReportJobList>;
