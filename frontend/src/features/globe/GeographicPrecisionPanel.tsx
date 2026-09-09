import { useId, useMemo, useState } from 'react';
import type { Category, LiveEvent } from '@/lib/api/eventSchemas';
import {
  locationQuality,
  precisionLabel,
  QUALITY_LABELS,
  type LocationQuality,
  type LocationQualityFilter,
} from './geographicPrecision';

const PAGE_SIZE = 20;
const QUALITIES: LocationQuality[] = ['reported', 'approximate', 'propagated', 'unplotted'];

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
    <section
      aria-label="Location quality"
      className="shrink-0 rounded-md border border-line bg-surface/90 p-3 text-xs"
    >
      <h2 className="font-medium">Location quality</h2>
      <p className="mt-2 text-muted">Understand what a position represents before using it.</p>
      <dl className="mt-3 space-y-2">
        <div>
          <dt className="font-medium">Source-reported exact</dt>
          <dd className="text-muted">
            A supplied point marked exact by its source. It has not been independently verified or
            audited.
          </dd>
        </div>
        <div>
          <dt className="font-medium">Approximate</dt>
          <dd className="text-muted">
            A city or administrative location. A marker is not an uncertainty boundary or an exact
            incident site.
          </dd>
        </div>
        <div>
          <dt className="font-medium">Propagated satellite</dt>
          <dd className="text-muted">
            A calculated orbital position from source elements, not a directly observed current
            position.
          </dd>
        </div>
        <div>
          <dt className="font-medium">Not plotted</dt>
          <dd className="text-muted">
            Country-only, unknown or invalid coordinates. The record remains available without an
            invented point.
          </dd>
        </div>
      </dl>
      <p className="mt-3 text-muted">
        Counts cover loaded records within your other filters, not worldwide coverage. This filters
        event markers, including flights and ships. GNSS, CCTV and infrastructure keep their
        separate controls. Choose All location qualities to restore event markers.
      </p>
      <ul aria-label="Location quality counts" className="mt-2 space-y-1">
        {QUALITIES.map((quality) => (
          <li key={quality}>
            {QUALITY_LABELS[quality]} ({counts[quality]})
          </li>
        ))}
      </ul>
      <label htmlFor={`${id}-filter`} className="mt-3 block font-medium">
        Show on map or globe
      </label>
      <select
        id={`${id}-filter`}
        value={filter}
        onChange={(event) => {
          onFilterChange(event.target.value as LocationQualityFilter);
          setPage(0);
        }}
        className="mt-1 min-h-11 w-full rounded border border-line bg-surface p-2"
      >
        {(['all', ...QUALITIES] as const).map((quality) => (
          <option key={quality} value={quality}>
            {QUALITY_LABELS[quality]}
          </option>
        ))}
      </select>
      {filter === 'unplotted' && (
        <p className="mt-2 text-muted">
          These records have no map markers. Select a record below to inspect its source details.
        </p>
      )}
      <label htmlFor={`${id}-search`} className="mt-3 block font-medium">
        Search loaded records
      </label>
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
        className="mt-1 min-h-11 w-full rounded border border-line bg-surface p-2"
      />
      <p id={`${id}-search-help`} className="mt-1 text-muted">
        Search this list by title, country code, source or record ID. This does not change the map
        filter.
      </p>
      <p role="status" className="mt-2">
        {matches.length} matching loaded records · page {current + 1} of {pages}
      </p>
      {matches.length === 0 ? (
        <p className="mt-2 text-muted">No records match these filters.</p>
      ) : (
        <ul className="mt-2 space-y-2">
          {matches.slice(current * PAGE_SIZE, (current + 1) * PAGE_SIZE).map((event) => (
            <li key={event.id}>
              <button
                type="button"
                onClick={() => onSelect(event)}
                className="min-h-11 w-full rounded p-1 text-left hover:bg-surface-2 focus-visible:outline-2 focus-visible:outline-ember"
              >
                <span className="block">{event.title_en ?? event.title}</span>
                <span className="mt-1 block text-muted">
                  {event.country_iso ?? 'No country'} · {precisionLabel(event)}
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
      {pages > 1 && (
        <nav
          aria-label="Location quality record pages"
          className="mt-2 flex items-center justify-between gap-2"
        >
          <button
            type="button"
            disabled={current === 0}
            onClick={() => setPage(current - 1)}
            className="min-h-11 disabled:opacity-40"
          >
            Previous
          </button>
          <span>
            {current + 1} / {pages}
          </span>
          <button
            type="button"
            disabled={current === pages - 1}
            onClick={() => setPage(current + 1)}
            className="min-h-11 disabled:opacity-40"
          >
            Next
          </button>
        </nav>
      )}
    </section>
  );
}
