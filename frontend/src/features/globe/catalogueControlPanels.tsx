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
import { CyberFilterPanel } from './CyberFilterPanel';
import { FiresFilterPanel } from './FiresFilterPanel';
import { NewsPanel } from './NewsPanel';
import { useMemo, type ComponentProps } from 'react';
import type { LiveEvent } from '@/lib/api/eventSchemas';
import { ContextTabs } from './context/ContextTabs';
import { SpaceWeatherPanel } from './context/SpaceWeatherPanel';
import { locationQuality, type LocationQualityFilter } from './geographicPrecision';

function SatelliteContent({
  satellites,
  qualityFilter,
  ...props
}: {
  satellites: ReturnType<typeof useSatelliteFilters>;
  qualityFilter: LocationQualityFilter;
  selectedId: string | null;
  onSelect: (event: LiveEvent) => void;
}) {
  const results = useMemo(
    () =>
      satellites.results.filter(
        (event) => qualityFilter === 'all' || locationQuality(event) === qualityFilter,
      ),
    [satellites.results, qualityFilter],
  );
  return (
    <>
      {qualityFilter !== 'all' && (
        <p className="px-3 pt-3 text-xs text-muted">
          The active location-quality filter also applies to this list.
        </p>
      )}
      <SatelliteFilterPanel {...satellites} {...props} results={results} />
    </>
  );
}

/** Category panels are opened beneath their switches, not duplicated on the rail. */
export function catalogueControlPanels({
  infrastructure,
  focusInfrastructure,
  satellites,
  conflicts,
  conflictOverview,
  hazards,
  gnss,
  country,
  onContextSelect,
  onSatelliteSelect,
  selectedId,
  qualityFilter,
  cyber,
  fires,
  news,
}: {
  infrastructure: ReturnType<typeof useInfrastructure>;
  focusInfrastructure: ReturnType<typeof useInfrastructureSelection>['focus'];
  satellites: ReturnType<typeof useSatelliteFilters>;
  conflicts: ReturnType<typeof useConflictFilters>;
  conflictOverview: Omit<ComponentProps<typeof ConflictOverviewPanel>, 'reports'>;
  hazards: ReturnType<typeof useHazardFilters>;
  gnss: ComponentProps<typeof GnssPanel>;
  country: string | null;
  onContextSelect: (event: LiveEvent) => void;
  onSatelliteSelect: (event: LiveEvent) => void;
  selectedId: string | null;
  qualityFilter: LocationQualityFilter;
  cyber: ComponentProps<typeof CyberFilterPanel>;
  fires: ComponentProps<typeof FiresFilterPanel>;
  news: ComponentProps<typeof NewsPanel>;
}) {
  return [
    <ControlPanel key="fires" side="left" label="Fires" icon="firms" entry={false}>
      <FiresFilterPanel {...fires} />
    </ControlPanel>,
    <ControlPanel key="news" side="left" label="News briefing" icon="news" entry={false}>
      <NewsPanel {...news} />
    </ControlPanel>,
    <ControlPanel
      key="cyber"
      side="left"
      label="Cyber threat intelligence"
      icon="cyber"
      entry={false}
    >
      <CyberFilterPanel {...cyber} />
    </ControlPanel>,
    <ControlPanel key="gnss" side="left" label="GNSS interference" icon="gnss" entry={false}>
      <GnssPanel {...gnss} />
    </ControlPanel>,
    <ControlPanel key="infrastructure" side="left" label="Infrastructure" icon="infrastructure">
      <InfrastructurePanel state={infrastructure} onSelect={focusInfrastructure} />
    </ControlPanel>,
    <ControlPanel key="satellites" side="left" label="Space" icon="space" entry={false}>
      <ContextTabs
        label="Space view"
        primaryLabel="Satellites"
        secondaryLabel="Space weather"
        primary={
          <SatelliteContent
            satellites={satellites}
            selectedId={selectedId}
            onSelect={onSatelliteSelect}
            qualityFilter={qualityFilter}
          />
        }
        secondary={<SpaceWeatherPanel country={country} onSelect={onContextSelect} />}
      />
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
