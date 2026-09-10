import { useId, useMemo, useState } from 'react';
import { MapToolIntro } from '@/components/maps/MapToolIntro';
import type { Category, LiveEvent } from '@/lib/api/eventSchemas';
import {
  locationQuality,
  precisionLabel,
  QUALITY_LABELS,
  type LocationQuality,
  type LocationQualityFilter,
} from './geographicPrecision';
import './referenceTools.css';

const PAGE_SIZE = 20;
const QUALITIES: LocationQuality[] = ['reported', 'approximate', 'propagated', 'unplotted'];
const DESCRIPTIONS: Record<LocationQualityFilter, string> = {
  all: 'Show every location quality, including records without a plotted position.',
  reported:
    'A supplied point marked exact by its source. It has not been independently verified or audited.',
  approximate:
    'A city or administrative location. A marker is not an uncertainty boundary or an exact incident site.',
  propagated:
    'A calculated orbital position from source elements, not a directly observed current position.',
  unplotted:
    'Country-only, unknown or invalid coordinates. The record remains available without an invented point.',
};

/** Loaded records stay inspectable, including those that cannot be plotted. */
export function GeographicPrecisionPanel({
  events,
  hidden,
  filter,
  onFilterChange,
  onSelect,
}: {
  events: readonly LiveEvent[];
  hidden: readonly Category[];
  filter: LocationQualityFilter;
  onFilterChange: (filter: LocationQualityFilter) => void;
  onSelect: (event: LiveEvent) => void;
}) {
  const id = useId();
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(0);
  const visible = useMemo(
    () => events.filter((event) => !hidden.includes(event.category)),
    [events, hidden],
  );
  const counts = useMemo(() => {
    const result: Record<LocationQuality, number> = {
      reported: 0,
      approximate: 0,
      propagated: 0,
      unplotted: 0,
    };
    for (const event of visible) result[locationQuality(event)] += 1;
    return result;
  }, [visible]);
  const matches = useMemo(() => {
    const query = search.trim().toLocaleLowerCase();
    return visible.filter(
      (event) =>
        (filter === 'all' || locationQuality(event) === filter) &&
        (!query ||
          [event.title, event.title_en, event.country_iso, event.source_id, event.id].some(
            (value) => value?.toLocaleLowerCase().includes(query),
          )),
    );
  }, [visible, filter, search]);
  const pages = Math.max(1, Math.ceil(matches.length / PAGE_SIZE));
  const current = Math.min(page, pages - 1);
  return (
    <section aria-label="Location quality" className="map-tool-workspace">
      <MapToolIntro
        title="Location quality"
        description="Filter loaded records by what their position represents."
        status={`${visible.length.toLocaleString('en-GB')} loaded`}
      />
      <label htmlFor={`${id}-filter`} className="map-tool-field">
        Show on map or globe
        <select
          id={`${id}-filter`}
          value={filter}
          onChange={(event) => {
            onFilterChange(event.target.value as LocationQualityFilter);
            setPage(0);
          }}
          aria-describedby={`${id}-quality-help`}
          className="map-tool-input"
        >
          {(['all', ...QUALITIES] as const).map((quality) => (
            <option key={quality} value={quality}>
              {QUALITY_LABELS[quality]}
            </option>
          ))}
        </select>
      </label>
      <p id={`${id}-quality-help`} className="map-tool-help">
        {DESCRIPTIONS[filter]}
      </p>
      {filter === 'unplotted' && (
        <p className="map-tool-notice">
          These records have no map markers. Select a record below to inspect its source details.
        </p>
      )}
      <label htmlFor={`${id}-search`} className="map-tool-field">
        Search loaded records
        <input
          id={`${id}-search`}
          type="search"
          maxLength={200}
          value={search}
          onChange={(event) => {
            setSearch(event.target.value);
            setPage(0);
          }}
          aria-describedby={`${id}-search-help`}
          placeholder="Title, country code, source or record ID"
          className="map-tool-input"
        />
      </label>
      <p id={`${id}-search-help`} className="map-tool-help">
        Searches this list only. The location-quality selection above filters the map.
      </p>
      <p role="status" className="map-tool-help">
        {matches.length} matching loaded records · page {current + 1} of {pages}
      </p>
      {matches.length === 0 ? (
        <p className="map-tool-notice">No records match these filters.</p>
      ) : (
        <ul className="map-reference-results">
          {matches.slice(current * PAGE_SIZE, (current + 1) * PAGE_SIZE).map((event) => (
            <li key={event.id}>
              <button type="button" onClick={() => onSelect(event)}>
                <span>{event.title_en ?? event.title}</span>
                <span className="map-tool-help">
                  {event.country_iso ?? 'No country'} · {precisionLabel(event)}
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
      {pages > 1 && (
        <nav aria-label="Location quality record pages" className="map-tool-actions">
          <button
            type="button"
            disabled={current === 0}
            onClick={() => setPage(current - 1)}
            className="map-tool-secondary"
          >
            Previous
          </button>
          <span className="map-tool-help">
            {current + 1} / {pages}
          </span>
          <button
            type="button"
            disabled={current === pages - 1}
            onClick={() => setPage(current + 1)}
            className="map-tool-secondary"
          >
            Next
          </button>
        </nav>
      )}
      <details className="map-tool-disclosure">
        <summary>How locations are classified</summary>
        <dl className="map-reference-glossary map-tool-help">
          {QUALITIES.map((quality) => (
            <div key={quality}>
              <dt>{QUALITY_LABELS[quality]}</dt>
              <dd>{DESCRIPTIONS[quality]}</dd>
            </div>
          ))}
        </dl>
        <ul aria-label="Location quality counts" className="map-reference-counts map-tool-help">
          {QUALITIES.map((quality) => (
            <li key={quality}>
              {QUALITY_LABELS[quality]} ({counts[quality]})
            </li>
          ))}
        </ul>
      </details>
      <p className="map-tool-help map-reference-footnote">
        Counts cover loaded records within your other filters, not worldwide coverage. This filters
        event markers, including flights and ships. GNSS, CCTV and infrastructure keep their
        separate controls. Choose All location qualities to restore event markers.
      </p>
    </section>
  );
}
