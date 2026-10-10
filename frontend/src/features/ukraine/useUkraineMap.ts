import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

import { fetchUkraineControl, type Settlement, type UkraineControl } from '@/lib/api/ukraine';
import {
  fetchUkraineFrontline,
  fetchUkraineSpotted,
  type SpottedLoss,
  type UkraineFrontline,
  type UkraineSpotted,
} from '@/lib/api/ukraineMap';
import { useResource } from '@/lib/hooks/useResource';
import type { MapEngine } from '@/lib/map/MapEngine';
import { createMapLibreEngine } from '@/lib/map/MapLibreEngine';
import { hasWebGl2 } from '@/lib/map/webgl';
import { useAuthStore } from '@/stores/auth';
import { mapSourceAllowed, sourceUnavailable, useMapSourcePolicy } from '@/lib/map/sourcePolicy';

import { UKRAINE_BOUNDS, buildControlLayers } from './controlLayers';
import { buildFrontlineLayers, buildSpottedLayer } from './providerLayers';

export type Hover =
  | { kind: 'settlement'; settlement: Settlement; x: number; y: number }
  | { kind: 'loss'; loss: SpottedLoss; x: number; y: number };

export interface MapLoaders {
  control?: () => Promise<UkraineControl>;
  frontline?: () => Promise<UkraineFrontline>;
  spotted?: () => Promise<UkraineSpotted>;
}

/** A 2D mercator map fitted to Ukraine: the control snapshot, then any flagged provider layers. */
export function useUkraineMap(loaders: MapLoaders = {}) {
  const policy = useMapSourcePolicy();
  const policyReason = sourceUnavailable(policy, 'map:openfreemap');
  const loadControl = loaders.control ?? fetchUkraineControl;
  const loadFrontline = loaders.frontline ?? fetchUkraineFrontline;
  const loadSpotted = loaders.spotted ?? fetchUkraineSpotted;
  const control = useResource<UkraineControl>(useCallback(() => loadControl(), [loadControl]));
  const frontline = useResource<UkraineFrontline>(
    useCallback(() => loadFrontline(), [loadFrontline]),
  );
  const spotted = useResource<UkraineSpotted>(useCallback(() => loadSpotted(), [loadSpotted]));
  const supported = useMemo(() => hasWebGl2(), []);
  const container = useRef<HTMLDivElement>(null);
  const engine = useRef<MapEngine | null>(null);
  const [hover, setHover] = useState<Hover | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    if (!container.current || !supported || policyReason) return;
    const map = createMapLibreEngine({
      authHeader: () => useAuthStore.getState().accessToken,
      sourceAllowed: mapSourceAllowed,
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
  }, [supported, policyReason]);

  const onSettlement = useCallback((settlement: Settlement | null, x: number, y: number) => {
    setHover(settlement ? { kind: 'settlement', settlement, x, y } : null);
  }, []);
  const onLoss = useCallback((loss: SpottedLoss | null, x: number, y: number) => {
    setHover(loss ? { kind: 'loss', loss, x, y } : null);
  }, []);

  useEffect(() => {
    if (!engine.current || !control.data) return;
    engine.current.setLayers([
      ...buildControlLayers(control.data, onSettlement),
      ...buildFrontlineLayers(frontline.data),
      ...buildSpottedLayer(spotted.data, onLoss),
    ]);
  }, [control.data, frontline.data, spotted.data, onSettlement, onLoss, policyReason]);

  const refit = useCallback(
    () => engine.current?.fitBounds(UKRAINE_BOUNDS, { padding: 24, maxZoom: 7 }),
    [],
  );

  return { container, supported, failed, policyReason, hover, control, frontline, spotted, refit };
}
