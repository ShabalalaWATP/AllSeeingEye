import { useMemo } from 'react';
import type { LiveEvent } from '@/lib/api/eventSchemas';
import { isMilitaryAircraft, isMilitaryVessel } from '@/lib/traffic';
import { ControlPanel } from './GlobeControls';
import {
  observationKind,
  filterObservations,
  type useObservationFilters,
} from './ObservationControls';
import { TrafficPanel } from './TrafficPanel';
import { ContextTabs } from './context/ContextTabs';
import { NavigationWarningsPanel } from './context/NavigationWarningsPanel';
import { locationQuality, type LocationQualityFilter } from './geographicPrecision';

interface Props {
  events: readonly LiveEvent[];
  observations: ReturnType<typeof useObservationFilters>;
  onSelect: (event: LiveEvent) => void;
  onContextSelect: (event: LiveEvent) => void;
  selectionDisabled: boolean;
  country: string | null;
  qualityFilter: LocationQualityFilter;
  available: { aircraft?: number; vessels?: number };
}

/** Work happens only inside the mounted drawer, never for closed traffic panels. */
function TrafficContent({ kind, ...props }: Props & { kind: 'aircraft' | 'vessels' }) {
  const { events, observations, qualityFilter } = props;
  const { flightFilter, vesselFilter } = observations;
  const eligible = useMemo(
    () =>
      events.filter(
        (event) =>
          observationKind(event) === kind &&
          (qualityFilter === 'all' || locationQuality(event) === qualityFilter),
      ),
    [events, kind, qualityFilter],
  );
  const shown = useMemo(
    () =>
      filterObservations(
        eligible,
        { aircraft: true, vessels: true, firms: true },
        flightFilter,
        vesselFilter,
      ),
    [eligible, flightFilter, vesselFilter],
  );
  return (
    <TrafficPanel
      key={kind}
      kind={kind}
      filter={kind === 'aircraft' ? flightFilter : vesselFilter}
      onChange={kind === 'aircraft' ? observations.setFlightFilter : observations.setVesselFilter}
      count={eligible.filter(kind === 'aircraft' ? isMilitaryAircraft : isMilitaryVessel).length}
      events={shown}
      available={props.available[kind]}
      onSelect={props.onSelect}
      selectionDisabled={props.selectionDisabled}
      refinements={observations.trafficRefinements[kind]}
    />
  );
}

export function trafficControlPanels(props: Props) {
  return (['aircraft', 'vessels'] as const).map((kind) => (
    <ControlPanel
      key={kind}
      side="left"
      label={kind === 'aircraft' ? 'Flight filters' : 'Boat list'}
      icon={kind}
      entry={false}
    >
      {kind === 'aircraft' ? (
        <TrafficContent key={kind} {...props} kind={kind} />
      ) : (
        <ContextTabs
          label="Maritime view"
          primaryLabel="Vessels"
          secondaryLabel="Navigation warnings"
          primary={<TrafficContent key={kind} {...props} kind={kind} />}
          secondary={
            <NavigationWarningsPanel country={props.country} onSelect={props.onContextSelect} />
          }
        />
      )}
    </ControlPanel>
  ));
}
