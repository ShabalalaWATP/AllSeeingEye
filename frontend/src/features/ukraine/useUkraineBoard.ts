import { useCallback, useEffect } from 'react';

import { fetchUkraineBoard, type UkraineBoard } from '@/lib/api/ukraine';
import { useResource } from '@/lib/hooks/useResource';

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
  useEffect(() => {
    const tick = () => {
      if (document.visibilityState === 'visible') void reload();
    };
    const timer = window.setInterval(tick, REFRESH_MS);
    return () => window.clearInterval(timer);
  }, [reload]);
  return resource;
}
