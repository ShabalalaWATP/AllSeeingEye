import { Link } from 'react-router';
import type { LiveEvent } from '@/lib/api/eventSchemas';
import { CYBER_KIND_LABELS, cyberKind, type CyberKindFilter } from '@/lib/cyber';
import { useCyberFiltersStore } from '@/stores/cyberFilters';
import { useEventsStore } from '@/stores/events';
import { MapToolIntro } from '@/components/maps/MapToolIntro';
import type { useCyberCountryContext } from './useCyberCountryContext';
import { precisionLabel } from './geographicPrecision';
import { utcDate } from './context/contextPresentation';

export function CyberFilterPanel({
  cyber,
  onSelect,
  picking,
}: {
  cyber: ReturnType<typeof useCyberCountryContext>;
  onSelect: (event: LiveEvent) => void;
  picking: boolean;
}) {
  const { kind, query, countryContext, setKind, setQuery, setCountryContext } =
    useCyberFiltersStore();
  const hidden = useEventsStore((state) => state.hidden.includes('cyber'));
  const country = useEventsStore((state) => state.country);
  return (
    <section aria-label="Cyber threat intelligence filters" className="map-tool-workspace">
      <MapToolIntro
        title="Cyber threat intelligence"
        description="Filter collected cyber records on the map and globe. Claims, signals and advisories retain their source meaning."
      />
      <Link to="/cyber" className="map-tool-text-button">
        Open Cyber Threat Intelligence
      </Link>
      <label className="map-tool-field">
        Record type
        <select
          className="map-tool-input"
          value={kind}
          onChange={(event) => setKind(event.target.value as CyberKindFilter)}
        >
          <option value="all">All cyber records</option>
          {Object.entries(CYBER_KIND_LABELS).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
      </label>
      <label className="map-tool-field">
        Search cyber records
        <input
          type="search"
          className="map-tool-input"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Victim, group, CVE, source…"
        />
      </label>
      <label className="flex min-h-11 items-center gap-2 text-xs">
        <input
          type="checkbox"
          checked={countryContext}
          onChange={(event) => setCountryContext(event.target.checked)}
        />
        Show approximate country context
      </label>
      <p className="map-tool-help">
        Country context uses source-attributed victim or outage countries. Labelled reference
        markers show collected record counts at country centres, not incident coordinates, attackers
        or attack paths. Country-only records remain under Not plotted in location quality.
      </p>
      <p className="map-tool-help">
        Ransomware entries are unverified claims. Connectivity signals do not establish a
        cyberattack or a continuing outage. Advisories and KEV entries are not located incidents.
      </p>
      <p className="map-tool-help">
        {country ? `Nation: ${country}.` : 'Worldwide context.'} The shared time and
        location-quality filters also apply. Context is a separate bounded snapshot, independent of
        the visible map extent.
      </p>
      {hidden && (
        <p className="map-tool-notice">
          The Cyber layer is off. Enable its switch to load records and show eligible markers.
        </p>
      )}
      <div className="flex items-center justify-between gap-2 border-t border-line pt-2">
        <p className="text-xs text-muted">{cyber.events.length} matching collected records</p>
        <button
          type="button"
          className="map-tool-text-button"
          disabled={hidden || cyber.loading}
          onClick={cyber.refresh}
        >
          Refresh cyber records
        </button>
      </div>
      {cyber.loading && (
        <p role="status" className="map-tool-help">
          Loading cyber records…
        </p>
      )}
      {cyber.error && (
        <p role="alert" className="map-tool-notice">
          {cyber.error}
        </p>
      )}
      {!hidden && !cyber.loading && !cyber.events.length && (
        <p className="map-tool-help">No matching records in this collected snapshot.</p>
      )}
      <ul className="map-tool-list">
        {cyber.events.slice(0, 25).map((event) => (
          <li key={event.id}>
            <button
              type="button"
              disabled={picking}
              onClick={() => onSelect(event)}
              className="map-tool-list-button w-full text-left"
            >
              <span className="block text-xs font-medium">{event.title}</span>{' '}
              <span className="mt-1 block text-[10px] text-muted">
                {CYBER_KIND_LABELS[cyberKind(event)]} · {precisionLabel(event)}
              </span>
            </button>
          </li>
        ))}
      </ul>
      <p className="map-tool-help">
        Snapshot: {utcDate(cyber.fetchedAt)}. Up to 500 collected records and 25 list entries.{' '}
        {cyber.limited ? 'The snapshot reached its limit. ' : ''}Counts are not unique verified
        incidents or complete coverage.
      </p>
    </section>
  );
}
