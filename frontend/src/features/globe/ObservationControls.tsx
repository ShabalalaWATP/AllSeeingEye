import { useEffect, useMemo, useState } from 'react';
import { isObservationShown, toggleObservationLayer } from './layerVisibility';
import type { Category, LiveEvent } from '@/lib/api/eventSchemas';
import { useEventsStore } from '@/stores/events';
import { matchesFlightFilter, matchesVesselFilter } from './flightFilters';
import type { FlightFilter } from './flightFilters';

export type ObservationKind = 'aircraft' | 'vessels' | 'firms';
export type ObservationVisibility = Record<ObservationKind, boolean>;
export const OBSERVATIONS = [
  { kind: 'aircraft', label: 'Aircraft positions', category: 'aviation' },
  { kind: 'vessels', label: 'Vessel positions', category: 'maritime' },
  { kind: 'firms', label: 'FIRMS thermal detections', category: 'disaster' },
] as const;

export function observationKind(event: LiveEvent): ObservationKind | null {
  if (event.category === 'aviation') return 'aircraft';
  if (event.category === 'maritime' && event.subtype === 'vessel_position') return 'vessels';
  if (
    event.category === 'disaster' &&
    event.subtype === 'thermal_detection' &&
    (event.source_id === 'firms' || event.source_id.startsWith('firms_'))
  )
    return 'firms';
  return null;
}

export function filterObservations(
  events: readonly LiveEvent[],
  visibility: ObservationVisibility,
  flightFilter: FlightFilter = 'all',
  vesselFilter: FlightFilter = 'all',
) {
  return events.filter((event) => {
    const kind = observationKind(event);
    return (
      (kind === null || visibility[kind]) &&
      matchesFlightFilter(event, flightFilter) &&
      matchesVesselFilter(event, vesselFilter)
    );
  });
}

export function useObservationFilters(events: readonly LiveEvent[]) {
  const [flightFilter, setFlightFilter] = useState<FlightFilter>('all');
  const [vesselFilter, setVesselFilter] = useState<FlightFilter>('all');
  const selectedId = useEventsStore((state) => state.selectedId);
  const select = useEventsStore((state) => state.select);
  useEffect(() => {
    const selected = events.find((event) => event.id === selectedId);
    if (
      selected &&
      (!matchesVesselFilter(selected, vesselFilter) || !matchesFlightFilter(selected, flightFilter))
    )
      select(null);
  }, [events, selectedId, select, vesselFilter, flightFilter]);
  const [visibility, setVisibility] = useState<ObservationVisibility>({
    aircraft: true,
    vessels: true,
    firms: true,
  });
  const filtered = useMemo(
    () => filterObservations(events, visibility, flightFilter, vesselFilter),
    [events, visibility, flightFilter, vesselFilter],
  );
  return {
    visibility,
    filtered,
    flightFilter,
    setFlightFilter,
    vesselFilter,
    setVesselFilter,
    toggle: (kind: ObservationKind) =>
      setVisibility((previous) => ({ ...previous, [kind]: !previous[kind] })),
  };
}

export function ObservationControls({
  events,
  visibility,
  hidden,
  onToggle,
  onToggleCategory,
}: {
  events: readonly LiveEvent[];
  visibility: ObservationVisibility;
  hidden: readonly Category[];
  onToggle: (kind: ObservationKind) => void;
  onToggleCategory: (category: Category) => void;
}) {
  const counts = { aircraft: 0, vessels: 0, firms: 0 };
  for (const event of events) {
    const kind = observationKind(event);
    if (kind !== null) counts[kind] += 1;
  }
  return (
    <section aria-label="Observation overlays" className="mt-3 border-t border-line pt-3">
      <h2 className="mb-2 font-mono text-[10px] uppercase tracking-[0.16em] text-cyan">
        Observation overlays
      </h2>
      {OBSERVATIONS.map(({ kind, label, category }) => (
        <div key={kind} className="border-t border-line py-2">
          <button
            type="button"
            role="switch"
            aria-label={label}
            aria-checked={isObservationShown(kind, visibility, hidden)}
            onClick={() =>
              toggleObservationLayer(kind, visibility, hidden, onToggle, onToggleCategory)
            }
            className="flex min-h-11 w-full items-center justify-between gap-2 text-left text-xs hover:text-cyan focus-visible:outline-2 focus-visible:outline-cyan"
          >
            <span>{label}</span>
            <span
              className={`font-mono text-[10px] ${isObservationShown(kind, visibility, hidden) ? 'text-cyan' : 'text-muted'}`}
            >
              {isObservationShown(kind, visibility, hidden) ? 'ON' : 'OFF'}
            </span>
          </button>
          <p className="font-mono text-[10px] text-muted">
            {counts[kind]} loaded in this scope
            {hidden.includes(category) ? ' · category hidden' : ''}
          </p>
        </div>
      ))}
      <p className="mt-2 text-[10px] leading-relaxed text-muted">
        Regional ADS-B, Finnish-waterway AIS and optional AISStream coverage. Global ship positions
        require an administrator to configure an AISStream key; receiver coverage still varies.
        FIRMS requires a server key. Switches control display only; zero loaded records does not
        prove no activity. Vessel symbols expire on the next cleanup after 15 minutes without a
        fresh record. A side-view boat means direction is unknown.
      </p>
      <p className="mt-2 text-[10px] leading-relaxed text-muted">
        AIS:{' '}
        <a
          className="underline"
          href="https://www.digitraffic.fi/en/marine-traffic/"
          target="_blank"
          rel="noreferrer"
        >
          Fintraffic / Digitraffic
        </a>
        {' · '}
        <a
          className="underline"
          href="https://creativecommons.org/licenses/by/4.0/"
          target="_blank"
          rel="noreferrer"
        >
          CC BY 4.0
        </a>
        {' · '}Normalised and freshness-filtered.
      </p>
      <p className="mt-2 text-[10px] leading-relaxed text-muted">
        At wide zoom, up to 250 traffic records stay outside clusters. Other records remain
        clustered or individually visible. Thermal detections do not establish their cause.
      </p>
    </section>
  );
}
