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
    <ControlPanel key="time" side="right" label="Event time" caption="Time" icon="time">
      <LayerPanel
        counts={data.counts}
        stats={data.stats}
        status={data.status}
        error={data.error}
        windowHours={data.windowHours}
        onWindow={data.setWindow}
      />
    </ControlPanel>,
  ];
}
