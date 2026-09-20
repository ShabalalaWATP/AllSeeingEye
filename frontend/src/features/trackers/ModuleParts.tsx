import type { ReactNode } from 'react';
import { Link } from 'react-router';

import { Alert, LoadingNote } from '@/components/ui/Alert';
import type { LiveEvent } from '@/lib/api/eventSchemas';
import type { Tally } from '@/lib/api/modules';

import { EventRow } from '@/components/events/EventRow';
import { BackToTrackers, ShowOnGlobe } from './TrackerParts';

/** A labelled figure on a tracker board. */
export function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-card border border-line bg-surface px-3 py-2">
      <div className="font-mono text-[11px] uppercase tracking-wide text-muted">{label}</div>
      <div className="text-lg font-semibold tabular-nums">{value}</div>
    </div>
  );
}

/** Counts per key as compact chips, largest first, the worst severity tinting the chip. */
export function TallyChips({ label, rows }: { label: string; rows: readonly Tally[] }) {
  if (rows.length === 0) return <p className="text-sm text-muted">Nothing in the window.</p>;
  return (
    <ul aria-label={label} className="flex flex-wrap gap-1.5">
      {rows.map((row) => (
        <li
          key={row.key}
          className={`rounded border px-2 py-0.5 font-mono text-xs ${
            (row.max_severity ?? 0) >= 0.8
              ? 'border-critical/60 text-critical'
              : (row.max_severity ?? 0) >= 0.6
                ? 'border-amber-300/60 text-amber-300'
                : 'border-line text-text'
          }`}
        >
          {row.key} <span className="text-muted">{row.count}</span>
        </li>
      ))}
    </ul>
  );
}

export function EventList({ label, events }: { label: string; events: readonly LiveEvent[] }) {
  return (
    <section aria-label={label} className="flex flex-col gap-1">
      <h2 className="text-base font-semibold">{label}</h2>
      {events.length === 0 ? (
        <p className="text-sm text-muted">Nothing in the window.</p>
      ) : (
        <ul>
          {events.map((event) => (
            <EventRow key={event.id} event={event} />
          ))}
        </ul>
      )}
    </section>
  );
}

/** The shared frame of a module page: title, blurb, actions, then whatever the board shows. */
export function ModulePage({
  title,
  blurb,
  template,
  loading,
  error,
  children,
}: {
  title: string;
  blurb: string;
  template: string | null;
  loading: boolean;
  error: string | null;
  children: ReactNode;
}) {
  return (
    <article className="flex h-full flex-col gap-5 overflow-y-auto p-6">
      <header className="flex flex-col gap-2">
        <BackToTrackers />
        <h1 className="text-xl font-semibold">{title}</h1>
        <p className="text-sm text-muted">{blurb}</p>
        <div className="flex flex-wrap gap-2">
          <ShowOnGlobe country={null} />
          {template !== null && (
            <Link
              to={`/reports?template=${template}`}
              className="rounded-md border border-line bg-surface-2 px-3 py-2 text-sm text-text hover:bg-surface"
            >
              Generate report
            </Link>
          )}
        </div>
      </header>
      {error === null ? null : <Alert tone="error">{error}</Alert>}
      {loading ? <LoadingNote label={`Loading ${title.toLowerCase()}`} /> : null}
      {children}
    </article>
  );
}
