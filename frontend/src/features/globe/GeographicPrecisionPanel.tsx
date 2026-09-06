import { useState } from 'react';
import type { Category, LiveEvent } from '@/lib/api/eventSchemas';
import { isMappedEvent, precisionLabel } from './geographicPrecision';

const PAGE_SIZE = 20;
/** Every unplotted record remains accessible without invented coordinates. */
export function GeographicPrecisionPanel({
  events,
  hidden,
  onSelect,
}: {
  events: readonly LiveEvent[];
  hidden: readonly Category[];
  onSelect: (event: LiveEvent) => void;
}) {
  const [page, setPage] = useState(0);
  const visible = events.filter((event) => !hidden.includes(event.category));
  const unlocated = visible.filter((event) => !isMappedEvent(event));
  const approximate = visible.filter(
    (event) => isMappedEvent(event) && event.geo_confidence !== 'exact',
  ).length;
  const pages = Math.max(1, Math.ceil(unlocated.length / PAGE_SIZE));
  const current = Math.min(page, pages - 1);
  return (
    <section
      aria-label="Geographic precision"
      className="shrink-0 rounded-md border border-line bg-surface/90 p-3 text-xs"
    >
      <h2 className="font-medium">Geographic precision</h2>
      <p className="mt-2 text-muted">
        Filled markers: source-reported exact positions. Hollow rings: approximate city or
        administrative locations, not measured uncertainty areas.
      </p>
      <p className="mt-2">
        {visible.length - unlocated.length - approximate} exact · {approximate} approximate ·{' '}
        {unlocated.length} not plotted
      </p>
      <details className="mt-2">
        <summary className="cursor-pointer py-2">Not plotted ({unlocated.length})</summary>
        <p className="mb-2 text-muted">
          Country-only and unknown locations remain research evidence. Counts describe loaded
          records in the current filters.
        </p>
        {unlocated.length === 0 ? (
          <p>No unplotted records in these filters.</p>
        ) : (
          <>
            <ul className="space-y-2">
              {unlocated.slice(current * PAGE_SIZE, (current + 1) * PAGE_SIZE).map((event) => (
                <li key={event.id}>
                  <button
                    type="button"
                    className="min-h-11 w-full rounded p-1 text-left hover:bg-surface-2 focus-visible:outline-2 focus-visible:outline-ember"
                    onClick={() => onSelect(event)}
                  >
                    <span className="block">{event.title_en ?? event.title}</span>
                    <span className="mt-1 block text-muted">
                      {event.country_iso ?? 'No country'} · {precisionLabel(event)}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
            {pages > 1 && (
              <nav
                aria-label="Unplotted record pages"
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
          </>
        )}
      </details>
    </section>
  );
}
