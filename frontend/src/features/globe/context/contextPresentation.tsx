import type { ReactNode } from 'react';
import type { LiveEvent } from '@/lib/api/eventSchemas';
import { isHttpUrl } from '@/lib/urls';
import type { useContextEvents } from './useContextEvents';

export interface ContextPanelProps {
  country?: string | null;
  onSelect?: (event: LiveEvent) => void;
}

export const controlClass =
  'min-h-9 w-full rounded-lg border border-line bg-panel px-2 text-xs text-text';
export const actionClass =
  'inline-flex min-h-9 items-center text-xs text-cyan underline underline-offset-2';

/** Provider timestamps without an offset are documented UTC, never browser-local time. */
export function utcDate(value: unknown): string {
  if (typeof value !== 'string' || !/^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}/.test(value))
    return 'Not reported';
  const iso = value.replace(' ', 'T');
  const when = new Date(/(?:Z|[+-]\d{2}:\d{2})$/.test(iso) ? iso : `${iso}Z`);
  if (!Number.isFinite(when.getTime())) return 'Not reported';
  return `${when.toISOString().slice(0, 16).replace('T', ' ')} UTC`;
}

export function attribute(event: LiveEvent, key: string): string {
  const value = event.attributes[key];
  return (typeof value === 'string' && value.trim()) || typeof value === 'number'
    ? String(value)
    : 'Not reported';
}

export function newest(events: LiveEvent[]): LiveEvent[] {
  return [...events].sort((a, b) => (b.published_at ?? '').localeCompare(a.published_at ?? ''));
}

export function matchesQuery(event: LiveEvent, query: string): boolean {
  return `${event.title} ${event.summary ?? ''} ${Object.values(event.attributes).join(' ')}`
    .toLocaleLowerCase()
    .includes(query.trim().toLocaleLowerCase());
}

export function ContextShell({
  title,
  scope,
  snapshot,
  children,
}: {
  title: string;
  scope: string;
  snapshot: ReturnType<typeof useContextEvents>;
  children: ReactNode;
}) {
  return (
    <section aria-label={title} className="space-y-3 p-3 text-xs">
      <header className="space-y-2 border-b border-line pb-3">
        <div className="flex items-center justify-between gap-2">
          <h3 className="font-medium text-text">{title}</h3>
          <button
            type="button"
            onClick={snapshot.refresh}
            disabled={snapshot.loading}
            className="min-h-9 rounded-lg border border-line px-3 text-cyan disabled:opacity-40"
          >
            Refresh
          </button>
        </div>
        <p className="leading-relaxed text-muted">{scope}</p>
        <p className="text-[10px] text-muted">
          Snapshot fetched: {utcDate(snapshot.fetchedAt)}. Refresh reads collected records, not a
          new provider scan.
        </p>
      </header>
      {snapshot.loading && (
        <p role="status" className="text-muted">
          Loading collected records…
        </p>
      )}
      {snapshot.failures > 0 && (
        <p
          role="alert"
          className="rounded-lg border border-amber-300/20 bg-amber-300/5 p-3 text-amber-200"
        >
          Some source records could not be loaded. Refresh to retry. Other available records remain
          below.
        </p>
      )}
      {children}
      <p className="border-t border-line pt-3 text-[10px] leading-relaxed text-muted">
        Limited to 100 collected records and 25 list entries. An empty list does not establish
        normal conditions or provider health.
      </p>
    </section>
  );
}

export function EventActions({
  event,
  onSelect,
  locate = false,
}: {
  event: LiveEvent;
  onSelect?: ContextPanelProps['onSelect'];
  locate?: boolean;
}) {
  return (
    <div className="flex flex-wrap items-center gap-x-4">
      {onSelect && (
        <button type="button" className={actionClass} onClick={() => onSelect(event)}>
          {locate && event.point ? 'Locate first position' : 'View details'}
        </button>
      )}
      {isHttpUrl(event.url) && (
        <a href={event.url} target="_blank" rel="noopener noreferrer" className={actionClass}>
          Open source
        </a>
      )}
    </div>
  );
}
