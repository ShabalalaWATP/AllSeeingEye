import type { useInfrastructure } from './infrastructure/useInfrastructure';
import type { useInfrastructureSelection } from './infrastructure/useInfrastructureSelection';
import type { useSatelliteFilters } from './useSatelliteFilters';
import type { useConflictFilters } from './useConflictFilters';
import type { useHazardFilters } from './useHazardFilters';
import { ControlPanel } from './GlobeControls';
import { InfrastructurePanel } from './infrastructure/InfrastructurePanel';
import { SatelliteFilterPanel } from './SatelliteFilterPanel';
import { ConflictOverviewPanel } from './ConflictOverviewPanel';
import { HazardFilterPanel } from './HazardFilterPanel';
import { GnssPanel } from './GnssPanel';
import type { ComponentProps } from 'react';

/** Category panels are opened beneath their switches, not duplicated on the rail. */
export function catalogueControlPanels({
  infrastructure,
  focusInfrastructure,
  satellites,
  conflicts,
  conflictOverview,
  hazards,
  gnss,
}: {
  infrastructure: ReturnType<typeof useInfrastructure>;
  focusInfrastructure: ReturnType<typeof useInfrastructureSelection>['focus'];
  satellites: ReturnType<typeof useSatelliteFilters>;
  conflicts: ReturnType<typeof useConflictFilters>;
  conflictOverview: Omit<ComponentProps<typeof ConflictOverviewPanel>, 'reports'>;
  hazards: ReturnType<typeof useHazardFilters>;
  gnss: ComponentProps<typeof GnssPanel>;
}) {
  return [
    <ControlPanel key="gnss" side="left" label="GNSS interference" icon="gnss" entry={false}>
      <GnssPanel {...gnss} />
    </ControlPanel>,
    <ControlPanel key="infrastructure" side="left" label="Infrastructure" icon="infrastructure">
      <InfrastructurePanel state={infrastructure} onSelect={focusInfrastructure} />
    </ControlPanel>,
    <ControlPanel key="satellites" side="left" label="Space" icon="space" entry={false}>
      <h3 className="px-3 pt-3 text-sm font-medium">Satellites</h3>
      <SatelliteFilterPanel {...satellites} />
    </ControlPanel>,
    <ControlPanel
      key="conflicts"
      side="left"
      label="Conflict reports"
      icon="conflict"
      entry={false}
    >
      <ConflictOverviewPanel {...conflictOverview} reports={conflicts} />
    </ControlPanel>,
    <ControlPanel key="hazards" side="left" label="Natural hazards" icon="disaster" entry={false}>
      <HazardFilterPanel {...hazards} />
    </ControlPanel>,
  ];
}
