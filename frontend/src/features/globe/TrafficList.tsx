import { useDeferredValue, useMemo, useState } from 'react';
import type { LiveEvent } from '@/lib/api/eventSchemas';
import { militaryTrafficLabel, trafficSearchText } from '@/lib/traffic';
import { formatAgo } from '@/lib/format';
import { useNow } from '@/lib/hooks/useNow';

export const TRAFFIC_PAGE_SIZE = 25;

export function TrafficList({
  events,
  kind,
  available,
  onSelect,
  selectionDisabled = false,
}: {
  events: readonly LiveEvent[];
  kind: 'aircraft' | 'vessels';
  available?: number | undefined;
  onSelect: (event: LiveEvent) => void;
  selectionDisabled?: boolean;
}) {
  const [query, setQuery] = useState('');
  const [page, setPage] = useState(0);
  const deferredQuery = useDeferredValue(query.trim().toLowerCase());
  const now = useNow();
  const indexed = useMemo(
    () => events.map((event) => ({ event, search: trafficSearchText(event) })),
    [events],
  );
  const results = useMemo(
    () =>
      indexed
        .filter(({ search }) => !deferredQuery || search.includes(deferredQuery))
        .map(({ event }) => event),
    [indexed, deferredQuery],
  );
  const pages = Math.max(1, Math.ceil(results.length / TRAFFIC_PAGE_SIZE));
  const currentPage = Math.min(page, pages - 1);
  const shown = results.slice(
    currentPage * TRAFFIC_PAGE_SIZE,
    (currentPage + 1) * TRAFFIC_PAGE_SIZE,
  );
  const noun = kind === 'aircraft' ? 'aircraft' : 'vessels';
  return (
    <section aria-label={`Loaded ${noun}`} className="space-y-2 border-t border-line pt-3">
      <label className="block text-xs text-muted">
        Search {noun}
        <input
          type="search"
          value={query}
          onChange={(event) => {
            setQuery(event.target.value);
            setPage(0);
          }}
          placeholder={kind === 'aircraft' ? 'Callsign, registration or ICAO' : 'Name, MMSI or IMO'}
          maxLength={100}
          className="mt-1 w-full rounded-md border border-line bg-ground px-3 py-2 text-sm text-text outline-none focus:border-cyan"
        />
      </label>
      <p className="font-mono text-[10px] text-muted">
        {events.length.toLocaleString()} loaded in this scope
        {available === undefined
          ? ''
          : ` / ${available.toLocaleString()} total category records on server`}{' '}
        · {results.length.toLocaleString()} matching
      </p>
      <p className="text-[10px] text-muted">
        The browser keeps a bounded sample. Server totals cover all scopes and may include
        non-position records; this is not worldwide coverage.
      </p>
      {selectionDisabled && (
        <p className="text-xs text-amber-300">Finish measuring to select a position.</p>
      )}
      <ul
        className="max-h-64 divide-y divide-line overflow-y-auto"
        aria-label={`${noun} search results`}
      >
        {shown.map((event) => {
          const military = militaryTrafficLabel(event);
          return (
            <li key={event.id}>
              <button
                type="button"
                disabled={selectionDisabled || event.point === null}
                onClick={() => onSelect(event)}
                className="w-full space-y-1 px-1 py-2 text-left hover:bg-white/5 disabled:opacity-50 focus-visible:outline-2 focus-visible:outline-cyan"
              >
                <span className="block truncate text-xs font-medium">
                  {event.title_en ?? event.title}
                </span>
                {military && (
                  <span
                    className={`block text-[10px] ${kind === 'aircraft' ? 'text-amber-300' : 'text-fuchsia-300'}`}
                  >
                    {military}
                  </span>
                )}
                <span className="block font-mono text-[10px] text-muted">
                  {event.source_id} · {formatAgo(event.published_at, now)}
                  {event.point === null ? ' · no position' : ''}
                </span>
              </button>
            </li>
          );
        })}
      </ul>
      {results.length === 0 && (
        <p className="py-3 text-xs text-muted">No matching {noun} loaded.</p>
      )}
      <div className="flex items-center justify-between text-xs">
        <button
          type="button"
          disabled={currentPage === 0}
          onClick={() => setPage(currentPage - 1)}
          className="min-h-9 px-2 disabled:opacity-40"
        >
          Previous
        </button>
        <span>
          {currentPage + 1} / {pages}
        </span>
        <button
          type="button"
          disabled={currentPage >= pages - 1}
          onClick={() => setPage(currentPage + 1)}
          className="min-h-9 px-2 disabled:opacity-40"
        >
          Next
        </button>
      </div>
    </section>
  );
}
