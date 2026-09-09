import { useEffect, useMemo } from 'react';
import type { Layer } from '@deck.gl/core';
import type { Category, LiveEvent } from '@/lib/api/eventSchemas';
import type { JamCell } from '@/lib/api/aviation';
import type { ViewMode } from '@/stores/globe';
import type { GlobeEngineHandle } from './useGlobeEngine';
import type { Cluster } from './layers/clusters';
import { buildEventLayers } from './layers/registry';
import { buildJamLayer } from './layers/jamming';
import { buildTerminatorLayer } from './layers/terminator';

interface Scene {
  engine: GlobeEngineHandle;
  events: readonly LiveEvent[];
  hidden: readonly Category[];
  selectedId: string | null;
  highlightedId: string | null;
  onPick: (event: LiveEvent | null, position?: readonly [number, number]) => void;
  onCluster: (cluster: Cluster) => void;
  onJam: (cell: JamCell) => void;
  jamCells: readonly JamCell[];
  jamSelection?: JamCell | null;
  gridLayers: readonly Layer[];
  cameraLayers: readonly Layer[];
  infrastructureLayers?: readonly Layer[];
  measured: readonly Layer[];
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
  gridLayers,
  cameraLayers,
  infrastructureLayers,
  measured,
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
}: Scene) {
  const eventLayers = useMemo(
    () =>
      supported
        ? buildEventLayers(events, hidden, onPick, selectedId ?? highlightedId, {
            zoom,
            onCluster,
            globe: mode === 'globe',
          })
        : [],
    [hidden, onCluster, onPick, events, selectedId, supported, zoom, mode, highlightedId],
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
        ...gridLayers,
        ...(infrastructureLayers ?? []),
        ...eventLayers,
        ...cameraLayers,
        ...measured,
      ]);
  }, [
    engine,
    eventLayers,
    jam,
    night,
    supported,
    measured,
    gridLayers,
    cameraLayers,
    infrastructureLayers,
  ]);

  // The wall screen turns the globe slowly; lite mode and the flat map keep it still.
  useEffect(() => {
    if (!supported) return;
    engine.spin(opsRoom && mode === 'globe' && !lite && !reducedMotion && visible);
    return () => {
      engine.spin(false);
    };
  }, [engine, lite, mode, opsRoom, reducedMotion, supported, visible]);
}
