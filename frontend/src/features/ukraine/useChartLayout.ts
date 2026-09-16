/**
 * Chart or indented outline. A narrow viewport gets the outline by default because a squeezed
 * top-down chart is unreadable at 360px; the reader can override the choice either way.
 */
import { useSyncExternalStore } from 'react';

import type { ChartLayout } from './ForceChart';

const NARROW_QUERY = '(max-width: 767px)';

function query(): MediaQueryList | null {
  if (typeof window.matchMedia !== 'function') return null;
  return window.matchMedia(NARROW_QUERY);
}

function subscribe(onChange: () => void): () => void {
  const media = query();
  if (media === null) return () => undefined;
  media.addEventListener('change', onChange);
  return () => {
    media.removeEventListener('change', onChange);
  };
}

export function useNarrowViewport(): boolean {
  return useSyncExternalStore(
    subscribe,
    () => query()?.matches ?? false,
    () => false,
  );
}

export function useChartLayout(override: ChartLayout | null): ChartLayout {
  const narrow = useNarrowViewport();
  if (override !== null) return override;
  return narrow ? 'stacked' : 'chart';
}
