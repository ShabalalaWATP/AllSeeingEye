import { useEffect, useEffectEvent, useMemo } from 'react';
import { PathLayer } from '@deck.gl/layers';
import type { ViewMode } from '@/stores/globe';
import type { NavigationRoute } from '@/lib/api/navigation';
import { measurementLayers } from '@/lib/map/measurementLayers';
import { drawingLayers } from '@/lib/map/drawingLayers';
import { researchAreaLayers } from '@/lib/map/researchAreaLayers';
import { researchAreaGeometry } from '@/lib/map/researchAreaGeometry';
import { rfMapLayers } from '@/lib/map/rfMap';
import { rfTerrainLayers } from '@/lib/map/rfTerrainLayers';
import { hfGroundwaveLayers } from '@/lib/map/hfGroundwaveMap';
import { hfSkywaveLayers } from '@/lib/map/hfSkywaveLayers';
import { useRoutePlannerState } from '@/components/maps/useRoutePlannerState';
import { useRfMapPlacement } from './useRfMapPlacement';
import { useMapDrawing } from './useMapDrawing';
import { useMapMeasurement } from './useMapMeasurement';
import type { GlobeEngineHandle } from './useGlobeEngine';

/** One click owner prevents drawings, measurements and item selections competing. */
export function useMapWorkspaceTools(engine: GlobeEngineHandle, enabled: boolean, mode: ViewMode) {
  const measurement = useMapMeasurement(engine, enabled);
  const drawing = useMapDrawing(engine, enabled);
  const researchDrawing = useMapDrawing(engine, enabled);
  const rf = useRfMapPlacement(engine, enabled);
  const routePlanner = useRoutePlannerState();
  const { route, setRoute } = routePlanner;
  const stopPicking = useEffectEvent(() => {
    measurement.setPicking(false);
    drawing.setPicking(false);
    researchDrawing.setPicking(false);
    rf.setPicking(null);
  });
  useEffect(() => {
    if (!enabled) stopPicking();
  }, [enabled]);
  const sketchMode =
    (drawing.picking && drawing.interaction !== 'click') ||
    (researchDrawing.picking && researchDrawing.interaction !== 'click')
      ? 'drag'
      : drawing.picking || researchDrawing.picking || measurement.picking || rf.picking
        ? 'points'
        : 'navigate';
  useEffect(() => {
    engine.setSketchMode?.(sketchMode);
    return () => engine.setSketchMode?.('navigate');
  }, [engine, sketchMode]);

  // Drag previews must not resample unchanged measurements/RF or upload long routes again.
  const measured = useMemo(
    () => measurementLayers(measurement.points, measurement.mode, mode === 'map'),
    [measurement.points, measurement.mode, mode],
  );
  const drawn = useMemo(
    () => drawingLayers(drawing.points, drawing.mode, mode === 'map', drawing.displayedAnchors),
    [drawing.points, drawing.mode, drawing.displayedAnchors, mode],
  );
  const researchLayers = useMemo(
    () =>
      researchAreaLayers(researchDrawing.shape, researchDrawing.displayedAnchors, mode === 'map'),
    [researchDrawing.shape, researchDrawing.displayedAnchors, mode],
  );
  const researchBoundary = useMemo(() => {
    if (researchDrawing.picking || researchDrawing.anchors.length === 0)
      return { area: null, areaError: null };
    try {
      return {
        area: researchAreaGeometry(researchDrawing.shape, researchDrawing.anchors),
        areaError: null,
      };
    } catch (error) {
      return {
        area: null,
        areaError: error instanceof Error ? error.message : 'Draw a valid area.',
      };
    }
  }, [researchDrawing.shape, researchDrawing.anchors, researchDrawing.picking]);
  const radio = useMemo(
    () => rfMapLayers(rf.estimate, mode === 'map', rf.coverageBubble && !rf.estimate?.receiver),
    [rf.estimate, mode, rf.coverageBubble],
  );
  const propagation = useMemo(() => {
    const analysis = rf.analysis;
    if (analysis?.kind === 'terrain')
      return rfTerrainLayers(analysis.terrain, mode === 'map', rf.coverageBubble);
    if (analysis?.kind === 'hf-groundwave') return hfGroundwaveLayers(analysis, mode === 'map');
    if (analysis?.kind === 'hf-skywave') return hfSkywaveLayers(analysis.estimate, mode === 'map');
    return [];
  }, [rf.analysis, mode, rf.coverageBubble]);
  const routed = useMemo(
    () =>
      route
        ? [
            new PathLayer<{ path: NavigationRoute['coordinates'] }>({
              id: 'navigation-route',
              data: [{ path: route.coordinates }],
              getPath: (item) => item.path,
              getColor: [122, 222, 240, 230],
              getWidth: 4,
              widthUnits: 'pixels',
              pickable: false,
              wrapLongitude: mode === 'map',
            }),
          ]
        : [],
    [route, mode],
  );
  const layers = useMemo(
    () => [...measured, ...drawn, ...researchLayers, ...radio, ...propagation, ...routed],
    [measured, drawn, researchLayers, radio, propagation, routed],
  );
  return {
    measurement: {
      ...measurement,
      setPicking: (active: boolean) => {
        if (active) {
          drawing.setPicking(false);
          researchDrawing.setPicking(false);
          rf.setPicking(null);
        }
        measurement.setPicking(active);
      },
    },
    drawing: {
      ...drawing,
      setPicking: (active: boolean) => {
        if (active) {
          measurement.setPicking(false);
          researchDrawing.setPicking(false);
          rf.setPicking(null);
        }
        drawing.setPicking(active);
      },
    },
    research: {
      ...researchBoundary,
      drawing: {
        ...researchDrawing,
        setPicking: (active: boolean) => {
          if (active) {
            measurement.setPicking(false);
            drawing.setPicking(false);
            rf.setPicking(null);
          }
          researchDrawing.setPicking(active);
        },
      },
    },
    rf: {
      ...rf,
      setPicking: (point: 'origin' | 'receiver' | null) => {
        if (point) {
          measurement.setPicking(false);
          drawing.setPicking(false);
          researchDrawing.setPicking(false);
        }
        rf.setPicking(point);
      },
    },
    layers,
    routePlanner,
    setRoute,
    picking:
      measurement.picking || drawing.picking || researchDrawing.picking || rf.picking !== null,
    activatePanel: (label: string | null) => {
      if (label !== null && label !== 'Measure distance and area') measurement.setPicking(false);
      if (label !== 'Draw on map') drawing.setPicking(false);
      if (label !== 'Research area') researchDrawing.setPicking(false);
      if (label !== 'RF link calculator') rf.setPicking(null);
    },
  };
}
