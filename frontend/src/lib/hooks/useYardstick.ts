/**
 * The configured probability yardstick, read once per session from the report methodology
 * endpoint so likelihood terms show the server's own bands, never a copy kept here.
 */
import { useEffect, useState } from 'react';

import { fetchReportMethodology } from '@/lib/api/reportMethodology';
import type { ReportMethodology } from '@/lib/api/reportMethodology';
import { useAuthStore } from '@/stores/auth';

export type YardstickBand = ReportMethodology['probability_yardstick'][number];
/** Loaded bands, `null` while loading or signed out, or `'unavailable'` after a failure. */
export type Yardstick = readonly YardstickBand[] | null | 'unavailable';

let pending: Promise<readonly YardstickBand[]> | null = null;

function load(): Promise<readonly YardstickBand[]> {
  pending ??= fetchReportMethodology().then(
    (methodology) => methodology.probability_yardstick,
    (error: unknown) => {
      pending = null; // A later reader may retry.
      throw error;
    },
  );
  return pending;
}

/** For tests: forget the cached bands. */
export function resetYardstick() {
  pending = null;
}

export function useYardstick(): Yardstick {
  const signedIn = useAuthStore((state) => state.status === 'authenticated');
  const [bands, setBands] = useState<Yardstick>(null);
  useEffect(() => {
    if (!signedIn) return;
    let live = true;
    load().then(
      (loaded) => {
        if (live) setBands(loaded);
      },
      () => {
        if (live) setBands('unavailable');
      },
    );
    return () => {
      live = false;
    };
  }, [signedIn]);
  return bands;
}

/** The band for a stored likelihood value, or why none is shown. */
export function bandText(yardstick: Yardstick, probability: string): string | null {
  if (yardstick === null) return null;
  if (yardstick === 'unavailable') return 'Band unavailable';
  return (
    yardstick.find((band) => band.probability === probability)?.range_description ??
    'No configured band for this term'
  );
}

/** The loaded bands, or none while loading, signed out or unavailable. */
export function loadedBands(yardstick: Yardstick): readonly YardstickBand[] {
  return yardstick === null || yardstick === 'unavailable' ? [] : yardstick;
}
