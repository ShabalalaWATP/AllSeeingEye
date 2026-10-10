import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { RefObject } from 'react';

import type { BaseLayer, ViewMode } from '@/stores/globe';

import type {
  CursorHandler,
  DataLayer,
  FlyToTarget,
  MapEngine,
  MapCamera,
  MapBounds,
  MapEngineFactory,
  Projection,
  SketchMode,
  SketchDragHandler,
} from './engine/MapEngine';
import { createMapLibreEngine } from './engine/MapLibreEngine';
import { useMapRecovery } from './useMapRecovery';
import type { MapRenderState } from './useMapRecovery';
import { areaClickPoint } from '@/lib/map/areaGeometry';
import { isDailyImageryError, type DailyImagery } from '@/lib/map/dailyImagery';

export function projectionFor(mode: ViewMode): Projection {
  return mode === 'globe' ? 'globe' : 'mercator';
}

export interface GlobeEngineHandle {
  renderState?: MapRenderState;
  reload?: () => void;
  setLayers: (layers: readonly DataLayer[]) => void;
  flyTo: (target: FlyToTarget) => void;
  getZoom: () => number;
  getCamera?: () => MapCamera | null;
  getViewportBounds?: () => MapBounds | null;
  /** An explicit projection waits for its committed engine synchronisation. */
  restoreCamera?: (camera: MapCamera, projection?: Projection) => void;
  pickObjectsAt?: (x: number, y: number) => readonly unknown[];
  spin: (enabled: boolean) => void;
  /** Subscribes to cursor positions; safe to call before the engine has mounted. */
  onCursor: (handler: CursorHandler) => () => void;
  onClick: (handler: CursorHandler) => () => void;
  onDrag?: (handler: SketchDragHandler) => () => void;
  setSketchMode?: (mode: SketchMode) => void;
  /** Subscribes to camera moves with the zoom after each; safe before the engine mounts. */
  onView: (handler: ViewHandler) => () => void;
}

export type ViewHandler = (view: { zoom: number }) => void;

type Navigation =
  | { kind: 'focus'; target: FlyToTarget }
  | { kind: 'restore'; camera: MapCamera; projection: Projection | undefined };

export interface GlobeEngineOptions {
  enabled: boolean;
  /** Retain the latest navigation while an initial admission check is unresolved. */
  deferred?: boolean;
  mode: ViewMode;
  baseLayer?: BaseLayer;
  lite?: boolean;
  createEngine?: MapEngineFactory;
  /** Dated imagery over the base map; null or omitted draws none. */
  dailyImagery?: DailyImagery | null;
  /** Called when a dated imagery tile fails; the base map is unaffected. */
  onImageryError?: () => void;
}

/**
 * Mounts a map engine into the container for the life of the component, keeps its
 * projection, base layer and lite setting in step with the view state, and hands
 * back stable callbacks for the data layers, the camera and the cursor. Engine replacement
 * replays the current scene; synchronisation effects also depend on the mount inputs.
 */
export function useGlobeEngine(
  containerRef: RefObject<HTMLDivElement | null>,
  {
    enabled,
    deferred = false,
    mode,
    baseLayer = 'dark',
    lite = false,
    createEngine,
    dailyImagery = null,
    onImageryError,
  }: GlobeEngineOptions,
): GlobeEngineHandle {
  const engineRef = useRef<MapEngine | null>(null);
  const appliedProjection = useRef<Projection | null>(null);
  const pendingNavigation = useRef<{ generation: number; intent: Navigation } | null>(null);
  const nextNavigation = useRef(0);
  const [navigationGeneration, setNavigationGeneration] = useState(0);
  const queueNavigation = useCallback((intent: Navigation) => {
    const generation = ++nextNavigation.current;
    pendingNavigation.current = { generation, intent };
    // Only deferred navigation schedules an owner commit, never stream updates.
    setNavigationGeneration(generation);
  }, []);
  const cursorHandlers = useRef(new Set<CursorHandler>());
  const clickHandlers = useRef(new Set<CursorHandler>());
  const dragHandlers = useRef(new Set<SketchDragHandler>());
  const sketchMode = useRef<SketchMode>('navigate');
  const viewHandlers = useRef(new Set<ViewHandler>());
  const latestLayers = useRef<readonly DataLayer[]>([]);
  const spinning = useRef(false);
  const imageryError = useRef(onImageryError);
  useEffect(() => {
    imageryError.current = onImageryError;
  }, [onImageryError]);
  const factory = createEngine ?? createMapLibreEngine;
  const { renderState, revision, reload, onRenderStatus, restoreReloadCamera } =
    useMapRecovery(engineRef);

  useEffect(() => {
    const container = containerRef.current;
    if (!enabled || container === null) {
      if (!deferred) pendingNavigation.current = null;
      return;
    }
    let active = true;
    const engine = factory({
      onRenderStatus: (status, message) => {
        if (active) onRenderStatus(status, message);
      },
    });
    try {
      engine.mount(container);
      restoreReloadCamera(engine);
    } catch {
      engine.destroy();
      pendingNavigation.current = null;
      appliedProjection.current = null;
      onRenderStatus('failed', 'Map graphics could not start. Reload the map to retry.');
      return () => {
        active = false;
      };
    }
    engine.setLayers(latestLayers.current);
    engine.spin(spinning.current);
    engine.setSketchMode?.(sketchMode.current);
    const offDrag = engine.onDrag?.((event) => {
      for (const handler of dragHandlers.current) handler(event);
    });
    const offCursor = engine.onCursor((position) => {
      for (const handler of cursorHandlers.current) handler(position);
    });
    const offMove = engine.on('move', () => {
      const view = { zoom: engine.getZoom() };
      for (const handler of viewHandlers.current) handler(view);
    });
    const offImageryError = engine.on('error', (payload) => {
      if (isDailyImageryError(payload)) imageryError.current?.();
    });
    const offClick = engine.on('click', (event) => {
      const point = areaClickPoint(event);
      if (point)
        for (const handler of clickHandlers.current) handler({ lon: point[0], lat: point[1] });
    });
    engineRef.current = engine;
    return () => {
      active = false;
      offMove();
      offClick();
      offImageryError();
      offCursor();
      engine.destroy();
      offDrag?.();
      engineRef.current = null;
      appliedProjection.current = null;
      pendingNavigation.current = null;
    };
  }, [containerRef, factory, enabled, deferred, revision, onRenderStatus, restoreReloadCamera]);

  useEffect(() => {
    const engine = engineRef.current;
    const projection = projectionFor(mode);
    if (engine) {
      appliedProjection.current = null;
      engine.setProjection(projection);
      appliedProjection.current = projection;
    }
    const pending = pendingNavigation.current;
    // A child can request navigation before this parent's older mount effect runs.
    // Admission can defer the initial mount; retain only the latest intent until resolved.
    if (pending?.generation !== navigationGeneration) return;
    if (!engine && deferred) return;
    pendingNavigation.current = null;
    if (!engine) return;
    const { intent } = pending;
    if (intent.kind === 'focus') engine.flyTo(intent.target);
    else if (intent.projection === undefined || intent.projection === projection)
      engine.restoreCamera(intent.camera);
  }, [mode, enabled, deferred, factory, containerRef, revision, navigationGeneration]);

  useEffect(() => {
    engineRef.current?.setBaseLayer(baseLayer);
  }, [baseLayer, enabled, factory, containerRef, revision]);

  useEffect(() => {
    engineRef.current?.setDailyImagery?.(dailyImagery);
  }, [dailyImagery, enabled, factory, containerRef, revision]);

  useEffect(() => {
    engineRef.current?.setLite(lite);
  }, [lite, enabled, factory, containerRef, revision]);

  const setLayers = useCallback((layers: readonly DataLayer[]) => {
    latestLayers.current = layers;
    engineRef.current?.setLayers(layers);
  }, []);

  const flyTo = useCallback(
    (target: FlyToTarget) => {
      if (containerRef.current === null) return;
      pendingNavigation.current = null;
      if (engineRef.current && appliedProjection.current !== null) engineRef.current.flyTo(target);
      else queueNavigation({ kind: 'focus', target });
    },
    [containerRef, queueNavigation],
  );

  const pickObjectsAt = useCallback(
    (x: number, y: number) => engineRef.current?.pickObjectsAt?.(x, y) ?? [],
    [],
  );
  const getCamera = useCallback(() => engineRef.current?.getCamera() ?? null, []);
  const restoreCamera = useCallback(
    (camera: MapCamera, projection?: Projection) => {
      if (containerRef.current === null) return;
      pendingNavigation.current = null;
      const engine = engineRef.current;
      if (
        engine &&
        appliedProjection.current !== null &&
        (projection === undefined || projection === appliedProjection.current)
      )
        engine.restoreCamera(camera);
      else queueNavigation({ kind: 'restore', camera, projection });
    },
    [containerRef, queueNavigation],
  );
  const getViewportBounds = useCallback(() => engineRef.current?.getViewportBounds() ?? null, []);
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
  const onClick = useCallback((handler: CursorHandler) => {
    clickHandlers.current.add(handler);
    return () => {
      clickHandlers.current.delete(handler);
    };
  }, []);
  const onDrag = useCallback((handler: SketchDragHandler) => {
    dragHandlers.current.add(handler);
    return () => {
      dragHandlers.current.delete(handler);
    };
  }, []);
  const setSketchMode = useCallback((mode: SketchMode) => {
    sketchMode.current = mode;
    engineRef.current?.setSketchMode?.(mode);
  }, []);

  return useMemo(
    () => ({
      renderState,
      reload,
      setLayers,
      flyTo,
      getZoom,
      spin,
      onCursor,
      onView,
      onClick,
      onDrag,
      setSketchMode,
      pickObjectsAt,
      getCamera,
      getViewportBounds,
      restoreCamera,
    }),
    [
      renderState,
      reload,
      setLayers,
      flyTo,
      getZoom,
      spin,
      onCursor,
      onView,
      onClick,
      onDrag,
      setSketchMode,
      pickObjectsAt,
      getCamera,
      getViewportBounds,
      restoreCamera,
    ],
  );
}
