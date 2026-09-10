import type { LiveEvent } from '@/lib/api/eventSchemas';
import type { useDashboardEvents } from './useDashboardEvents';
import { ControlPanel } from './GlobeControls';
import { LayerPanel } from './LayerPanel';
import { ConnectivityPanel } from './context/ConnectivityPanel';

/** Event controls state their scope separately from independent catalogues. */
export function eventControlPanels(
  data: ReturnType<typeof useDashboardEvents>,
  onContextSelect: (event: LiveEvent) => void,
) {
  return [
    <ControlPanel
      key="network"
      side="left"
      label="Connectivity signals"
      caption="Network"
      icon="connectivity"
    >
      <ConnectivityPanel country={data.country} onSelect={onContextSelect} />
    </ControlPanel>,
    <ControlPanel key="topics" side="left" label="Topics & time" icon="topics">
      <LayerPanel
        counts={data.counts}
        hidden={data.hidden}
        stats={data.stats}
        status={data.status}
        error={data.error}
        windowHours={data.windowHours}
        onWindow={data.setWindow}
        onToggle={data.toggleCategory}
      />
    </ControlPanel>,
  ];
}
