import { useCallback, useEffect, useRef, useState } from 'react';

import { asApiError } from '@/lib/api/errors';
import type { ApiError } from '@/lib/api/errors';
import {
  cancelEvaluationRun,
  downloadEvaluationArtefact,
  fetchEvaluationCatalogue,
  fetchEvaluationRuns,
  startEvaluationRun,
} from '@/lib/api/evaluations';
import type { EvaluationCatalogue, EvaluationRun, EvaluationStart } from '@/lib/api/evaluations';
import { fetchLlmProfiles } from '@/lib/api/llm';
import type { LlmProfile } from '@/lib/api/llm';
import { saveBinaryFile } from '@/lib/downloadBinary';

import { assessmentProfiles } from './evaluationPresentation';

export const POLL_INTERVAL_MS = 3000;

export interface Evaluations {
  catalogue: EvaluationCatalogue | null;
  profiles: LlmProfile[];
  runs: EvaluationRun[];
  loading: boolean;
  busy: boolean;
  error: ApiError | null;
  start: (body: EvaluationStart) => Promise<boolean>;
  cancel: (runId: string) => Promise<void>;
  download: (run: EvaluationRun) => Promise<void>;
}

/** Loads the casebook, assessment connections and recent runs; polls while one runs. */
export function useEvaluations(): Evaluations {
  const [catalogue, setCatalogue] = useState<EvaluationCatalogue | null>(null);
  const [profiles, setProfiles] = useState<LlmProfile[]>([]);
  const [runs, setRuns] = useState<EvaluationRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);
  const mounted = useRef(true);

  const refreshRuns = useCallback(async () => {
    try {
      const items = await fetchEvaluationRuns();
      if (mounted.current) setRuns(items);
    } catch (caught) {
      if (mounted.current) setError(asApiError(caught));
    }
  }, []);

  useEffect(() => {
    mounted.current = true;
    const controller = new AbortController();
    void (async () => {
      try {
        const [loadedCatalogue, loadedProfiles, loadedRuns] = await Promise.all([
          fetchEvaluationCatalogue(controller.signal),
          fetchLlmProfiles(),
          fetchEvaluationRuns(controller.signal),
        ]);
        if (controller.signal.aborted) return;
        setCatalogue(loadedCatalogue);
        setProfiles(assessmentProfiles(loadedProfiles.items));
        setRuns(loadedRuns);
      } catch (caught) {
        if (!controller.signal.aborted) setError(asApiError(caught));
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    })();
    return () => {
      mounted.current = false;
      controller.abort();
    };
  }, []);

  const running = runs.some((run) => run.status === 'running');
  useEffect(() => {
    if (!running) return undefined;
    const timer = window.setInterval(() => void refreshRuns(), POLL_INTERVAL_MS);
    return () => window.clearInterval(timer);
  }, [running, refreshRuns]);

  const act = useCallback(async (action: () => Promise<void>): Promise<boolean> => {
    setBusy(true);
    try {
      await action();
      setError(null);
      return true;
    } catch (caught) {
      setError(asApiError(caught));
      return false;
    } finally {
      setBusy(false);
    }
  }, []);

  const start = useCallback(
    (body: EvaluationStart) =>
      act(async () => {
        const run = await startEvaluationRun(body);
        setRuns((current) => [run, ...current.filter((item) => item.id !== run.id)]);
      }),
    [act],
  );

  const cancel = useCallback(
    async (runId: string) => {
      await act(async () => {
        const run = await cancelEvaluationRun(runId);
        setRuns((current) => current.map((item) => (item.id === run.id ? run : item)));
      });
    },
    [act],
  );

  const download = useCallback(
    async (run: EvaluationRun) => {
      await act(async () => {
        const file = await downloadEvaluationArtefact(run.id);
        saveBinaryFile(file.filename ?? `evaluation-${run.id}.zip`, file.blob);
      });
    },
    [act],
  );

  return { catalogue, profiles, runs, loading, busy, error, start, cancel, download };
}
