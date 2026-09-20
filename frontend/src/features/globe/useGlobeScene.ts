import { useEffect, useMemo } from 'react';
import type { GlobeLayerGroups } from './useGlobeLayerGroups';
import type { Category, LiveEvent } from '@/lib/api/eventSchemas';
import type { JamCell } from '@/lib/api/aviation';
import type { ViewMode } from '@/stores/globe';
import type { GlobeEngineHandle } from './useGlobeEngine';
import type { Cluster } from './layers/clusters';
import { buildEventLayers } from './layers/registry';
import { buildJamLayer } from './layers/jamming';
import { buildTerminatorLayer } from './layers/terminator';

interface Scene {
  engine: Pick<GlobeEngineHandle, 'setLayers' | 'spin'>;
  events: readonly LiveEvent[];
  hidden: readonly Category[];
  selectedId: string | null;
  highlightedId: string | null;
  onPick: (event: LiveEvent | null, position?: readonly [number, number]) => void;
  onCluster: (cluster: Cluster) => void;
  onJam: (cell: JamCell) => void;
  jamCells: readonly JamCell[];
  jamSelection?: JamCell | null;
  /** Catalogue groups in draw order; events marks the event layer position. */
  layerGroups: GlobeLayerGroups;
  supported: boolean;
  terminator: boolean;
  lite: boolean;
  interference: boolean;
  opsRoom: boolean;
  reducedMotion: boolean;
  visible: boolean;
  now: number;
  zoom: number;
  mode: ViewMode;
  symbolMode: ViewMode;
}

/** Compose catalogue, event and contextual layers through one engine owner. */
export function useGlobeScene({
  engine,
  events,
  hidden,
  selectedId,
  highlightedId,
  onPick,
  onCluster,
  onJam,
  jamCells,
  jamSelection = null,
  layerGroups,
  supported,
  terminator,
  lite,
  interference,
  opsRoom,
  reducedMotion,
  visible,
  now,
  zoom,
  mode,
  symbolMode,
}: Scene) {
  const eventLayers = useMemo(
    () =>
      supported
        ? buildEventLayers(events, hidden, onPick, selectedId ?? highlightedId, {
            zoom,
            onCluster,
            globe: symbolMode === 'globe',
          })
        : [],
    [hidden, onCluster, onPick, events, selectedId, supported, zoom, symbolMode, highlightedId],
  );
  const night = useMemo(
    () => (supported && terminator && !lite ? [buildTerminatorLayer(new Date(now))] : []),
    [lite, now, supported, terminator],
  );
  const jam = useMemo(
    () => (supported && interference ? buildJamLayer(jamCells, onJam, jamSelection) : null),
    [interference, jamCells, supported, onJam, jamSelection],
  );
  useEffect(() => {
    if (supported)
      engine.setLayers([
        ...night,
        ...(jam === null ? [] : [jam]),
        ...layerGroups.flatMap((group) => (group === 'events' ? eventLayers : group)),
      ]);
  }, [engine, eventLayers, jam, night, supported, layerGroups]);

  // The wall screen turns the globe slowly; lite mode and the flat map keep it still.
  useEffect(() => {
    if (!supported) return;
    engine.spin(opsRoom && mode === 'globe' && !lite && !reducedMotion && visible);
    return () => {
      engine.spin(false);
    };
  }, [engine, lite, mode, opsRoom, reducedMotion, supported, visible]);
}
