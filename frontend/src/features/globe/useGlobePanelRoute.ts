/** Keeps the open map tool in the `panel` query parameter so a link reopens it. */
import { useRef } from 'react';
import { useLocation, useSearchParams } from 'react-router';
import { mapPanelId, readMapPanel } from '@/lib/mapLayerDirectory';
import type { ShowPanel } from './GlobeControls';

export function useGlobePanelRoute() {
  const [params, setParams] = useSearchParams();
  const location = useLocation();
  // Lets controls outside the rails, such as the heading's skip link, open a panel.
  const showPanel = useRef<ShowPanel | null>(null);
  return {
    requestedPanel: readMapPanel(params),
    /** A new history entry re-applies the requested panel even when its name is unchanged. */
    requestKey: location.key,
    showPanel,
    /** Records user navigation only; an unchanged query never adds a history entry. */
    onPanelChange: (label: string | null) => {
      const next = new URLSearchParams(params);
      if (label) next.set('panel', mapPanelId(label) ?? label);
      else next.delete('panel');
      if (next.toString() !== params.toString()) setParams(next);
    },
  };
}

export type GlobePanelRoute = ReturnType<typeof useGlobePanelRoute>;
