import type { Category, LiveEvent } from '@/lib/api/eventSchemas';
import { CATEGORY_STYLES } from '@/lib/categories';
import { useEventsStore } from '@/stores/events';
import { useGlobeStore } from '@/stores/globe';
import { observationKind } from './ObservationControls';
import type { ObservationKind, ObservationVisibility } from './ObservationControls';
import { isObservationShown, toggleObservationLayer } from './layerVisibility';
import { MapControlLabel } from './MapControlLabel';
import { MapControlIcon } from './MapControlIcon';
import type { ControlIcon } from './MapControlIcon';
import { FlightLayerControl } from './FlightLayerControl';
import { isMilitaryFlight, matchesFlightFilter, matchesVesselFilter } from './flightFilters';
import type { FlightFilter } from './flightFilters';
import { isMilitaryVessel } from '@/lib/traffic';

const compactCount = new Intl.NumberFormat('en-GB', {
  notation: 'compact',
  maximumFractionDigits: 1,
});

function LayerButton({
  label,
  icon,
  active,
  count,
  onClick,
}: {
  label: string;
  icon: ControlIcon;
  active: boolean;
  count?: number;
  onClick: () => void;
}) {
  return (
    <MapControlLabel
      label={`${label}: ${active ? 'shown' : 'hidden'}${count === undefined ? '' : ` · ${count} loaded`}`}
    >
      <button
        type="button"
        role="switch"
        aria-checked={active}
        aria-label={count === undefined ? `${label} ${active ? 'on' : 'off'}` : `${label} ${count}`}
        title={`${label}: ${active ? 'shown' : 'hidden'}${count === undefined ? '' : ` · ${count} loaded`}`}
        className="map-icon-button"
        onClick={onClick}
      >
        <MapControlIcon name={icon} />
        {count !== undefined && count > 0 && (
          <span aria-hidden="true" className="map-layer-count">
            {compactCount.format(count)}
          </span>
        )}
      </button>
    </MapControlLabel>
  );
}

export function MapLayerRail({
  events,
  counts,
  visibility,
  onToggle,
  flightFilter = 'all',
  onFlightFilter,
  onTrafficSelect,
  vesselFilter = 'all',
  onVesselFilter,
  selectionDisabled = false,
}: {
  events: readonly LiveEvent[];
  counts: Partial<Record<Category, number>>;
  visibility: ObservationVisibility;
  onToggle: (kind: ObservationKind) => void;
  vesselFilter?: FlightFilter;
  onVesselFilter?: (value: FlightFilter) => void;
  selectionDisabled?: boolean;
  flightFilter?: FlightFilter;
  onFlightFilter?: (value: FlightFilter) => void;
  onTrafficSelect?: (event: LiveEvent) => void;
}) {
  const hidden = useEventsStore((state) => state.hidden);
  const toggleCategory = useEventsStore((state) => state.toggleCategory);
  const stats = useEventsStore((state) => state.stats);
  const { terminator, toggleTerminator, interference, toggleInterference } = useGlobeStore();
  const observations = [
    { kind: 'aircraft', label: 'Flights' },
    { kind: 'vessels', label: 'Boats' },
    { kind: 'firms', label: 'FIRMS' },
  ] as const;
  return (
    <>
      {observations.map(({ kind, label }) => {
        const button = (
          <LayerButton
            key={kind}
            label={label}
            icon={kind}
            count={
              events.filter(
                (event) =>
                  observationKind(event) === kind &&
                  matchesFlightFilter(event, flightFilter) &&
                  matchesVesselFilter(event, vesselFilter),
              ).length
            }
            active={isObservationShown(kind, visibility, hidden)}
            onClick={() =>
              toggleObservationLayer(kind, visibility, hidden, onToggle, toggleCategory)
            }
          />
        );
        return kind === 'aircraft' && onFlightFilter ? (
          <FlightLayerControl
            key={kind}
            filter={flightFilter}
            onChange={onFlightFilter}
            count={events.filter(isMilitaryFlight).length}
            events={events.filter(
              (event) =>
                observationKind(event) === kind &&
                matchesFlightFilter(event, flightFilter) &&
                matchesVesselFilter(event, vesselFilter),
            )}
            available={stats?.per_category.find((item) => item.category === 'aviation')?.count}
            onSelect={onTrafficSelect}
            selectionDisabled={selectionDisabled}
          >
            {button}
          </FlightLayerControl>
        ) : kind === 'vessels' && onTrafficSelect ? (
          <FlightLayerControl
            key={kind}
            kind="vessels"
            filter={vesselFilter}
            onChange={onVesselFilter}
            count={events.filter(isMilitaryVessel).length}
            events={events.filter(
              (event) =>
                observationKind(event) === kind && matchesVesselFilter(event, vesselFilter),
            )}
            available={stats?.per_category.find((item) => item.category === 'maritime')?.count}
            onSelect={onTrafficSelect}
            selectionDisabled={selectionDisabled}
          >
            {button}
          </FlightLayerControl>
        ) : (
          button
        );
      })}
      {(['space', 'disaster', 'conflict', 'news'] as const).map((category) => (
        <LayerButton
          key={category}
          label={CATEGORY_STYLES[category].label}
          icon={category}
          count={counts[category] ?? 0}
          active={!hidden.includes(category)}
          onClick={() => toggleCategory(category)}
        />
      ))}
      <LayerButton
        label="Day and night"
        icon="night"
        active={terminator}
        onClick={toggleTerminator}
      />
      <LayerButton
        label="GNSS interference"
        icon="signal"
        active={interference}
        onClick={toggleInterference}
      />
    </>
  );
}
