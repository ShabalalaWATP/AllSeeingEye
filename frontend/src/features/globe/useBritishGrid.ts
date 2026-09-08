import { useEffect, useMemo, useState } from 'react';
import { PathLayer } from '@deck.gl/layers';

import { britishGridLines } from '@/lib/map/britishGrid';
import type { GridLine } from '@/lib/map/britishGrid';
import type { GlobeEngineHandle } from './useGlobeEngine';

const EMPTY_LAYERS: PathLayer<GridLine>[] = [];

export function useBritishGrid(engine: GlobeEngineHandle) {
  const [enabled, setEnabled] = useState(false);
  const [zoom, setZoom] = useState(() => engine.getZoom());
  useEffect(() => engine.onView((view) => setZoom(Math.floor(view.zoom))), [engine]);
  const gridZoom = zoom >= 8 ? 8 : zoom >= 5 ? 5 : 0;
  const layers = useMemo(() => {
    const lines = enabled ? britishGridLines(gridZoom) : [];
    return lines.length === 0
      ? EMPTY_LAYERS
      : [
          new PathLayer<GridLine>({
            id: 'british-national-grid',
            data: lines,
            pickable: false,
            getPath: (line) => line.path,
            getColor: (line) => [151, 188, 197, line.major ? 150 : 65],
            getWidth: (line) => (line.major ? 1.4 : 0.7),
            widthUnits: 'pixels',
          }),
        ];
  }, [enabled, gridZoom]);
  return { enabled, setEnabled, layers, zoom };
}
