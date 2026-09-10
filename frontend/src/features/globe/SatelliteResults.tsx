import type { LiveEvent } from '@/lib/api/eventSchemas';
import { useState } from 'react';
import { SATELLITE_PAGE_SIZE, satelliteIdentifiers } from './satelliteSearch';

export function SatelliteResults({
  results,
  onSelect,
  selectedId,
}: {
  results: LiveEvent[];
  onSelect?: ((event: LiveEvent) => void) | undefined;
  selectedId?: string | null | undefined;
}) {
  const [page, setPage] = useState(0);
  const pages = Math.max(1, Math.ceil(results.length / SATELLITE_PAGE_SIZE));
  const current = Math.min(page, pages - 1);
  return (
    <>
      {!results.length && (
        <p className="rounded border border-line p-3 text-xs text-muted">
          No current satellite positions match. Try another name, identifier or catalogue.
        </p>
      )}
      <ul aria-label="Matching satellites" className="max-h-80 overflow-y-auto">
        {results
          .slice(current * SATELLITE_PAGE_SIZE, (current + 1) * SATELLITE_PAGE_SIZE)
          .map((event) => (
            <li key={event.id}>
              <button
                type="button"
                disabled={!onSelect}
                aria-pressed={selectedId === event.id}
                onClick={() => onSelect?.(event)}
                className="min-h-14 w-full border-b border-line px-2 py-3 text-left text-xs hover:bg-white/5 aria-pressed:bg-cyan/10 focus-visible:outline-2 focus-visible:outline-cyan disabled:cursor-default"
              >
                <span className="block font-medium">{event.title}</span>
                <span className="mt-1 block font-mono text-[11px] text-muted">
                  {satelliteIdentifiers(event) || 'Catalogue identifier unavailable'}
                </span>
              </button>
            </li>
          ))}
      </ul>
      {pages > 1 && (
        <nav
          aria-label="Satellite result pages"
          className="flex items-center justify-between gap-2 text-xs"
        >
          <button
            type="button"
            disabled={current === 0}
            onClick={() => setPage(current - 1)}
            className="min-h-11 disabled:text-muted"
          >
            Previous satellites
          </button>
          <span className="text-muted">
            {current + 1} / {pages}
          </span>
          <button
            type="button"
            disabled={current === pages - 1}
            onClick={() => setPage(current + 1)}
            className="min-h-11 disabled:text-muted"
          >
            Next satellites
          </button>
        </nav>
      )}
    </>
  );
}
