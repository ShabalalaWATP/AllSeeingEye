import { useCallback, useEffect, useRef, useState, useSyncExternalStore } from 'react';

import { isApiError } from '@/lib/api/errors';
import { readResearchProgress, type ResearchStage } from '@/lib/api/researchProgress';
import { subscribeWorkspaceAccess, workspaceRevision } from '@/lib/workspaceAccess';
import { useAuthStore } from '@/stores/auth';

type Outcome = 'running' | 'completed' | 'failed' | 'cancelled';
export interface ResearchProgressSnapshot {
  /** Durable jobs use this only while the initial submission is being acknowledged. */
  submission?: boolean;
  stage: ResearchStage | null;
  outcome: Outcome;
  unavailable: boolean;
}
interface Attempt {
  key: string;
  runId: string;
  request: AbortController;
  polling: AbortController;
  timer: number | null;
  registered: boolean;
  deadline: number;
  snapshot: ResearchProgressSnapshot;
}

function accessKey() {
  const user = useAuthStore.getState().user;
  return `${user?.id ?? ''}:${user?.role ?? ''}:${user?.is_active ?? false}:${workspaceRevision()}`;
}

function stopPolling(attempt: Attempt) {
  attempt.polling.abort();
  if (attempt.timer !== null) window.clearTimeout(attempt.timer);
  attempt.timer = null;
}

const terminal = new Set<ResearchStage>(['completed', 'failed', 'cancelled', 'timed_out']);

/** One request and one non-overlapping status poll, scoped to this mounted account view. */
export function useResearchProgress() {
  const user = useAuthStore((state) => state.user);
  const revision = useSyncExternalStore(subscribeWorkspaceAccess, workspaceRevision);
  const key = `${user?.id ?? ''}:${user?.role ?? ''}:${user?.is_active ?? false}:${revision}`;
  const attempt = useRef<Attempt | null>(null);
  const [state, setState] = useState<{ key: string; snapshot: ResearchProgressSnapshot } | null>(
    null,
  );

  useEffect(() => {
    return () => {
      if (attempt.current !== null) {
        attempt.current.request.abort();
        stopPolling(attempt.current);
        attempt.current = null;
      }
    };
  }, [key]);

  const publish = useCallback((current: Attempt) => {
    if (attempt.current !== current || current.key !== accessKey()) return;
    setState({ key: current.key, snapshot: { ...current.snapshot } });
  }, []);

  const begin = useCallback(() => {
    if (attempt.current !== null) {
      attempt.current.request.abort();
      stopPolling(attempt.current);
    }
    const current: Attempt = {
      key: accessKey(),
      runId: crypto.randomUUID(),
      request: new AbortController(),
      polling: new AbortController(),
      timer: null,
      registered: false,
      deadline: Date.now() + 15 * 60_000,
      snapshot: { stage: null, outcome: 'running', unavailable: false },
    };
    attempt.current = current;
    publish(current);
    const isCurrent = () =>
      attempt.current === current && current.key === accessKey() && !current.polling.signal.aborted;
    const poll = async () => {
      if (!isCurrent()) return;
      if (Date.now() >= current.deadline) {
        current.snapshot.unavailable = true;
        publish(current);
        return;
      }
      try {
        const receipt = await readResearchProgress(current.runId, current.polling.signal);
        if (!isCurrent()) return;
        if (receipt.id !== current.runId) throw new Error('Mismatched run receipt');
        current.registered = true;
        current.deadline = Math.min(current.deadline, Date.parse(receipt.expires_at));
        current.snapshot = { ...current.snapshot, stage: receipt.stage, unavailable: false };
        publish(current);
        if (terminal.has(receipt.stage)) return;
      } catch (error) {
        if (!isCurrent()) return;
        // The POST may not have registered when the first status request arrives.
        current.snapshot.unavailable = !(
          isApiError(error) &&
          error.status === 404 &&
          !current.registered
        );
        publish(current);
      }
      if (isCurrent()) current.timer = window.setTimeout(() => void poll(), 2000);
    };
    current.timer = window.setTimeout(() => void poll(), 2000);
    return { runId: current.runId, signal: current.request.signal };
  }, [publish]);

  const finish = useCallback(
    (outcome: Exclude<Outcome, 'running'>) => {
      const current = attempt.current;
      if (current?.snapshot.outcome !== 'running') return;
      stopPolling(current);
      current.snapshot.outcome = current.snapshot.stage === 'completed' ? 'completed' : outcome;
      publish(current);
    },
    [publish],
  );

  const cancel = useCallback(() => {
    const current = attempt.current;
    if (current?.snapshot.outcome !== 'running') return;
    current.request.abort();
    stopPolling(current);
    current.snapshot.outcome = 'cancelled';
    publish(current);
  }, [publish]);

  // Clear old state when access changes, including a later return to the same account.
  if (state !== null && state.key !== key) setState(null);
  const snapshot = state?.key === key ? state.snapshot : null;
  return { begin, finish, cancel, snapshot, active: snapshot?.outcome === 'running' };
}
