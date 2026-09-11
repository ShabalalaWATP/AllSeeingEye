import { useId, useMemo } from 'react';
import type { LiveEvent } from '@/lib/api/eventSchemas';
import type { FlightFilter } from './flightFilters';
import { TrafficList } from './TrafficList';
import { TrafficRefinementControls } from './TrafficRefinementControls';
import { matchesTrafficRefinement, type TrafficRefinementsState } from './trafficRefinements';
import { MapToolIntro } from '@/components/maps/MapToolIntro';

export interface TrafficPanelProps {
  kind: 'aircraft' | 'vessels';
  filter: FlightFilter;
  onChange?: ((value: FlightFilter) => void) | undefined;
  count: number;
  events?: readonly LiveEvent[] | undefined;
  available?: number | undefined;
  onSelect?: ((event: LiveEvent) => void) | undefined;
  selectionDisabled?: boolean;
  refinements?: TrafficRefinementsState | undefined;
}

/** One content component for the shared category drawer and isolated control fixtures. */
export function TrafficPanel({
  kind,
  filter,
  onChange,
  count,
  events,
  available,
  onSelect,
  selectionDisabled = false,
  refinements,
}: TrafficPanelProps) {
  const id = useId();
  const applied = refinements?.applied;
  const shown = useMemo(
    () =>
      applied ? events?.filter((event) => matchesTrafficRefinement(event, kind, applied)) : events,
    [events, kind, applied],
  );
  return (
    <div className="map-tool-workspace">
      <MapToolIntro
        title={kind === 'aircraft' ? 'Aircraft' : 'Vessels'}
        description="Filter loaded positions, then select a result to locate it on the map."
      />
      {onChange && (
        <fieldset>
          <legend className="mb-2 text-xs text-muted">
            {kind === 'aircraft' ? 'Aircraft shown' : 'Vessels shown'}
          </legend>
          <div className="map-tool-choice-grid">
            {(['all', 'military'] as const).map((value) => (
              <label key={value} className="map-tool-radio-option">
                <input
                  type="radio"
                  name={id}
                  value={value}
                  checked={filter === value}
                  onChange={() => onChange(value)}
                  className="sr-only"
                />
                <span>
                  {value === 'all'
                    ? kind === 'aircraft'
                      ? 'All aircraft'
                      : 'All vessels'
                    : 'Military only'}
                </span>
              </label>
            ))}
          </div>
        </fieldset>
      )}
      <p className={`text-xs ${kind === 'aircraft' ? 'text-amber-300' : 'text-fuchsia-300'}`}>
        {count}{' '}
        {kind === 'aircraft'
          ? 'provider-labelled military aircraft loaded'
          : 'vessels labelled as military operations'}
      </p>
      {refinements && <TrafficRefinementControls kind={kind} state={refinements} />}
      {shown && onSelect && (
        <TrafficList
          key={
            refinements
              ? `${filter}:${refinements.applied.query}:${refinements.source}:${refinements.ground}`
              : kind
          }
          events={shown}
          kind={kind}
          available={available}
          onSelect={onSelect}
          selectionDisabled={selectionDisabled}
          searchEnabled={!refinements}
        />
      )}
      <details className="map-tool-disclosure">
        <summary className="min-h-9 cursor-pointer py-2">Source and coverage</summary>
        <p className="leading-relaxed">
          {kind === 'aircraft'
            ? 'Classification comes from the public provider. Reception is incomplete; hidden transponders and aircraft outside receiver coverage are not shown. This filter does not establish a flight’s mission.'
            : 'Purple identifies reported military operations from AIS ship type or an explicit provider label. This does not verify naval ownership. Position and classification coverage vary.'}
        </p>
        {kind === 'vessels' && (
          <p className="mt-2 leading-relaxed">
            AISStream provides worldwide receiver coverage where available. Fintraffic covers
            Finnish waterways; BarentsWatch adds Norwegian and Arctic waters. Only configured
            providers contribute positions. Reception is incomplete and old reports expire.
          </p>
        )}
      </details>
    </div>
  );
}
