import { useMemo, useState } from 'react';

import type { UkraineReference } from '@/lib/api/ukraine';

import { ReferenceImage } from './ReferenceImage';

type Fetcher = ((path: string) => Promise<Blob>) | undefined;

function EventCard({
  event,
  reference,
  fetcher,
}: {
  event: UkraineReference['events'][number];
  reference: UkraineReference;
  fetcher: Fetcher;
}) {
  return (
    <li className="grid gap-3 rounded-card border border-line bg-surface p-3 md:grid-cols-[1fr_12rem]">
      <div className="flex min-w-0 flex-col gap-1">
        <div className="flex flex-wrap items-baseline gap-2">
          <time dateTime={event.on} className="font-mono text-[11px] text-muted">
            {event.on}
          </time>
          <span className="rounded bg-surface-2 px-1 font-mono text-[10px] text-muted">
            {reference.themes[event.theme] ?? event.theme}
          </span>
        </div>
        <h4 className="font-medium text-text">{event.title}</h4>
        <p className="text-sm text-muted">{event.text}</p>
        <ul className="flex flex-wrap gap-2">
          {event.links.map((link) => (
            <li key={link.url}>
              <a
                href={link.url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs text-ember hover:underline"
              >
                {link.label}
              </a>
            </li>
          ))}
        </ul>
      </div>
      {event.image_id ? (
        <ReferenceImage
          imageId={event.image_id}
          meta={reference.images[event.image_id]}
          alt=""
          fetcher={fetcher}
        />
      ) : null}
    </li>
  );
}

/** Phase ribbon over dated event cards; a theme filter narrows the cards, a phase scrolls to them. */
export function TimelineSection({
  reference,
  fetcher,
}: {
  reference: UkraineReference;
  fetcher?: Fetcher;
}) {
  const [phase, setPhase] = useState<string | null>(null);
  const [theme, setTheme] = useState<string | null>(null);
  const events = useMemo(
    () =>
      [...reference.events]
        .sort((a, b) => a.on.localeCompare(b.on))
        .filter(
          (event) =>
            (phase === null || event.phase_id === phase) &&
            (theme === null || event.theme === theme),
        ),
    [reference.events, phase, theme],
  );
  return (
    <section
      id="timeline"
      aria-labelledby="ukraine-timeline-heading"
      className="flex flex-col gap-3"
    >
      <h2 id="ukraine-timeline-heading" className="text-base font-semibold">
        Timeline of the war
      </h2>
      <ol aria-label="Phases" className="flex gap-1 overflow-x-auto pb-1">
        {reference.phases.map((item) => (
          <li key={item.id} className="shrink-0">
            <button
              type="button"
              aria-pressed={phase === item.id}
              onClick={() => setPhase(phase === item.id ? null : item.id)}
              title={item.summary}
              className="flex min-h-11 flex-col rounded border border-line px-3 py-1 text-left text-xs text-muted aria-pressed:border-cyan aria-pressed:bg-cyan/10 aria-pressed:text-cyan"
            >
              <span className="font-medium">{item.label}</span>
              <span className="font-mono text-[10px]">
                {item.start.slice(0, 7)} to {item.end ? item.end.slice(0, 7) : 'now'}
              </span>
            </button>
          </li>
        ))}
      </ol>
      {phase ? (
        <p className="text-sm text-muted">
          {reference.phases.find((item) => item.id === phase)?.summary}
        </p>
      ) : null}
      <div role="group" aria-label="Theme" className="flex flex-wrap gap-1">
        <button
          type="button"
          aria-pressed={theme === null}
          onClick={() => setTheme(null)}
          className="min-h-9 rounded-full border border-line px-3 text-xs text-muted aria-pressed:border-ember aria-pressed:text-ember"
        >
          All themes
        </button>
        {Object.entries(reference.themes).map(([key, label]) => (
          <button
            key={key}
            type="button"
            aria-pressed={theme === key}
            onClick={() => setTheme(theme === key ? null : key)}
            className="min-h-9 rounded-full border border-line px-3 text-xs text-muted aria-pressed:border-ember aria-pressed:text-ember"
          >
            {label}
          </button>
        ))}
      </div>
      {events.length === 0 ? (
        <p className="text-sm text-muted">No events match this phase and theme.</p>
      ) : (
        <ol aria-label="Timeline events" className="flex flex-col gap-2">
          {events.map((event) => (
            <EventCard key={event.id} event={event} reference={reference} fetcher={fetcher} />
          ))}
        </ol>
      )}
      <p className="text-xs text-muted">
        Hand-written notes with a source on each card; later events reach the page through the
        updates above, not this list.
      </p>
    </section>
  );
}
