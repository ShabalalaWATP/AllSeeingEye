import { useEffect, useRef } from 'react';
import type { RefObject } from 'react';

import type { ViewMode } from '@/stores/globe';

import type { MapEngine, MapEngineFactory, Projection } from './engine/MapEngine';
import { createMapLibreEngine } from './engine/MapLibreEngine';

export function projectionFor(mode: ViewMode): Projection {
  return mode === 'globe' ? 'globe' : 'mercator';
}

/**
 * Mounts a map engine into the container for the life of the component and
 * keeps its projection in step with the view mode.
 */
export function useGlobeEngine(
  containerRef: RefObject<HTMLDivElement | null>,
  mode: ViewMode,
  enabled: boolean,
  createEngine: MapEngineFactory = createMapLibreEngine,
): void {
  const engineRef = useRef<MapEngine | null>(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!enabled || container === null) return;
    const engine = createEngine();
    engine.mount(container);
    engineRef.current = engine;
    return () => {
      engine.destroy();
      engineRef.current = null;
    };
  }, [containerRef, createEngine, enabled]);

  useEffect(() => {
    engineRef.current?.setProjection(projectionFor(mode));
  }, [mode, enabled]);
}
