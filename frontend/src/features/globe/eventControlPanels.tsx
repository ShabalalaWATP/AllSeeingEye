import type { LiveEvent } from '@/lib/api/eventSchemas';
import type { useDashboardEvents } from './useDashboardEvents';
import { ControlPanel } from './GlobeControls';
import { LayerPanel } from './LayerPanel';
import { PlanFilterPanel } from './PlanFilterPanel';

/** Event controls state their scope separately from independent catalogues. */
export function eventControlPanels(
  data: ReturnType<typeof useDashboardEvents>,
  _onContextSelect: (event: LiveEvent) => void,
) {
  return [
    <ControlPanel key="time" side="right" label="Event time" caption="Time" icon="time">
      <LayerPanel
        counts={data.counts}
        stats={data.stats}
        status={data.status}
        error={data.error}
        windowHours={data.windowHours}
        onWindow={data.setWindow}
        replay={data.replay}
      />
    </ControlPanel>,
    <ControlPanel key="plan" side="right" label="Collection plan" caption="Plan" icon="filter">
      <PlanFilterPanel shown={data.quality.filtered.length} />
    </ControlPanel>,
  ];
}
