import { useEffect, useState, useSyncExternalStore } from 'react';

import { ensureDailyBriefing, type DailyBriefing } from '@/lib/api/dailyBriefing';
import { asApiError, ApiError } from '@/lib/api/errors';
import { fetchReportJob } from '@/lib/api/reportJobs';
import { fetchReport, type Report } from '@/lib/api/reports';
import { subscribeWorkspaceAccess, workspaceRevision } from '@/lib/workspaceAccess';
import { useAuthStore } from '@/stores/auth';

interface State<T extends DailyBriefing> {
  briefing: T | null;
  report: Report | null;
  error: ApiError | null;
  loading: boolean;
  owner: string | undefined;
  access: number;
  loader: (signal: AbortSignal) => Promise<T>;
}

/** Poll only the active job; a completed briefing is checked again once its day expires. */
export function useDailyBriefing(ensure: typeof ensureDailyBriefing = ensureDailyBriefing) {
  return useBriefing(ensure);
}

/** A changed loader identifies a different report scope, so previous content hides immediately. */
export function useBriefing<T extends DailyBriefing>(ensure: (signal: AbortSignal) => Promise<T>) {
  const owner = useAuthStore((state) => state.user?.id);
  const access = useSyncExternalStore(subscribeWorkspaceAccess, workspaceRevision);
  const [attempt, setAttempt] = useState(0);
  const [state, setState] = useState<State<T>>({
    briefing: null,
    report: null,
    error: null,
    loading: true,
    owner,
    access,
    loader: ensure,
  });

  useEffect(() => {
    const effectAccess = workspaceRevision();
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout> | undefined;
    let startDeferred = false;
    const signal = controller.signal;
    const update = (value: Omit<State<T>, 'owner' | 'access' | 'loader'>) => {
      if (!signal.aborted) setState({ ...value, owner, access: effectAccess, loader: ensure });
    };
    const inspect = async (briefing: T) => {
      try {
        if (signal.aborted) return;
        const job = briefing.job;
        const pending = job.status === 'queued' || job.status === 'running';
        const report =
          !pending && job.report_id ? await fetchReport(job.report_id, undefined, signal) : null;
        if (report && report.report.id !== job.report_id) {
          throw new ApiError(
            502,
            'invalid_response',
            'The server returned a different briefing. Please retry.',
          );
        }
        update({ briefing, report, error: null, loading: false });
        // The awaited report request may have been aborted after the first check.
        // eslint-disable-next-line @typescript-eslint/no-unnecessary-condition
        if (signal.aborted) return;
        if (pending) {
          timer = setTimeout(() => {
            void poll(briefing);
          }, 5_000);
        } else {
          timer = setTimeout(
            () => {
              void start();
            },
            Math.max(60_000, new Date(briefing.next_refresh_at).getTime() - Date.now()),
          );
        }
      } catch (error) {
        update({ briefing, report: null, error: asApiError(error), loading: false });
      }
    };
    const poll = async (briefing: T) => {
      try {
        if (document.visibilityState === 'hidden') {
          timer = setTimeout(() => {
            void poll(briefing);
          }, 5_000);
          return;
        }
        await inspect({ ...briefing, job: await fetchReportJob(briefing.job.id, signal) });
      } catch (error) {
        update({ briefing, report: null, error: asApiError(error), loading: false });
      }
    };
    const start = async () => {
      if (signal.aborted) return;
      if (document.visibilityState === 'hidden') {
        startDeferred = true;
        return;
      }
      startDeferred = false;
      try {
        await inspect(await ensure(signal));
      } catch (error) {
        update({ briefing: null, report: null, error: asApiError(error), loading: false });
      }
    };
    const resumeVisible = () => {
      if (startDeferred && document.visibilityState === 'visible') void start();
    };
    document.addEventListener('visibilitychange', resumeVisible);
    const unsubscribe = subscribeWorkspaceAccess(() => {
      controller.abort();
      clearTimeout(timer);
      setState({
        briefing: null,
        report: null,
        loading: false,
        owner,
        access: workspaceRevision(),
        loader: ensure,
        error: new ApiError(
          409,
          'access_changed',
          'Your access changed. Reload the briefing to continue.',
        ),
      });
    });
    void start();
    return () => {
      controller.abort();
      clearTimeout(timer);
      document.removeEventListener('visibilitychange', resumeVisible);
      unsubscribe();
    };
  }, [owner, attempt, ensure]);

  const visible = state.owner === owner && state.access === access && state.loader === ensure;
  return {
    briefing: visible ? state.briefing : null,
    report: visible ? state.report : null,
    error: visible ? state.error : null,
    loading: !visible || state.loading,
    retry: () => {
      setState({
        briefing: null,
        report: null,
        error: null,
        loading: true,
        owner,
        access,
        loader: ensure,
      });
      setAttempt((value) => value + 1);
    },
  };
}
