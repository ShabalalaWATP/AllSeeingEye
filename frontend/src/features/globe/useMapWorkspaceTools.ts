import { useEffect, useEffectEvent, useMemo, useState } from 'react';
import { PathLayer } from '@deck.gl/layers';
import type { ViewMode } from '@/stores/globe';
import type { NavigationRoute } from '@/lib/api/navigation';
import { measurementLayers } from '@/lib/map/measurementLayers';
import { drawingLayers } from '@/lib/map/drawingLayers';
import { useMapDrawing } from './useMapDrawing';
import { useMapMeasurement } from './useMapMeasurement';
import type { GlobeEngineHandle } from './useGlobeEngine';

/** One click owner prevents drawings, measurements and item selections competing. */
export function useMapWorkspaceTools(engine: GlobeEngineHandle, enabled: boolean, mode: ViewMode) {
  const measurement = useMapMeasurement(engine, enabled);
  const drawing = useMapDrawing(engine, enabled);
  const [route, setRoute] = useState<NavigationRoute | null>(null);
  const stopPicking = useEffectEvent(() => {
    measurement.setPicking(false);
    drawing.setPicking(false);
  });
  useEffect(() => {
    if (!enabled) stopPicking();
  }, [enabled]);

  const layers = useMemo(
    () => [
      ...measurementLayers(measurement.points, measurement.mode, mode === 'map'),
      ...drawingLayers(drawing.points, drawing.mode, mode === 'map'),
      ...(route
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
        : []),
    ],
    [measurement.points, measurement.mode, drawing.points, drawing.mode, route, mode],
  );
  return {
    measurement: {
      ...measurement,
      setPicking: (active: boolean) => {
        if (active) drawing.setPicking(false);
        measurement.setPicking(active);
      },
    },
    drawing: {
      ...drawing,
      setPicking: (active: boolean) => {
        if (active) measurement.setPicking(false);
        drawing.setPicking(active);
      },
    },
    layers,
    setRoute,
    picking: measurement.picking || drawing.picking,
    activatePanel: (label: string | null) => {
      if (label !== null && label !== 'Measure distance and area') measurement.setPicking(false);
      if (label !== 'Draw on map') drawing.setPicking(false);
    },
  };
}
