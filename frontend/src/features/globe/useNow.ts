import { useSyncExternalStore } from 'react';

export const NOW_TICK_MS = 30_000;

function subscribe(onChange: () => void): () => void {
  const id = setInterval(onChange, NOW_TICK_MS);
  return () => {
    clearInterval(id);
  };
}

/** The current time bucketed to the tick, so snapshots stay stable between ticks. */
function getSnapshot(): number {
  return Math.floor(Date.now() / NOW_TICK_MS) * NOW_TICK_MS;
}

/** A clock that re-renders the subscriber every tick, for relative timestamps. */
export function useNow(): number {
  return useSyncExternalStore(subscribe, getSnapshot, getSnapshot);
}
