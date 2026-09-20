import { useEffect, useRef, useState, useSyncExternalStore } from 'react';

import { describeError } from '@/lib/api/errors';
import { runBrief } from '@/lib/api/researchBriefs';
import type { ResearchBrief } from '@/lib/api/researchBriefSchema';
import { useScopedRequest } from '@/lib/hooks/useScopedRequest';
import { subscribeWorkspaceAccess, workspaceRevision } from '@/lib/workspaceAccess';
import { useAuthStore } from '@/stores/auth';

interface RunState {
  key: string;
  busy: boolean;
  error: string | null;
  jobId: string | null;
}

/** An unresolved admission keeps its identity until success or a change of authority/brief. */
export function useBriefRun(brief: ResearchBrief | null) {
  const actor = useAuthStore(
    (state) => `${state.status}:${state.user?.id}:${state.user?.role}:${state.user?.is_active}`,
  );
  const access = useSyncExternalStore(subscribeWorkspaceAccess, workspaceRevision);
  const key = `${actor}:${access}:${brief?.identity.id}:${brief?.identity.revision}`;
  const begin = useScopedRequest();
  const pending = useRef<AbortController | null>(null);
  const attempt = useRef<{ key: string; requestId: string } | null>(null);
  const [state, setState] = useState<RunState>({ key, busy: false, error: null, jobId: null });
  useEffect(
    () => () => {
      pending.current?.abort();
      pending.current = null;
      attempt.current = null;
    },
    [key],
  );
  const run = async () => {
    if (!brief || pending.current) return null;
    if (attempt.current?.key !== key) attempt.current = { key, requestId: crypto.randomUUID() };
    const controller = new AbortController();
    pending.current = controller;
    const signal = AbortSignal.any([controller.signal, begin()]);
    setState({ key, busy: true, error: null, jobId: null });
    try {
      const job = await runBrief(brief, signal, attempt.current.requestId);
      if (signal.aborted) return null;
      attempt.current = null;
      setState({ key, busy: false, error: null, jobId: job.id });
      return job;
    } catch (caught) {
      if (!signal.aborted)
        setState({ key, busy: false, error: describeError(caught), jobId: null });
      return null;
    } finally {
      if (pending.current === controller) pending.current = null;
    }
  };
  return {
    ...(state.key === key ? state : { busy: false, error: null, jobId: null }),
    run,
  };
}
