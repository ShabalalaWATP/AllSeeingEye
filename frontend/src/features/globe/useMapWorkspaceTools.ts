import { useEffect, useEffectEvent, useMemo } from 'react';
import { PathLayer, ScatterplotLayer } from '@deck.gl/layers';
import type { ViewMode } from '@/stores/globe';
import type { NavigationRoute } from '@/lib/api/navigation';
import { measurementLayers } from '@/lib/map/measurementLayers';
import { drawingLayers } from '@/lib/map/drawingLayers';
import type { LocalCollection } from '@/lib/map/geoJsonTypes';
import { terrainAnalysisLayers } from '@/lib/map/terrainAnalysisLayers';
import { useTerrainAnalysis } from '@/components/maps/useTerrainAnalysis';
import { rfMapLayers } from '@/lib/map/rfMap';
import { radioSiteLayers } from '@/lib/map/radioSiteLayers';
import { rfTerrainLayers } from '@/lib/map/rfTerrainLayers';
import { hfGroundwaveLayers } from '@/lib/map/hfGroundwaveMap';
import { hfSkywaveLayers } from '@/lib/map/hfSkywaveLayers';
import { useRoutePlannerState } from '@/components/maps/useRoutePlannerState';
import { useRfMapPlacement } from './useRfMapPlacement';
import { useMapDrawing } from './useMapDrawing';
import { useMapMeasurement } from './useMapMeasurement';
import { useDrawingWorkspace } from './useDrawingWorkspace';
import { useResearchBoundary } from './useResearchBoundary';
import { useWorkspaceVisibility } from './useWorkspaceVisibility';
import type { GlobeEngineHandle } from './useGlobeEngine';

/** One click owner prevents drawings, measurements and item selections competing. */
export function useMapWorkspaceTools(engine: GlobeEngineHandle, enabled: boolean, mode: ViewMode) {
  const measurement = useMapMeasurement(engine, enabled);
  const drawing = useMapDrawing(engine, enabled);
  const researchDrawing = useMapDrawing(engine, enabled);
  const drawingWorkspace = useDrawingWorkspace(drawing, mode === 'map');
  const researchBoundary = useResearchBoundary(researchDrawing, mode === 'map');
  const terrainStudy = useTerrainAnalysis();
  const visibility = useWorkspaceVisibility();
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
    (researchDrawing.picking && researchDrawing.interaction !== 'click') ||
    (rf.picking && rf.interaction === 'drag')
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
  const terrainLayers = useMemo(
    () => terrainAnalysisLayers(terrainStudy.result, mode === 'map', terrainStudy.highlighted),
    [terrainStudy.result, terrainStudy.highlighted, mode],
  );
  const radioHighlight = useMemo(
    () =>
      rf.profilePoint
        ? [
            new ScatterplotLayer({
              id: 'radio-profile-inspection',
              data: [rf.profilePoint],
              getPosition: (point: [number, number]) => point,
              getFillColor: [255, 255, 255, 240],
              getRadius: 6,
              radiusUnits: 'pixels',
              pickable: false,
              wrapLongitude: mode === 'map',
            }),
          ]
        : [],
    [rf.profilePoint, mode],
  );
  const radio = useMemo(
    () => rfMapLayers(rf.estimate, mode === 'map', rf.coverageBubble && !rf.estimate?.receiver),
    [rf.estimate, mode, rf.coverageBubble],
  );
  const radioSites = useMemo(
    () => radioSiteLayers(rf.origin, rf.receiver, rf.siteNames, mode === 'map'),
    [rf.origin, rf.receiver, rf.siteNames, mode],
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
    () => [
      ...(visibility.visible.measurement || measurement.picking ? measured : []),
      ...(visibility.visible.sketch || drawing.picking ? drawn : []),
      ...drawingWorkspace.layers,
      ...(visibility.visible.research || researchDrawing.picking ? researchBoundary.layers : []),
      ...(visibility.visible.radio || rf.picking
        ? [...radio, ...propagation, ...radioSites, ...radioHighlight]
        : []),
      ...(visibility.visible.route ? routed : []),
      ...(visibility.visible.terrain ? terrainLayers : []),
    ],
    [
      measured,
      drawn,
      researchBoundary.layers,
      radio,
      propagation,
      routed,
      visibility.visible,
      measurement.picking,
      drawing.picking,
      researchDrawing.picking,
      drawingWorkspace.layers,
      terrainLayers,
      radioHighlight,
      radioSites,
      rf.picking,
    ],
  );
  return {
    drawingWorkspace,
    terrainStudy,
    ...visibility,
    adoptResearch: (area: LocalCollection) => {
      researchBoundary.adopt(area);
      measurement.setPicking(false);
      drawing.setPicking(false);
      rf.setPicking(null);
      visibility.setVisible('research', true);
    },
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
            researchBoundary.discardImported();
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
      setDragSite: (point: 'origin' | 'receiver') => {
        measurement.setPicking(false);
        drawing.setPicking(false);
        researchDrawing.setPicking(false);
        rf.setDragSite(point);
      },
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
      if (label !== 'Measure distance and area') measurement.setPicking(false);
      if (label !== 'Draw on map') drawing.setPicking(false);
      if (label !== 'Research area') researchDrawing.setPicking(false);
      if (label !== 'RF link calculator') rf.setPicking(null);
    },
  };
}
