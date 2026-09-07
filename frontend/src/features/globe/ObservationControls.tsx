import { useMemo, useState } from 'react';
import type { Category, LiveEvent } from '@/lib/api/eventSchemas';

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
) {
  return events.filter((event) => {
    const kind = observationKind(event);
    return kind === null || visibility[kind];
  });
}

export function useObservationFilters(events: readonly LiveEvent[]) {
  const [visibility, setVisibility] = useState<ObservationVisibility>({
    aircraft: true,
    vessels: true,
    firms: true,
  });
  const filtered = useMemo(() => filterObservations(events, visibility), [events, visibility]);
  return {
    visibility,
    filtered,
    toggle: (kind: ObservationKind) =>
      setVisibility((previous) => ({ ...previous, [kind]: !previous[kind] })),
  };
}

export function ObservationControls({
  events,
  visibility,
  hidden,
  onToggle,
}: {
  events: readonly LiveEvent[];
  visibility: ObservationVisibility;
  hidden: readonly Category[];
  onToggle: (kind: ObservationKind) => void;
}) {
  const counts = { aircraft: 0, vessels: 0, firms: 0 };
  for (const event of events) {
    const kind = observationKind(event);
    if (kind !== null) counts[kind] += 1;
  }
  return (
    <section
      aria-label="Observation overlays"
      className="rounded-md border border-line bg-surface/90 p-3 backdrop-blur"
    >
      <h2 className="mb-2 font-mono text-[10px] uppercase tracking-[0.16em] text-cyan">
        Observation overlays
      </h2>
      {OBSERVATIONS.map(({ kind, label, category }) => (
        <div key={kind} className="border-t border-line py-2">
          <button
            type="button"
            role="switch"
            aria-label={label}
            aria-checked={visibility[kind]}
            onClick={() => onToggle(kind)}
            className="flex min-h-11 w-full items-center justify-between gap-2 text-left text-xs hover:text-cyan focus-visible:outline-2 focus-visible:outline-cyan"
          >
            <span>{label}</span>
            <span
              className={`font-mono text-[10px] ${visibility[kind] ? 'text-cyan' : 'text-muted'}`}
            >
              {visibility[kind] ? 'ON' : 'OFF'}
            </span>
          </button>
          <p className="font-mono text-[10px] text-muted">
            {counts[kind]} loaded in this scope
            {hidden.includes(category) ? ' · category hidden' : ''}
          </p>
        </div>
      ))}
      <p className="mt-2 text-[10px] leading-relaxed text-muted">
        Selected regional ADS-B coverage. Vessel and FIRMS connections are not configured. Switches
        control display only.
      </p>
      <p className="mt-2 text-[10px] leading-relaxed text-muted">
        At wide zoom, up to 250 traffic records stay outside clusters. Other records remain
        clustered or individually visible. Thermal detections do not establish their cause.
      </p>
    </section>
  );
}
