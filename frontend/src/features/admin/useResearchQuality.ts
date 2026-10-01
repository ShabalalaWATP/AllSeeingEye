import { useCallback, useState } from 'react';

import { fetchResearchQuality, type QualityWindow } from '@/lib/api/researchQuality';
import { useScopedResource } from '@/lib/hooks/useScopedResource';

import type { QualityDimension } from './quality/qualityPresentation';

/** Loads the scorecard for the chosen window; nothing is cached beyond the current view. */
export function useResearchQuality() {
  const [windowDays, setWindowDays] = useState<QualityWindow>(90);
  const [dimension, setDimension] = useState<QualityDimension>('template');
  const loader = useCallback(() => fetchResearchQuality(windowDays), [windowDays]);
  const { data, error, loading, reload } = useScopedResource(loader);
  return { data, error, loading, reload, windowDays, setWindowDays, dimension, setDimension };
}
