import type { Category, LiveEvent } from '@/lib/api/eventSchemas';
import { CATEGORY_STYLES } from '@/lib/categories';
import { useEventsStore } from '@/stores/events';
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
import type { useFiresFilters } from './useFiresFilters';
import type { useNewsFilters } from './newsFilters';
import { fireKind } from '@/lib/hazards';

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
  caption,
}: {
  label: string;
  icon: ControlIcon;
  active: boolean;
  count?: number;
  onClick: () => void;
  caption?: string;
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
        className={`map-icon-button ${caption ? 'map-style-button' : ''}`}
        onClick={onClick}
      >
        <MapControlIcon name={icon} />
        {caption && <span className="map-style-label">{caption}</span>}
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
  openPanel,
  activePanel,
  fires,
  news,
}: {
  events: readonly LiveEvent[];
  counts: Partial<Record<Category, number>>;
  visibility: ObservationVisibility;
  onToggle: (kind: ObservationKind) => void;
  vesselFilter?: FlightFilter;
  onVesselFilter?: (value: FlightFilter) => void;
  selectionDisabled?: boolean;
  openPanel?: (label: string, button: HTMLButtonElement) => void;
  activePanel?: string | null;
  fires?: ReturnType<typeof useFiresFilters>;
  news?: ReturnType<typeof useNewsFilters>;
  flightFilter?: FlightFilter;
  onFlightFilter?: (value: FlightFilter) => void;
  onTrafficSelect?: (event: LiveEvent) => void;
}) {
  const hidden = useEventsStore((state) => state.hidden);
  const toggleCategory = useEventsStore((state) => state.toggleCategory);
  const stats = useEventsStore((state) => state.stats);
  const observations = [
    { kind: 'aircraft', label: 'Flights' },
    { kind: 'vessels', label: 'Boats' },
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
            openPanel={openPanel}
            activePanel={activePanel}
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
            openPanel={openPanel}
            activePanel={activePanel}
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
      {fires && (
        <div className="flex flex-col items-center">
          <LayerButton
            label="Fires"
            caption="Fires"
            icon="firms"
            active={fires.enabled}
            count={fires.counts.all}
            onClick={fires.toggleEnabled}
          />
          {openPanel && (
            <button
              type="button"
              aria-label="Fire filters"
              aria-expanded={activePanel === 'Fires'}
              className="flex h-6 w-11 items-center justify-center whitespace-nowrap rounded text-[10px] text-muted hover:bg-white/10 focus-visible:outline-2 focus-visible:outline-cyan"
              onClick={(event) => openPanel('Fires', event.currentTarget)}
            >
              FILTERS <span aria-hidden="true"> ›</span>
            </button>
          )}
        </div>
      )}
      {(['space', 'disaster', 'conflict', 'cyber', 'news'] as const).map((category) => (
        <div key={category} className="flex flex-col items-center">
          <LayerButton
            label={category === 'disaster' ? 'Natural hazards' : CATEGORY_STYLES[category].label}
            icon={category}
            {...(category === 'cyber'
              ? { caption: 'Cyber' }
              : category === 'news'
                ? { caption: 'News' }
                : {})}
            count={
              category === 'disaster'
                ? events.filter((event) => event.category === 'disaster' && !fireKind(event)).length
                : category === 'news' && news
                  ? news.count
                  : (counts[category] ?? 0)
            }
            active={!hidden.includes(category)}
            onClick={() => toggleCategory(category)}
          />
          {openPanel && (
            <button
              type="button"
              className="flex h-6 w-11 items-center justify-center rounded text-[10px] text-muted hover:bg-white/10 focus-visible:outline-2 focus-visible:outline-cyan"
              aria-label={
                category === 'news'
                  ? 'News briefing'
                  : category === 'space'
                    ? 'Space filters'
                    : category === 'disaster'
                      ? 'Natural hazard filters'
                      : category === 'cyber'
                        ? 'Cyber filters'
                        : 'Conflict report filters'
              }
              aria-expanded={
                activePanel ===
                (
                  {
                    space: 'Space',
                    disaster: 'Natural hazards',
                    conflict: 'Conflict reports',
                    cyber: 'Cyber threat intelligence',
                    news: 'News briefing',
                  } as const
                )[category]
              }
              onClick={(event) =>
                openPanel(
                  (
                    {
                      space: 'Space',
                      disaster: 'Natural hazards',
                      conflict: 'Conflict reports',
                      cyber: 'Cyber threat intelligence',
                      news: 'News briefing',
                    } as const
                  )[category],
                  event.currentTarget,
                )
              }
            >
              {category === 'news' ? 'BRIEF' : 'FILTERS'} <span aria-hidden="true"> ›</span>
            </button>
          )}
        </div>
      ))}
    </>
  );
}
