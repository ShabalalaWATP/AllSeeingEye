import { useCallback, useEffect, useMemo, useRef } from 'react';
import type { RefObject } from 'react';

import type { ViewMode } from '@/stores/globe';

import type {
  DataLayer,
  FlyToTarget,
  MapEngine,
  MapEngineFactory,
  Projection,
} from './engine/MapEngine';
import { createMapLibreEngine } from './engine/MapLibreEngine';
import type { BaseLayer } from './engine/baseLayers';

export function projectionFor(mode: ViewMode): Projection {
  return mode === 'globe' ? 'globe' : 'mercator';
}

export interface GlobeEngineHandle {
  setLayers: (layers: readonly DataLayer[]) => void;
  flyTo: (target: FlyToTarget) => void;
}

/**
 * Mounts a map engine into the container for the life of the component, keeps
 * its projection in step with the view mode, and hands back stable callbacks
 * for the data layers and camera.
 */
export function useGlobeEngine(
  containerRef: RefObject<HTMLDivElement | null>,
  mode: ViewMode,
  enabled: boolean,
  baseLayer: BaseLayer = 'dark',
  createEngine: MapEngineFactory = createMapLibreEngine,
): GlobeEngineHandle {
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

  useEffect(() => {
    engineRef.current?.setBaseLayer(baseLayer);
  }, [baseLayer, enabled]);

  const setLayers = useCallback((layers: readonly DataLayer[]) => {
    engineRef.current?.setLayers(layers);
  }, []);

  const flyTo = useCallback((target: FlyToTarget) => {
    engineRef.current?.flyTo(target);
  }, []);

  return useMemo(() => ({ setLayers, flyTo }), [setLayers, flyTo]);
}
