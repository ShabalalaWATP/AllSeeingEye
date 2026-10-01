import { useCallback, useEffect, useState } from 'react';

import { fetchBell } from '@/lib/api/bell';
import type { Bell, BellAlert, BellMention, BellPreferences } from '@/lib/api/bell';
import type { ApiError } from '@/lib/api/errors';
import { fetchReportJobs } from '@/lib/api/reportJobs';
import type { ReportJob } from '@/lib/api/reportJobs';
import { subscribeBellChanges } from '@/lib/bellSignal';
import { usePolledResource } from '@/lib/hooks/usePolledResource';

import { markNotificationsSeen, notificationsSeenAt } from './notificationSeen';

/** How many finished research runs the bell lists before pointing at the full page. */
export const BELL_SHOWN = 5;
export const SHELL_POLL_MS = 60_000;

const FINISHED: ReadonlySet<ReportJob['status']> = new Set(['completed', 'needs_review', 'failed']);
// The polled resources abort these reads on unmount, a hidden tab, an access change or a newer load.
const loadJobs = (signal: AbortSignal) => fetchReportJobs(signal);
const loadBell = (signal: AbortSignal) => fetchBell(signal);

const time = (iso: string) => {
  const value = Date.parse(iso);
  return Number.isNaN(value) ? 0 : value;
};

export interface FinishedJob {
  job: ReportJob;
  /** Finished after the bell was last opened. */
  isNew: boolean;
}

export interface BellSection<T> {
  items: T[];
  total: number;
  error: ApiError | null;
  /** The account chose not to see this kind in the bell. */
  muted: boolean;
}

export interface NotificationBellState {
  open: boolean;
  /** True until both sources have answered once, successfully or not. */
  loading: boolean;
  /** Unacknowledged alerts in the window, unread mentions and newly finished research. */
  unread: number;
  /** The alert window, the same as the Alerts page. */
  windowDays: number;
  alerts: BellSection<BellAlert>;
  /** Unread board mentions; `total` is the capped unread count. */
  mentions: BellSection<BellMention>;
  jobs: BellSection<FinishedJob>;
  preferences: BellPreferences | null;
  toggle: () => void;
  close: () => void;
  retry: () => void;
  /** Refetch the bell, keeping what is shown until the server answers. */
  refresh: () => Promise<void>;
  /** Apply a server answer at once, before the refetch confirms it. */
  updateBell: (update: (bell: Bell) => Bell) => void;
}

/**
 * Awareness for the top bar. Alerts come from the bell endpoint, already limited in SQL to
 * the caller's own and current teams' records from the last seven days, without muted rules.
 * Research runs that finished since the bell was last opened come from the job list. A
 * bell change from another session reaches open streams and refetches the summary here.
 * Mount it per user so the last-seen time follows the account.
 */
export function useNotificationBell(userId: string): NotificationBellState {
  const bell = usePolledResource(loadBell, SHELL_POLL_MS);
  const jobs = usePolledResource(loadJobs, SHELL_POLL_MS);
  const [seenAt, setSeenAt] = useState(() => notificationsSeenAt(userId));
  // The previous last-seen time while the bell is open, so new items stay marked as new.
  const [openedFrom, setOpenedFrom] = useState<number | null>(null);
  const { refresh, setData } = bell;
  useEffect(() => subscribeBellChanges(() => void refresh()), [refresh]);

  const preferences = bell.data?.preferences ?? null;
  const researchMuted = preferences?.muted_kinds.includes('research') ?? false;
  const finished = (jobs.data ?? [])
    .filter((job) => FINISHED.has(job.status))
    .sort((a, b) => time(b.updated_at) - time(a.updated_at));
  const unseenJobs = researchMuted
    ? 0
    : finished.filter((job) => time(job.updated_at) > seenAt).length;
  const since = openedFrom ?? seenAt;
  const alerts = bell.data?.alerts;
  const mentions = bell.data?.mentions;

  const close = useCallback(() => setOpenedFrom(null), []);
  const toggle = useCallback(() => {
    if (openedFrom !== null) {
      setOpenedFrom(null);
      return;
    }
    setOpenedFrom(seenAt);
    setSeenAt(markNotificationsSeen(userId));
    // Reconcile with changes made in another session before the reader acts.
    void refresh();
  }, [openedFrom, seenAt, userId, refresh]);
  const { error: bellError, reload: reloadBell } = bell;
  const { error: jobsError, reload: reloadJobs } = jobs;
  const retry = useCallback(() => {
    if (bellError) void reloadBell();
    if (jobsError) void reloadJobs();
  }, [bellError, jobsError, reloadBell, reloadJobs]);
  const updateBell = useCallback(
    (update: (value: Bell) => Bell) => setData((value) => (value === null ? value : update(value))),
    [setData],
  );

  return {
    open: openedFrom !== null,
    loading: bell.loading || jobs.loading,
    unread:
      (alerts?.muted ? 0 : (alerts?.total ?? 0)) +
      (mentions?.muted ? 0 : (mentions?.unread ?? 0)) +
      unseenJobs,
    windowDays: bell.data?.window_days ?? 7,
    alerts: {
      items: alerts?.items ?? [],
      total: alerts?.total ?? 0,
      error: bell.error,
      muted: alerts?.muted ?? false,
    },
    mentions: {
      items: mentions?.items ?? [],
      total: mentions?.unread ?? 0,
      error: bell.error,
      muted: mentions?.muted ?? false,
    },
    jobs: {
      items: researchMuted
        ? []
        : finished
            .slice(0, BELL_SHOWN)
            .map((job) => ({ job, isNew: time(job.updated_at) > since })),
      total: researchMuted ? 0 : finished.length,
      error: jobs.error,
      muted: researchMuted,
    },
    preferences,
    toggle,
    close,
    retry,
    refresh,
    updateBell,
  };
}
