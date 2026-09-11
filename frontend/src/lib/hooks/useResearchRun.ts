import { useCallback, useEffect, useRef, useState, useSyncExternalStore } from 'react';
import { useNavigate } from 'react-router';
import { createReportJob, type ReportJobCreate } from '@/lib/api/reportJobs';
import type { ReportRequest } from '@/lib/api/reports';
import { asApiError, type ApiError } from '@/lib/api/errors';
import { subscribeWorkspaceAccess, workspaceRevision } from '@/lib/workspaceAccess';
import { useAuthStore } from '@/stores/auth';
import type { ResearchProgressSnapshot } from './useResearchProgress';
import { useScopedRequest } from './useScopedRequest';

function authority() {
  const state = useAuthStore.getState();
  return `${state.status}:${state.user?.id}:${state.user?.role}:${state.user?.is_active}:${workspaceRevision()}`;
}
interface Attempt {
  key: string;
  fingerprint: string;
  body: ReportJobCreate;
}
interface Submission {
  key: string;
  busy: boolean;
  error: ApiError | null;
  snapshot: ResearchProgressSnapshot | null;
}

/** Submission is brief. Accepted work belongs to the server, not this mounted page. */
export function useResearchRun() {
  const navigate = useNavigate();
  const actor = useAuthStore(
    (state) => `${state.status}:${state.user?.id}:${state.user?.role}:${state.user?.is_active}`,
  );
  const revision = useSyncExternalStore(subscribeWorkspaceAccess, workspaceRevision);
  const key = `${actor}:${revision}`;
  const begin = useScopedRequest();
  const attempt = useRef<Attempt | null>(null);
  const pending = useRef<AbortController | null>(null);
  const sequence = useRef(0);
  const [state, setState] = useState<Submission>({ key, busy: false, error: null, snapshot: null });
  useEffect(
    () => () => {
      sequence.current++;
      pending.current?.abort();
      pending.current = null;
      attempt.current = null;
    },
    [key],
  );

  const submit = async (current: Attempt) => {
    const session = useAuthStore.getState();
    if (
      pending.current ||
      current.key !== authority() ||
      session.status !== 'authenticated' ||
      !session.user?.is_active
    )
      return;
    const controller = new AbortController();
    pending.current = controller;
    const id = ++sequence.current;
    const signal = AbortSignal.any([begin(), controller.signal]);
    const isCurrent = () =>
      !signal.aborted && id === sequence.current && current.key === authority();
    setState({
      key,
      busy: true,
      error: null,
      snapshot: { stage: null, outcome: 'running', unavailable: false, submission: true },
    });
    try {
      const job = await createReportJob(current.body, signal);
      if (isCurrent()) {
        setState({ key, busy: false, error: null, snapshot: null });
        await navigate(`/research/jobs/${job.id}`);
      }
    } catch (caught) {
      if (isCurrent())
        setState({
          key,
          busy: false,
          error: asApiError(caught),
          snapshot: { stage: null, outcome: 'failed', unavailable: false, submission: true },
        });
    } finally {
      if (pending.current === controller) pending.current = null;
    }
  };
  const run = async (report: ReportRequest) => {
    if (pending.current) return;
    const fingerprint = JSON.stringify(report);
    if (attempt.current?.key !== key || attempt.current.fingerprint !== fingerprint)
      attempt.current = {
        key,
        fingerprint,
        body: { request_id: crypto.randomUUID(), report: structuredClone(report) },
      };
    await submit(attempt.current);
  };
  const cancel = useCallback(() => {
    if (!pending.current) return;
    sequence.current++;
    pending.current.abort();
    pending.current = null;
    setState({
      key,
      busy: false,
      error: null,
      snapshot: { stage: null, outcome: 'cancelled', unavailable: false, submission: true },
    });
  }, [key]);
  const clearError = useCallback(() => setState((value) => ({ ...value, error: null })), []);
  const visible = state.key === key ? state : { busy: false, error: null, snapshot: null };
  return {
    run,
    busy: visible.busy,
    error: visible.error,
    clearError,
    retry: async () => {
      if (attempt.current) await submit(attempt.current);
    },
    progress: { snapshot: visible.snapshot, active: visible.busy, cancel },
  };
}
