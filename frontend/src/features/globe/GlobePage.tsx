/**
 * The root view: a full-bleed 3D globe (default) with an explicit Map mode
 * toggle, live event markers, the layer panel, the ticker and the inspector.
 * When WebGL2 is unavailable the engine is not mounted and the page explains
 * why; the panels still work from the event mirror.
 */
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

import { Alert } from '@/components/ui/Alert';
import type { LiveEvent } from '@/lib/api/eventSchemas';
import { countByCategory, selectSelectedEvent, useEventsStore } from '@/stores/events';
import { useGlobeStore } from '@/stores/globe';

import { EventInspector } from './EventInspector';
import { LayerPanel } from './LayerPanel';
import { ModeToolbar } from './ModeToolbar';
import { Ticker } from './Ticker';
import { buildEventLayers } from './layers/registry';
import { useGlobeEngine } from './useGlobeEngine';
import { useLiveEvents } from './useLiveEvents';
import { useNow } from './useNow';
import { hasWebGl2 } from './webgl';

/** Zoom used when the user focuses an event from the ticker. */
export const FOCUS_ZOOM = 4;

export default function GlobePage() {
  const mode = useGlobeStore((state) => state.mode);
  const setMode = useGlobeStore((state) => state.setMode);
  const [supported] = useState(() => hasWebGl2());
  const containerRef = useRef<HTMLDivElement>(null);
  const engine = useGlobeEngine(containerRef, mode, supported);
  useLiveEvents();
  const now = useNow();

  const list = useEventsStore((state) => state.list);
  const hidden = useEventsStore((state) => state.hidden);
  const selectedId = useEventsStore((state) => state.selectedId);
  const selected = useEventsStore(selectSelectedEvent);
  const stats = useEventsStore((state) => state.stats);
  const status = useEventsStore((state) => state.status);
  const error = useEventsStore((state) => state.error);
  const select = useEventsStore((state) => state.select);
  const toggleCategory = useEventsStore((state) => state.toggleCategory);
  const counts = useMemo(() => countByCategory(list), [list]);

  const onPick = useCallback(
    (event: LiveEvent | null) => {
      select(event?.id ?? null);
    },
    [select],
  );

  useEffect(() => {
    if (!supported) return;
    engine.setLayers(buildEventLayers(list, hidden, onPick, selectedId));
  }, [engine, hidden, list, onPick, selectedId, supported]);

  const focus = useCallback(
    (event: LiveEvent) => {
      select(event.id);
      if (event.point !== null) {
        engine.flyTo({ center: [event.point.lon, event.point.lat], zoom: FOCUS_ZOOM });
      }
    },
    [engine, select],
  );

  const close = useCallback(() => {
    select(null);
  }, [select]);

  return (
    // Fills the shell's relative <main> directly: a percentage height would collapse
    // because the main area takes its height from flex, not from an explicit value.
    <div className="absolute inset-0 bg-ground">
      {supported ? (
        <div
          ref={containerRef}
          role="region"
          aria-label={mode === 'globe' ? '3D globe' : 'Map'}
          data-testid="map-container"
          // MapLibre's stylesheet forces position: relative on this element, so it
          // needs an explicit height rather than absolute positioning.
          className="h-full w-full"
        />
      ) : (
        <div className="flex h-full items-center justify-center p-6">
          <Alert tone="warning" title="WebGL2 is required" className="max-w-md">
            The globe needs WebGL2, which this browser or device does not provide. Enable hardware
            acceleration or use a current version of Chrome, Edge, Firefox or Safari.
          </Alert>
        </div>
      )}
      <ModeToolbar mode={mode} onChange={setMode} />
      <Ticker events={list} selectedId={selectedId} now={now} onSelect={focus} />
      <LayerPanel
        counts={counts}
        hidden={hidden}
        stats={stats}
        status={status}
        error={error}
        onToggle={toggleCategory}
      />
      {selected !== null && <EventInspector event={selected} onClose={close} />}
    </div>
  );
}
