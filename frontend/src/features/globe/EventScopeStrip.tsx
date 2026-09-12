import type { useDashboardEvents } from './useDashboardEvents';
import { QUALITY_LABELS } from './geographicPrecision';
import { DEFAULT_HAZARD_OPTIONS } from '@/lib/hazards';
import { useCyberFiltersStore } from '@/stores/cyberFilters';

/** Describes event filtering only; static catalogues have separate scopes. */
export function EventScopeStrip({ state }: { state: ReturnType<typeof useDashboardEvents> }) {
  const { country, setCountry, windowHours, setWindow, coverageBounds, quality } = state;
  const button =
    'shrink-0 rounded px-2 py-1 text-[11px] text-muted hover:bg-white/10 focus-visible:outline-2 focus-visible:outline-cyan';
  const { observations, satellites, hazards, conflicts } = state;
  const cyber = useCyberFiltersStore();
  const hazardRefined = Object.entries(DEFAULT_HAZARD_OPTIONS).some(
    ([key, value]) => hazards.options[key as keyof typeof DEFAULT_HAZARD_OPTIONS] !== value,
  );
  const conflictRefined =
    conflicts.group !== 'all' ||
    conflicts.query !== '' ||
    conflicts.source !== 'all' ||
    conflicts.precision !== 'all' ||
    conflicts.includeHistorical ||
    conflicts.includeUnreviewed;
  return (
    <section aria-label="Event scope" className="map-event-scope">
      <span className="shrink-0 px-2 text-[10px] uppercase tracking-wider text-muted">Events</span>
      <span className="shrink-0 text-[11px] text-text">
        {coverageBounds ? 'Map area' : 'Worldwide sample'}
      </span>
      {country && (
        <button
          className={button}
          onClick={() => setCountry(null)}
          title="Clear event nation filter"
        >
          Nation: {country} ×
        </button>
      )}
      {windowHours !== null ? (
        <button className={button} onClick={() => setWindow(null)} title="Clear event time filter">
          Reported: {windowHours}h ×
        </button>
      ) : (
        <span className="shrink-0 px-2 text-[11px] text-muted">Retained times</span>
      )}
      {quality.filter !== 'all' && (
        <button
          className={button}
          onClick={() => quality.setFilter('all')}
          title="Clear event location-quality filter"
        >
          {QUALITY_LABELS[quality.filter]} ×
        </button>
      )}
      {observations.flightFilter !== 'all' && (
        <button
          className={button}
          onClick={() => observations.setFlightFilter('all')}
          title="Clear military aircraft filter"
        >
          Flights: military ×
        </button>
      )}
      {observations.vesselFilter !== 'all' && (
        <button
          className={button}
          onClick={() => observations.setVesselFilter('all')}
          title="Clear military vessel filter"
        >
          Boats: military ×
        </button>
      )}
      {(['aircraft', 'vessels'] as const).map((kind) => {
        const filter = observations.trafficRefinements[kind];
        return (
          (filter.query.trim() || filter.source || filter.ground !== 'all') && (
            <button
              key={kind}
              className={button}
              title={`Reset ${kind} search, source and status filters`}
              onClick={() => {
                filter.setQuery('');
                filter.setSource('');
                filter.setGround('all');
              }}
            >
              {kind === 'aircraft' ? 'Flights' : 'Boats'}: refined ×
            </button>
          )
        );
      })}
      {satellites.group !== 'all' && (
        <button
          className={button}
          onClick={() => satellites.setGroup('all')}
          title="Clear satellite catalogue filter"
        >
          Space: {satellites.group} ×
        </button>
      )}
      {satellites.query.trim() && (
        <button
          className={button}
          onClick={() => satellites.setQuery('')}
          title="Clear satellite search"
        >
          Space search ×
        </button>
      )}
      {hazardRefined && (
        <button
          className={button}
          onClick={() => hazards.updateOptions(DEFAULT_HAZARD_OPTIONS)}
          title="Reset natural hazard filters"
        >
          Hazards: filtered ×
        </button>
      )}
      {conflictRefined && (
        <button
          className={button}
          onClick={() => {
            conflicts.setGroup('all');
            conflicts.setQuery('');
            conflicts.setSource('all');
            conflicts.setPrecision('all');
            conflicts.setIncludeHistorical(false);
            conflicts.setIncludeUnreviewed(false);
          }}
          title="Reset conflict report filters"
        >
          Conflicts: filtered{conflicts.includeUnreviewed ? ', unreviewed included' : ''} ×
        </button>
      )}
      {(cyber.kind !== 'all' || cyber.query !== '') && (
        <button
          className={button}
          onClick={() => {
            cyber.setKind('all');
            cyber.setQuery('');
          }}
          title="Reset cyber filters"
        >
          Cyber: filtered ×
        </button>
      )}
      <span className="shrink-0 px-2 font-mono text-[10px] text-cyan">
        {quality.filtered.length.toLocaleString()} matching records
      </span>
      <span className="sr-only">
        Category filters also apply. Cameras, infrastructure, GNSS and contextual bulletins use
        their own scopes. Regional conflict markers follow nation only. Counts are loaded records,
        not worldwide coverage.
      </span>
    </section>
  );
}
