import { useCallback, useEffect, useMemo, useRef } from 'react';
import type { RefObject } from 'react';

import type { BaseLayer, ViewMode } from '@/stores/globe';

import type {
  CursorHandler,
  DataLayer,
  FlyToTarget,
  MapEngine,
  MapEngineFactory,
  Projection,
} from './engine/MapEngine';
import { createMapLibreEngine } from './engine/MapLibreEngine';

export function projectionFor(mode: ViewMode): Projection {
  return mode === 'globe' ? 'globe' : 'mercator';
}

export interface GlobeEngineHandle {
  setLayers: (layers: readonly DataLayer[]) => void;
  flyTo: (target: FlyToTarget) => void;
  getZoom: () => number;
  spin: (enabled: boolean) => void;
  /** Subscribes to cursor positions; safe to call before the engine has mounted. */
  onCursor: (handler: CursorHandler) => () => void;
  /** Subscribes to camera moves with the zoom after each; safe before the engine mounts. */
  onView: (handler: ViewHandler) => () => void;
}

export type ViewHandler = (view: { zoom: number }) => void;

export interface GlobeEngineOptions {
  enabled: boolean;
  mode: ViewMode;
  baseLayer?: BaseLayer;
  lite?: boolean;
  createEngine?: MapEngineFactory;
}

/**
 * Mounts a map engine into the container for the life of the component, keeps its
 * projection, base layer and lite setting in step with the view state, and hands
 * back stable callbacks for the data layers, the camera and the cursor. Engine replacement
 * replays the current scene; synchronisation effects also depend on the mount inputs.
 */
export function useGlobeEngine(
  containerRef: RefObject<HTMLDivElement | null>,
  { enabled, mode, baseLayer = 'dark', lite = false, createEngine }: GlobeEngineOptions,
): GlobeEngineHandle {
  const engineRef = useRef<MapEngine | null>(null);
  const cursorHandlers = useRef(new Set<CursorHandler>());
  const viewHandlers = useRef(new Set<ViewHandler>());
  const latestLayers = useRef<readonly DataLayer[]>([]);
  const spinning = useRef(false);
  const factory = createEngine ?? createMapLibreEngine;

  useEffect(() => {
    const container = containerRef.current;
    if (!enabled || container === null) return;
    const engine = factory();
    engine.mount(container);
    engine.setLayers(latestLayers.current);
    engine.spin(spinning.current);
    const offCursor = engine.onCursor((position) => {
      for (const handler of cursorHandlers.current) handler(position);
    });
    const offMove = engine.on('move', () => {
      const view = { zoom: engine.getZoom() };
      for (const handler of viewHandlers.current) handler(view);
    });
    engineRef.current = engine;
    return () => {
      offMove();
      offCursor();
      engine.destroy();
      engineRef.current = null;
    };
  }, [containerRef, factory, enabled]);

  useEffect(() => {
    engineRef.current?.setProjection(projectionFor(mode));
  }, [mode, enabled, factory, containerRef]);

  useEffect(() => {
    engineRef.current?.setBaseLayer(baseLayer);
  }, [baseLayer, enabled, factory, containerRef]);

  useEffect(() => {
    engineRef.current?.setLite(lite);
  }, [lite, enabled, factory, containerRef]);

  const setLayers = useCallback((layers: readonly DataLayer[]) => {
    latestLayers.current = layers;
    engineRef.current?.setLayers(layers);
  }, []);

  const flyTo = useCallback((target: FlyToTarget) => {
    engineRef.current?.flyTo(target);
  }, []);

  const getZoom = useCallback(() => engineRef.current?.getZoom() ?? 0, []);

  const spin = useCallback((enabled: boolean) => {
    spinning.current = enabled;
    engineRef.current?.spin(enabled);
  }, []);

  const onCursor = useCallback((handler: CursorHandler) => {
    cursorHandlers.current.add(handler);
    return () => {
      cursorHandlers.current.delete(handler);
    };
  }, []);

  const onView = useCallback((handler: ViewHandler) => {
    viewHandlers.current.add(handler);
    return () => {
      viewHandlers.current.delete(handler);
    };
  }, []);

  return useMemo(
    () => ({ setLayers, flyTo, getZoom, spin, onCursor, onView }),
    [setLayers, flyTo, getZoom, spin, onCursor, onView],
  );
}
