import { useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router';

import { generateReport, type ReportRequest } from '@/lib/api/reports';
import { asApiError, type ApiError } from '@/lib/api/errors';
import { workspaceRevision } from '@/lib/workspaceAccess';
import { useAuthStore } from '@/stores/auth';
import { useResearchProgress } from './useResearchProgress';

/** A completed request must not navigate a different account or a page the user has left. */
export function useResearchRun() {
  const navigate = useNavigate();
  const progress = useResearchProgress();
  const mounted = useRef(true);
  const inFlight = useRef(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);
  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);
  const run = async (request: ReportRequest) => {
    if (inFlight.current) return;
    inFlight.current = true;
    setBusy(true);
    setError(null);
    const actor = useAuthStore.getState().user;
    const revision = workspaceRevision();
    const isCurrent = () => {
      const current = useAuthStore.getState().user;
      return (
        mounted.current &&
        current?.id === actor?.id &&
        current?.role === actor?.role &&
        current?.is_active &&
        workspaceRevision() === revision
      );
    };
    let signal: AbortSignal | undefined;
    try {
      const options = progress.begin();
      signal = options.signal;
      const result = await generateReport(request, options);
      progress.finish(signal.aborted ? 'cancelled' : 'completed');
      if (!signal.aborted && isCurrent()) {
        await navigate(`/reports/${result.report.id}`);
      }
    } catch (caught) {
      progress.finish(signal?.aborted ? 'cancelled' : 'failed');
      if (!signal?.aborted && isCurrent()) setError(asApiError(caught));
    } finally {
      inFlight.current = false;
      if (mounted.current) setBusy(false);
    }
  };
  const clearError = useCallback(() => setError(null), []);
  return { run, busy, error, clearError, progress };
}
