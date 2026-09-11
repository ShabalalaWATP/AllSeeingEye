import { useCallback, useEffect, useRef, useState } from 'react';
import { controlReportJob, discardReportJob, fetchReportJob } from '@/lib/api/reportJobs';
import { useNavigate } from 'react-router';
import { asApiError, type ApiError } from '@/lib/api/errors';
import { useScopedRequest } from '@/lib/hooks/useScopedRequest';
import { jobAuthority, useJobPolling } from './useJobPolling';
import { jobRunning } from './jobLabels';

export function useReportJob(id: string) {
  const navigate = useNavigate();
  const loader = useCallback((signal: AbortSignal) => fetchReportJob(id, signal), [id]);
  const [operation, setOperation] = useState<{
    key: string;
    action: 'pause' | 'resume' | 'discard' | null;
    error: ApiError | null;
  } | null>(null);
  const key = `${jobAuthority()}:${id}`;
  const busy = operation?.key === key && operation.action !== null;
  const resource = useJobPolling(loader, jobRunning, busy);
  const begin = useScopedRequest();
  const inFlight = useRef<AbortController | null>(null);
  useEffect(
    () => () => {
      inFlight.current?.abort();
      inFlight.current = null;
    },
    [id],
  );
  const control = async (action: 'pause' | 'resume' | 'discard') => {
    if (inFlight.current && !inFlight.current.signal.aborted) return;
    if (
      !resource.data ||
      (action === 'discard'
        ? !['paused', 'failed'].includes(resource.data.status)
        : action === 'resume'
          ? !resource.data.can_resume
          : !jobRunning(resource.data))
    )
      return;
    const controller = new AbortController();
    const signal = AbortSignal.any([begin(), controller.signal]);
    inFlight.current = controller;
    setOperation({ key, action, error: null });
    try {
      if (action === 'discard') {
        await discardReportJob(id, signal);
        if (!signal.aborted && key === `${jobAuthority()}:${id}`) await navigate('/research/jobs');
        return;
      }
      const next = await controlReportJob(id, action, signal);
      if (!signal.aborted && key === `${jobAuthority()}:${id}`) {
        resource.replace(next);
        setOperation({ key, action: null, error: null });
      }
    } catch (caught) {
      if (!signal.aborted && key === `${jobAuthority()}:${id}`)
        setOperation({ key, action: null, error: asApiError(caught) });
    } finally {
      if (inFlight.current === controller) inFlight.current = null;
    }
  };
  return {
    ...resource,
    busy,
    operationError: operation?.key === key ? operation.error : null,
    action: operation?.key === key ? operation.action : null,
    control,
  };
}
