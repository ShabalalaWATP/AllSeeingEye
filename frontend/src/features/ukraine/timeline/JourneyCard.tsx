/**
 * The card a reader sees for one event. The same facts appear in the reading list below the
 * stage, so the overlay copy is hidden from assistive technology and its links are skipped in
 * the tab order; the list remains the one navigable source of the timeline.
 */
import type { UkraineReference } from '@/lib/api/ukraine';

import { ReferenceImage } from '../ReferenceImage';
import type { JourneyStop } from './journey';

export type Fetcher = ((path: string) => Promise<Blob>) | undefined;

export function EventLinks({
  links,
  skipTabStop = false,
}: {
  links: JourneyStop['event']['links'];
  skipTabStop?: boolean;
}) {
  if (links.length === 0) return null;
  return (
    <ul className="flex flex-wrap gap-x-3 gap-y-1">
      {links.map((link) => (
        <li key={link.url}>
          <a
            href={link.url}
            target="_blank"
            rel="noopener noreferrer"
            tabIndex={skipTabStop ? -1 : undefined}
            className="text-xs text-ember hover:underline"
          >
            {link.label}
          </a>
        </li>
      ))}
    </ul>
  );
}

export function ThemeChip({ label }: { label: string }) {
  return (
    <span className="rounded bg-surface-2 px-1.5 py-0.5 font-mono text-[10px] text-muted">
      {label}
    </span>
  );
}

/** The card floating over the scene: legible on its own panel, never typography over raw pixels. */
export function JourneyCard({
  stop,
  reference,
  fetcher,
}: {
  stop: JourneyStop;
  reference: UkraineReference;
  fetcher: Fetcher;
}) {
  const { event, phase } = stop;
  return (
    <div
      aria-hidden="true"
      className="pointer-events-none absolute inset-x-0 bottom-0 flex flex-col gap-3 p-3 sm:flex-row sm:items-end sm:p-5"
    >
      <article className="card-surface pointer-events-auto flex min-w-0 flex-col gap-2 p-4 sm:max-w-lg">
        <p
          className="font-mono text-[10px] uppercase tracking-[0.18em]"
          style={{ color: phase.colour }}
        >
          {phase.label}
        </p>
        <div className="flex flex-wrap items-baseline gap-2">
          <time dateTime={event.on} className="font-mono text-xs text-text">
            {stop.date}
          </time>
          <ThemeChip label={reference.themes[event.theme] ?? event.theme} />
        </div>
        <h3 className="text-lg leading-snug font-semibold text-text">{event.title}</h3>
        <p className="text-sm leading-relaxed text-muted">{event.text}</p>
        <EventLinks links={event.links} skipTabStop />
      </article>
      {event.image_id !== null ? (
        <ReferenceImage
          imageId={event.image_id}
          meta={reference.images[event.image_id]}
          alt=""
          fetcher={fetcher}
          className="pointer-events-auto hidden w-48 shrink-0 lg:block"
        />
      ) : null}
    </div>
  );
}
