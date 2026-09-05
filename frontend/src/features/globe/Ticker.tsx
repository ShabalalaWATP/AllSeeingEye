import type { LiveEvent } from '@/lib/api/eventSchemas';

import { formatAgo } from '@/lib/format';

import { CATEGORY_STYLES } from './layers/registry';

export const TICKER_LIMIT = 12;

export interface TickerProps {
  /** Newest first; only the first `limit` are shown. */
  events: readonly LiveEvent[];
  selectedId: string | null;
  now: number;
  onSelect: (event: LiveEvent) => void;
  limit?: number;
}

/** The strip of latest events along the top of the view. */
export function Ticker({ events, selectedId, now, onSelect, limit = TICKER_LIMIT }: TickerProps) {
  const latest = events.slice(0, limit);
  return (
    <nav
      aria-label="Latest events"
      className="absolute top-3 right-3 left-32 z-10 h-9 overflow-hidden rounded-md border border-line bg-surface/90 backdrop-blur"
    >
      {latest.length === 0 ? (
        <p className="px-3 py-2 font-mono text-[11px] uppercase tracking-wider text-muted">
          Waiting for events
        </p>
      ) : (
        <ul className="flex h-full items-stretch overflow-x-auto [scrollbar-width:none]">
          {latest.map((event) => {
            const style = CATEGORY_STYLES[event.category];
            const active = event.id === selectedId;
            return (
              <li key={event.id} className="shrink-0 border-r border-line last:border-r-0">
                <button
                  type="button"
                  aria-pressed={active}
                  title={event.title}
                  onClick={() => {
                    onSelect(event);
                  }}
                  className={`flex h-full max-w-72 items-center gap-2 px-3 text-left text-xs transition-colors hover:bg-surface-2 ${
                    active ? 'bg-surface-2' : ''
                  }`}
                >
                  <span
                    aria-hidden="true"
                    className="h-2 w-2 shrink-0 rounded-full"
                    style={{ backgroundColor: style.css }}
                  />
                  <span className="truncate text-text">{event.title}</span>{' '}
                  <span className="shrink-0 font-mono text-[11px] text-muted">
                    {formatAgo(event.published_at, now)}
                  </span>
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </nav>
  );
}
