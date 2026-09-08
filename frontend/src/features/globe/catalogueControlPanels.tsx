import type { useInfrastructure } from './infrastructure/useInfrastructure';
import type { useInfrastructureSelection } from './infrastructure/useInfrastructureSelection';
import type { useSatelliteFilters } from './useSatelliteFilters';
import type { useConflictFilters } from './useConflictFilters';
import { ControlPanel } from './GlobeControls';
import { InfrastructurePanel } from './infrastructure/InfrastructurePanel';
import { SatelliteFilterPanel } from './SatelliteFilterPanel';
import { ConflictFilterPanel } from './ConflictFilterPanel';

/** Return direct children so GlobeControls can place each catalogue on the left rail. */
export function catalogueControlPanels({
  infrastructure,
  focusInfrastructure,
  satellites,
  conflicts,
}: {
  infrastructure: ReturnType<typeof useInfrastructure>;
  focusInfrastructure: ReturnType<typeof useInfrastructureSelection>['focus'];
  satellites: ReturnType<typeof useSatelliteFilters>;
  conflicts: ReturnType<typeof useConflictFilters>;
}) {
  return [
    <ControlPanel key="infrastructure" side="left" label="Infrastructure" icon="signal">
      <InfrastructurePanel state={infrastructure} onSelect={focusInfrastructure} />
    </ControlPanel>,
    <ControlPanel key="satellites" side="left" label="Satellite filters" icon="filter">
      <SatelliteFilterPanel
        group={satellites.group}
        setGroup={satellites.setGroup}
        counts={satellites.counts}
      />
    </ControlPanel>,
    <ControlPanel key="conflicts" side="left" label="Conflict report filters" icon="filter">
      <ConflictFilterPanel
        group={conflicts.group}
        setGroup={conflicts.setGroup}
        counts={conflicts.counts}
        includeHistorical={conflicts.includeHistorical}
        setIncludeHistorical={conflicts.setIncludeHistorical}
        historicalCount={conflicts.historicalCount}
      />
    </ControlPanel>,
  ];
}
