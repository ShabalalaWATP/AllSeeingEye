import { useCallback } from 'react';

import { fetchUkraineBoard, type UkraineBoard } from '@/lib/api/ukraine';
import { useResource } from '@/lib/hooks/useResource';
import { useVisiblePolling, type PollOutcome } from '@/lib/hooks/useVisiblePolling';

export const REFRESH_MS = 5 * 60 * 1000;

export interface LoadedBoard {
  board: UkraineBoard;
  /** Wall-clock time of the load, for relative freshness labels. */
  loadedAt: number;
}

/** Loads the board and refreshes it while the page is visible; nothing runs when hidden. */
export function useUkraineBoard(load: () => Promise<UkraineBoard> = fetchUkraineBoard) {
  const loader = useCallback(
    async (): Promise<LoadedBoard> => ({ board: await load(), loadedAt: Date.now() }),
    [load],
  );
  const resource = useResource<LoadedBoard>(loader);
  const { reload } = resource;
  const poll = useCallback(async (): Promise<PollOutcome> => {
    await reload();
    return 'ok';
  }, [reload]);
  // A tab that returns after the interval refreshes at once instead of waiting a full cycle.
  useVisiblePolling({ enabled: true, intervalMs: REFRESH_MS, poll });
  return resource;
}
