import { useMemo, useRef, useState } from 'react';
import type { BaseLayer, ViewMode } from '@/stores/globe';
import { createEngine } from './globeEngineFactory';
import { useGlobeEngine } from './useGlobeEngine';
import { hasWebGl2 } from './webgl';
import { selectDailyImagery, useDailyImageryStore } from './imagery/dailyImageryStore';
import { sourceUnavailable, useMapSourcePolicy } from '@/lib/map/sourcePolicy';

/** Create one guarded engine while leaving the controls usable without WebGL. */
export function useDashboardEngine(options: {
  mode: ViewMode;
  baseLayer: BaseLayer;
  lite: boolean;
}) {
  const policy = useMapSourcePolicy();
  const [supported] = useState(() => hasWebGl2());
  const containerRef = useRef<HTMLDivElement>(null);
  const imageryOn = useDailyImageryStore((state) => state.enabled);
  const product = useDailyImageryStore((state) => state.product);
  const date = useDailyImageryStore((state) => state.date);
  const onImageryError = useDailyImageryStore((state) => state.markFailed);
  // Primitive dependencies keep one imagery object per choice, so tiles are not reloaded.
  const dailyImagery = useMemo(
    () => selectDailyImagery({ enabled: imageryOn, product, date }),
    [imageryOn, product, date],
  );
  const engine = useGlobeEngine(containerRef, {
    ...options,
    enabled: supported && sourceUnavailable(policy, 'map:openfreemap') === null,
    createEngine,
    dailyImagery,
    onImageryError,
  });
  return { supported, containerRef, engine };
}
