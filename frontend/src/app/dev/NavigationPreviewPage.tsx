/**
 * Development-only page (registered when import.meta.env.DEV) that frames the
 * reworked navigation: the grouped rail, the search palette and the map guide.
 * Layer state is a local fixture; nothing here reaches the API with a credential.
 */
import { useState, useSyncExternalStore } from 'react';

import { CommandPalette } from '@/app/shell/CommandPalette';
import { LeftRail } from '@/app/shell/LeftRail';
import { MobileNavigation } from '@/app/shell/MobileNavigation';
import { TopBar } from '@/app/shell/TopBar';
import { ControlPanel, GlobeControls } from '@/features/globe/GlobeControls';
import { MapGuide } from '@/features/globe/MapGuidePanel';
import type { MapGuideSources } from '@/features/globe/mapGuideControls';
import { MAP_GUIDE_PANEL } from '@/lib/mapLayerDirectory';
import { useShellStore } from '@/stores/shell';
import '@/features/globe/dashboard.css';

function previewSources(enabled: boolean, setEnabled: (value: boolean) => void): MapGuideSources {
  const noop = () => undefined;
  return {
    events: {
      fires: { enabled, toggleEnabled: () => setEnabled(!enabled) },
      observations: { visibility: { aircraft: true, vessels: false, firms: false }, toggle: noop },
    },
    cameras: { enabled, setEnabled },
    figures: { enabled: false, setEnabled },
    regions: { showRegions: false, setShowRegions: setEnabled },
    grid: { enabled: false, setEnabled },
  } as unknown as MapGuideSources;
}

const subscribe = (onChange: () => void) => {
  window.addEventListener('hashchange', onChange);
  return () => window.removeEventListener('hashchange', onChange);
};
const readHash = () => window.location.hash.replace('#', '');

export default function NavigationPreviewPage() {
  const [enabled, setEnabled] = useState(false);
  const [drawer, setDrawer] = useState(true);
  const hash = useSyncExternalStore(subscribe, readHash, () => '');
  const paletteOpen = useShellStore((state) => state.paletteOpen);
  const openPalette = useShellStore((state) => state.openPalette);
  if (hash === 'mobile') {
    return drawer ? (
      <MobileNavigation
        onClose={() => {
          setDrawer(false);
        }}
      />
    ) : (
      <button
        type="button"
        onClick={() => {
          setDrawer(true);
        }}
        className="m-4 min-h-11 rounded-md border border-line px-3 text-sm text-text"
      >
        Open navigation
      </button>
    );
  }
  return (
    <div className="flex h-dvh w-full overflow-hidden bg-ground text-text">
      <LeftRail />
      <div className="flex min-w-0 flex-1 flex-col">
        <TopBar />
        <main className="relative min-h-0 flex-1 overflow-y-auto">
          <div className="globe-dashboard absolute inset-0 bg-ground">
            <GlobeControls layers={null} initial={MAP_GUIDE_PANEL}>
              {(open) => [
                <ControlPanel
                  key="guide"
                  side="left"
                  label={MAP_GUIDE_PANEL}
                  icon="guide"
                  caption="Guide"
                >
                  <MapGuide open={open} sources={previewSources(enabled, setEnabled)} />
                </ControlPanel>,
                <ControlPanel
                  key="conflict"
                  side="left"
                  label="Conflict reports"
                  icon="conflict"
                  entry={false}
                >
                  <p className="p-4 text-sm text-muted">Conflict report filters live here.</p>
                </ControlPanel>,
              ]}
            </GlobeControls>
          </div>
          <div className="relative p-6">
            <button
              type="button"
              onClick={openPalette}
              className="min-h-11 rounded-md border border-line px-3 text-sm"
            >
              Open the search palette
            </button>
          </div>
        </main>
      </div>
      {paletteOpen && <CommandPalette />}
    </div>
  );
}
