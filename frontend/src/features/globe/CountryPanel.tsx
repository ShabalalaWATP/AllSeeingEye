import { Link } from 'react-router';

import { researchHref } from '@/lib/researchNavigation';
import type { LiveEvent } from '@/lib/api/eventSchemas';
import type { Country } from '@/lib/api/geoSchemas';
import { formatAgo } from '@/lib/format';
import { countByCategory } from '@/stores/events';

import { CATEGORY_STYLES, ORDERED_CATEGORIES } from '@/lib/categories';
import '@/components/maps/mapTool.css';

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
    <section aria-label={`${country.name} panel`} className="map-tool-workspace">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="text-sm font-semibold text-text">{country.name}</h2>
        <span className="font-mono text-[11px] text-muted">
          {country.iso2} · {events.length} loaded
        </span>
      </div>
      <Link
        to={researchHref(
          `What are the most significant recent developments in ${country.name}, what evidence supports or challenges them, and what remains uncertain?`,
          country.iso2,
        )}
        className="map-tool-secondary"
        title="Review the question before starting research"
      >
        Research this country
      </Link>
      {present.length > 0 ? (
        <ul className="grid grid-cols-2 gap-x-3 gap-y-2">
          {present.map((category) => (
            <li key={category} className="inline-flex items-center gap-2 text-xs text-muted">
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
        <p className="map-tool-help">No matching records are currently loaded for this nation.</p>
      )}
      {events.length > 0 && (
        <ol className="map-tool-list" aria-label="Recent country records">
          {events.slice(0, COUNTRY_PANEL_LIMIT).map((event) => (
            <li key={event.id}>
              <button
                type="button"
                aria-pressed={event.id === selectedId}
                onClick={() => {
                  onSelect(event);
                }}
                className="map-tool-list-button flex items-start gap-2"
              >
                <span
                  aria-hidden="true"
                  className="mt-1 h-2 w-2 shrink-0 rounded-full"
                  style={{ backgroundColor: CATEGORY_STYLES[event.category].css }}
                />
                <span className="min-w-0 flex-1 text-text">
                  {event.title_en ?? event.title}
                  <span className="mt-1 block text-[11px] text-muted">
                    {formatAgo(event.published_at, now)}
                  </span>
                </span>
              </button>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}
