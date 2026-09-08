import { useCallback, useMemo, useState } from 'react';
import type { Category, LiveEvent } from '@/lib/api/eventSchemas';
import type { JamCell } from '@/lib/api/aviation';
import type { GlobeEngineHandle } from './useGlobeEngine';
import type { MapDetails } from './MapDetailsInspector';
import type { Cluster } from './layers/clusters';
export function useMapPicking(
  events: readonly LiveEvent[],
  hidden: readonly Category[],
  picking: boolean,
  select: (id: string | null) => void,
  engine: GlobeEngineHandle,
) {
  const [details, setDetails] = useState<MapDetails | null>(null);
  const visible = useMemo(
    () => events.filter((event) => !hidden.includes(event.category)),
    [events, hidden],
  );
  const choose = useCallback(
    (event: LiveEvent | null) => {
      if (!picking) {
        setDetails(null);
        select(event?.id ?? null);
      }
    },
    [picking, select],
  );
  const close = useCallback(() => {
    setDetails(null);
    select(null);
  }, [select]);
  const onPick = useCallback(
    (event: LiveEvent | null, position?: readonly [number, number]) => {
      if (picking) return;
      if (!event) {
        choose(null);
        return;
      }
      const hits = position ? (engine.pickObjectsAt?.(...position) ?? []) : [];
      const ids = new Set(
        hits
          .flatMap((hit) =>
            typeof hit === 'object' &&
            hit !== null &&
            'members' in hit &&
            Array.isArray(hit.members)
              ? [hit, ...(hit.members as unknown[])]
              : [hit],
          )
          .flatMap((hit) =>
            typeof hit === 'object' && hit !== null && 'id' in hit && typeof hit.id === 'string'
              ? [hit.id]
              : [],
          ),
      );
      const members = visible.filter(
        (item) =>
          ids.has(item.id) ||
          item.id === event.id ||
          (event.point &&
            item.point &&
            Math.abs(item.point.lon - event.point.lon) < 1e-8 &&
            Math.abs(item.point.lat - event.point.lat) < 1e-8),
      );
      if (members.length > 1 && event.point) {
        select(null);
        setDetails({
          kind: 'cluster',
          cluster: {
            id: `overlap:${event.id}`,
            category: event.category,
            lon: event.point.lon,
            lat: event.point.lat,
            count: members.length,
            maxSeverity: 0,
            members,
          },
        });
      } else choose(event);
    },
    [choose, engine, picking, select, visible],
  );
  const onCluster = useCallback(
    (cluster: Cluster) => {
      if (!picking) {
        select(null);
        setDetails({ kind: 'cluster', cluster });
        engine.flyTo({
          center: [cluster.lon, cluster.lat],
          zoom: Math.min(4, engine.getZoom() + 2.5),
        });
      }
    },
    [engine, picking, select],
  );
  const onJam = useCallback(
    (cell: JamCell) => {
      if (!picking) {
        select(null);
        setDetails({ kind: 'jam', cell });
      }
    },
    [picking, select],
  );
  return { details, visible, choose, close, onPick, onCluster, onJam };
}
