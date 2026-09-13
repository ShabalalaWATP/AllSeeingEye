import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

import { fetchUkraineControl, type Settlement, type UkraineControl } from '@/lib/api/ukraine';
import { useResource } from '@/lib/hooks/useResource';
import type { MapEngine } from '@/lib/map/MapEngine';
import { createMapLibreEngine } from '@/lib/map/MapLibreEngine';
import { hasWebGl2 } from '@/lib/map/webgl';
import { useAuthStore } from '@/stores/auth';

import { UKRAINE_BOUNDS, buildControlLayers } from './controlLayers';

export interface Hover {
  settlement: Settlement;
  x: number;
  y: number;
}

/** A 2D mercator map fitted to Ukraine, drawing the packaged control snapshot. */
export function useUkraineMap(load: () => Promise<UkraineControl> = fetchUkraineControl) {
  const loader = useCallback(() => load(), [load]);
  const control = useResource<UkraineControl>(loader);
  const supported = useMemo(() => hasWebGl2(), []);
  const container = useRef<HTMLDivElement>(null);
  const engine = useRef<MapEngine | null>(null);
  const [hover, setHover] = useState<Hover | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    if (!container.current || !supported) return;
    const map = createMapLibreEngine({
      authHeader: () => useAuthStore.getState().accessToken,
    });
    map.setProjection('mercator');
    map.setBaseLayer('dark');
    map.mount(container.current);
    map.setLite(true);
    map.fitBounds(UKRAINE_BOUNDS, { padding: 24, maxZoom: 7 });
    const stopErrors = map.on('error', () => setFailed(true));
    engine.current = map;
    return () => {
      stopErrors();
      map.destroy();
      engine.current = null;
    };
  }, [supported]);

  const onHover = useCallback((settlement: Settlement | null, x: number, y: number) => {
    setHover(settlement ? { settlement, x, y } : null);
  }, []);

  useEffect(() => {
    if (!engine.current || !control.data) return;
    engine.current.setLayers(buildControlLayers(control.data, onHover));
  }, [control.data, onHover]);

  const refit = useCallback(
    () => engine.current?.fitBounds(UKRAINE_BOUNDS, { padding: 24, maxZoom: 7 }),
    [],
  );

  return { container, supported, failed, hover, control, refit };
}
