import type { RefObject } from 'react';

import { mapPanelHref } from '@/lib/mapLayerDirectory';
import type { ViewMode } from '@/stores/globe';

import type { ShowPanel } from './GlobeControls';

export const LOADED_EVENTS_PANEL = 'Location quality';
const VIEW_TITLES: Record<ViewMode, string> = { globe: 'Globe view', map: 'Map view' };

/**
 * The page heading and a direct, canvas-free route to the loaded-event list. Both are
 * visually hidden; the link appears when it receives keyboard focus.
 */
export function GlobeHeading({
  mode,
  showRef,
}: {
  mode: ViewMode;
  /** Absent when the map tools are hidden, as in the ops room. */
  showRef: RefObject<ShowPanel | null> | null;
}) {
  return (
    <>
      <h1 className="sr-only">{VIEW_TITLES[mode]}</h1>
      {showRef && (
        <a
          href={mapPanelHref(LOADED_EVENTS_PANEL)}
          onClick={(event) => {
            const show = showRef.current;
            if (show === null || event.metaKey || event.ctrlKey || event.shiftKey) return;
            event.preventDefault();
            show(LOADED_EVENTS_PANEL, event.currentTarget, 'input[type="search"]');
          }}
          className="sr-only rounded border border-control-border bg-surface px-3 py-2 text-sm text-text focus:not-sr-only focus:absolute focus:top-3 focus:left-3 focus:z-50"
        >
          Browse loaded events as a list
        </a>
      )}
    </>
  );
}
