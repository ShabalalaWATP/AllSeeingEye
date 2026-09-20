import { useCallback, useEffect, useRef, useState } from 'react';
import { fetchTerrainElevations } from '@/lib/api/terrain';
import { analyseTerrainStudy, planTerrainStudy } from '@/lib/map/terrainAnalysis';
import type { TerrainStudy, TerrainStudyInput } from '@/lib/map/terrainAnalysis';
import { useAuthStore } from '@/stores/auth';
import { subscribeWorkspaceAccess } from '@/lib/workspaceAccess';

export interface TerrainStudyDraft {
  mode: 'profile' | 'visibility';
  originLat: string;
  originLon: string;
  endLat: string;
  endLon: string;
  radiusKm: string;
  observerHeightM: string;
}
const EMPTY_DRAFT: TerrainStudyDraft = {
  mode: 'profile',
  originLat: '',
  originLon: '',
  endLat: '',
  endLon: '',
  radiusKm: '5',
  observerHeightM: '2',
};

/** Explicit, cancellable analyses belong to the workspace, not the visible drawer. */
export function useTerrainAnalysis() {
  const [result, setResult] = useState<TerrainStudy | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [highlighted, setHighlighted] = useState(-1);
  const [draft, setDraft] = useState<TerrainStudyDraft>(EMPTY_DRAFT);
  const request = useRef<AbortController | null>(null);
  const clear = useCallback(() => {
    request.current?.abort();
    request.current = null;
    setResult(null);
    setError(null);
    setBusy(false);
    setHighlighted(-1);
  }, []);
  useEffect(() => {
    const reset = () => {
      clear();
      setDraft(EMPTY_DRAFT);
    };
    const offAccess = subscribeWorkspaceAccess(reset);
    const offAuth = useAuthStore.subscribe((state, previous) => {
      if (state.status !== previous.status || state.user !== previous.user) reset();
    });
    return () => {
      offAccess();
      offAuth();
      request.current?.abort();
      request.current = null;
    };
  }, [clear]);
  const run = useCallback(
    async (input: TerrainStudyInput) => {
      clear();
      const controller = new AbortController();
      request.current = controller;
      setBusy(true);
      try {
        const plan = planTerrainStudy(input);
        const source = await fetchTerrainElevations(plan.positions, controller.signal);
        if (request.current !== controller || controller.signal.aborted) return;
        setResult(analyseTerrainStudy(input, plan, source));
      } catch (failure) {
        if (request.current === controller && !controller.signal.aborted)
          setError(failure instanceof Error ? failure.message : 'Terrain analysis failed.');
      } finally {
        if (request.current === controller) {
          request.current = null;
          setBusy(false);
        }
      }
    },
    [clear],
  );
  return { result, error, busy, run, clear, highlighted, setHighlighted, draft, setDraft };
}
