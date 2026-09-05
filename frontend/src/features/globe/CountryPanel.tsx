import type { LiveEvent } from '@/lib/api/eventSchemas';
import type { Country } from '@/lib/api/geoSchemas';
import { countByCategory } from '@/stores/events';

import { CATEGORY_STYLES, ORDERED_CATEGORIES } from './layers/registry';
import { formatAgo } from './timeAgo';

export const COUNTRY_PANEL_LIMIT = 8;

export interface CountryPanelProps {
  country: Country;
  /** Events already scoped to the nation, newest first. */
  events: readonly LiveEvent[];
  selectedId: string | null;
  now: number;
  onSelect: (event: LiveEvent) => void;
}

/** Country panel v1: what the live tier holds for one nation, by category and by recency. */
export function CountryPanel({ country, events, selectedId, now, onSelect }: CountryPanelProps) {
  const counts = countByCategory(events);
  const present = ORDERED_CATEGORIES.filter((category) => (counts[category] ?? 0) > 0);
  return (
    <section
      aria-label={`${country.name} panel`}
      className="rounded-md border border-line bg-surface/90 p-2 backdrop-blur"
    >
      <div className="flex items-baseline justify-between px-1">
        <h2 className="text-sm font-semibold text-text">{country.name}</h2>
        <span className="font-mono text-[11px] text-muted">
          {country.iso2} · {events.length} live
        </span>
      </div>
      {present.length > 0 ? (
        <ul className="mt-1 flex flex-wrap gap-1 px-1">
          {present.map((category) => (
            <li
              key={category}
              className="inline-flex items-center gap-1 rounded bg-surface-2 px-1.5 py-0.5 font-mono text-[11px] text-muted"
            >
              <span
                aria-hidden="true"
                className="h-2 w-2 rounded-full"
                style={{ backgroundColor: CATEGORY_STYLES[category].css }}
              />
              {CATEGORY_STYLES[category].label} {counts[category]}
            </li>
          ))}
        </ul>
      ) : (
        <p className="mt-1 px-1 text-xs text-muted">Nothing in the live tier for this nation.</p>
      )}
      {events.length > 0 && (
        <ol className="mt-2 space-y-0.5">
          {events.slice(0, COUNTRY_PANEL_LIMIT).map((event) => (
            <li key={event.id}>
              <button
                type="button"
                aria-pressed={event.id === selectedId}
                onClick={() => {
                  onSelect(event);
                }}
                className={`flex w-full items-start gap-2 rounded px-1.5 py-1 text-left text-xs hover:bg-surface-2 ${
                  event.id === selectedId ? 'bg-surface-2' : ''
                }`}
              >
                <span
                  aria-hidden="true"
                  className="mt-1 h-2 w-2 shrink-0 rounded-full"
                  style={{ backgroundColor: CATEGORY_STYLES[event.category].css }}
                />
                <span className="line-clamp-2 flex-1 text-text">{event.title}</span>{' '}
                <span className="shrink-0 font-mono text-[11px] text-muted">
                  {formatAgo(event.published_at, now)}
                </span>
              </button>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}
