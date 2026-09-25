import { useCallback, useState } from 'react';

import type { ApiError } from '@/lib/api/errors';
import { fetchReportJobs } from '@/lib/api/reportJobs';
import type { ReportJob } from '@/lib/api/reportJobs';
import type { Alert } from '@/lib/api/warning';
import { usePolledResource } from '@/lib/hooks/usePolledResource';

import { markNotificationsSeen, notificationsSeenAt } from './notificationSeen';
import { SHELL_POLL_MS, useShellAlertsResource } from './useShellAlerts';

/** How many alerts and finished research runs the bell lists before pointing at the full page. */
export const BELL_SHOWN = 5;

const FINISHED: ReadonlySet<ReportJob['status']> = new Set(['completed', 'needs_review', 'failed']);
// The shell never cancels this read; the scoped resource discards stale answers instead.
const loadJobs = () => fetchReportJobs(new AbortController().signal);

const time = (iso: string) => {
  const value = Date.parse(iso);
  return Number.isNaN(value) ? 0 : value;
};
const newestFirst = <T>(items: readonly T[], at: (item: T) => string) =>
  [...items].sort((a, b) => time(at(b)) - time(at(a)));

export interface FinishedJob {
  job: ReportJob;
  /** Finished after the bell was last opened. */
  isNew: boolean;
}

export interface BellSection<T> {
  items: T[];
  total: number;
  error: ApiError | null;
}

export interface NotificationBellState {
  open: boolean;
  /** True until both sources have answered once, successfully or not. */
  loading: boolean;
  /** Unacknowledged alerts plus research that finished since the bell was last opened. */
  unread: number;
  alerts: BellSection<Alert>;
  jobs: BellSection<FinishedJob>;
  toggle: () => void;
  close: () => void;
  retry: () => void;
}

/**
 * Awareness for the top bar: unacknowledged alerts from the last day and research runs that
 * finished since the user last opened the bell. Both come from endpoints that already apply
 * the caller's access scope. Mount it per user so the last-seen time follows the account.
 */
export function useNotificationBell(userId: string): NotificationBellState {
  const alerts = useShellAlertsResource();
  const jobs = usePolledResource(loadJobs, SHELL_POLL_MS);
  const [seenAt, setSeenAt] = useState(() => notificationsSeenAt(userId));
  // The previous last-seen time while the bell is open, so new items stay marked as new.
  const [openedFrom, setOpenedFrom] = useState<number | null>(null);

  const unacknowledged = newestFirst(
    alerts.data?.items.filter((item) => item.acknowledged_at === null) ?? [],
    (item) => item.fired_at,
  );
  const finished = newestFirst(
    (jobs.data ?? []).filter((job) => FINISHED.has(job.status)),
    (job) => job.updated_at,
  );
  const unseenJobs = finished.filter((job) => time(job.updated_at) > seenAt).length;
  const since = openedFrom ?? seenAt;

  const close = useCallback(() => setOpenedFrom(null), []);
  const toggle = useCallback(() => {
    if (openedFrom !== null) {
      setOpenedFrom(null);
      return;
    }
    setOpenedFrom(seenAt);
    setSeenAt(markNotificationsSeen(userId));
  }, [openedFrom, seenAt, userId]);
  const { error: alertsError, reload: reloadAlerts } = alerts;
  const { error: jobsError, reload: reloadJobs } = jobs;
  const retry = useCallback(() => {
    if (alertsError) void reloadAlerts();
    if (jobsError) void reloadJobs();
  }, [alertsError, jobsError, reloadAlerts, reloadJobs]);

  return {
    open: openedFrom !== null,
    loading: alerts.loading || jobs.loading,
    unread: unacknowledged.length + unseenJobs,
    alerts: {
      items: unacknowledged.slice(0, BELL_SHOWN),
      total: unacknowledged.length,
      error: alerts.error,
    },
    jobs: {
      items: finished
        .slice(0, BELL_SHOWN)
        .map((job) => ({ job, isNew: time(job.updated_at) > since })),
      total: finished.length,
      error: jobs.error,
    },
    toggle,
    close,
    retry,
  };
}
