import { useCallback, useEffect, useMemo, useState, useSyncExternalStore } from 'react';
import { ScatterplotLayer } from '@deck.gl/layers';
import type { Layer } from '@deck.gl/core';
import type { LiveEvent } from '@/lib/api/eventSchemas';
import { useAuthStore } from '@/stores/auth';
import { subscribeWorkspaceAccess, workspaceRevision } from '@/lib/workspaceAccess';
import { isMappedEvent } from '../geographicPrecision';
import type { ViewMode } from '@/stores/globe';
import { buildIconLayer } from '../layers/icons';

/** One explicit snapshot selection, separate from the bounded viewport collection. */
export function useContextSelection(
  country: string | null,
  picking: boolean,
  mode: ViewMode = 'map',
) {
  const actor = useAuthStore(
    (state) => `${state.status}:${state.user?.id}:${state.user?.role}:${state.user?.is_active}`,
  );
  const revision = useSyncExternalStore(subscribeWorkspaceAccess, workspaceRevision);
  const scope = `${actor}:${revision}:${country}`;
  const [selection, setSelection] = useState<{ scope: string; event: LiveEvent } | null>(null);
  if (selection && selection.scope !== scope) setSelection(null);
  const event = selection?.scope === scope ? selection.event : null;
  const close = useCallback(() => setSelection(null), []);
  useEffect(() => {
    const offAccess = subscribeWorkspaceAccess(close);
    const offAuth = useAuthStore.subscribe((next, previous) => {
      if (
        next.status !== previous.status ||
        next.user?.id !== previous.user?.id ||
        next.user?.role !== previous.user?.role ||
        next.user?.is_active !== previous.user?.is_active
      )
        close();
    });
    return () => {
      offAccess();
      offAuth();
    };
  }, [close]);
  const choose = useCallback(
    (next: LiveEvent) => {
      if (!picking && actor.startsWith('authenticated:') && actor.endsWith(':true'))
        setSelection({ scope, event: next });
    },
    [actor, scope, picking],
  );
  const layers = useMemo(
    () =>
      event && isMappedEvent(event)
        ? [
            new ScatterplotLayer<LiveEvent>({
              id: 'context-selected-position',
              data: [event],
              pickable: false,
              getPosition: (item) => [item.point?.lon ?? NaN, item.point?.lat ?? NaN],
              radiusUnits: 'pixels',
              getRadius: 12,
              stroked: true,
              filled: true,
              lineWidthUnits: 'pixels',
              getLineWidth: 2,
              getLineColor: [121, 216, 235, 255],
              getFillColor: [121, 216, 235, 55],
            }),
          ]
        : [],
    [event],
  );
  const cyberIcon = useMemo<Layer | null>(() => {
    if (event?.category !== 'cyber' || !isMappedEvent(event)) return null;
    const icon = buildIconLayer([event], () => undefined, event.id, mode === 'globe');
    return icon ? (icon.clone({ id: 'context-selected-cyber', pickable: false }) as Layer) : null;
  }, [event, mode]);
  const combined = useMemo(
    () => (cyberIcon ? [...layers, cyberIcon] : layers),
    [layers, cyberIcon],
  );
  return { event, choose, close, layers: combined };
}
