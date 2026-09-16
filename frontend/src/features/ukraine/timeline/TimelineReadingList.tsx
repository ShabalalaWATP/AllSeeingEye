/**
 * The whole timeline as a semantic list of phases and events. It is always in the document,
 * whether or not the 3D layer loaded, and it is the navigable version: every event has a
 * button, tabbing through them travels the journey, and the current event is marked.
 */
import type { UkraineReference } from '@/lib/api/ukraine';

import { ReferenceImage } from '../ReferenceImage';
import { EventLinks, ThemeChip, type Fetcher } from './JourneyCard';
import type { Journey, JourneyStop } from './journey';

function EventEntry({
  stop,
  reference,
  fetcher,
  active,
  onSelect,
}: {
  stop: JourneyStop;
  reference: UkraineReference;
  fetcher: Fetcher;
  active: boolean;
  onSelect: () => void;
}) {
  const { event } = stop;
  return (
    <li
      aria-current={active ? 'true' : undefined}
      className="grid gap-3 rounded-card border border-line bg-surface p-3 aria-[current]:border-ember md:grid-cols-[1fr_11rem]"
    >
      <div className="flex min-w-0 flex-col gap-1">
        <div className="flex flex-wrap items-baseline gap-2">
          <time dateTime={event.on} className="font-mono text-[11px] text-muted">
            {stop.date}
          </time>
          <ThemeChip label={reference.themes[event.theme] ?? event.theme} />
        </div>
        <h4 className="font-medium text-text">
          <button
            type="button"
            onClick={onSelect}
            onFocus={onSelect}
            className="text-left hover:text-ember focus-visible:text-ember"
          >
            {event.title}
          </button>
        </h4>
        <p className="text-sm text-muted">{event.text}</p>
        <EventLinks links={event.links} />
      </div>
      {event.image_id !== null ? (
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

export function TimelineReadingList({
  journey,
  reference,
  fetcher,
  index,
  onIndex,
}: {
  journey: Journey;
  reference: UkraineReference;
  fetcher: Fetcher;
  index: number;
  onIndex: (index: number) => void;
}) {
  if (journey.stops.length === 0) {
    return <p className="text-sm text-muted">No events match this theme.</p>;
  }
  return (
    <ol aria-label="Phases of the war" className="flex flex-col gap-5">
      {journey.phases.map((phase) => (
        <li key={phase.id} className="flex flex-col gap-2">
          <div
            className="flex flex-col gap-1 border-l-2 pl-3"
            style={{ borderColor: phase.colour }}
          >
            <h3 className="text-sm font-semibold text-text">{phase.label}</h3>
            <p className="font-mono text-[11px] text-muted">
              {phase.start} to {phase.end ?? 'now'}
            </p>
            <p className="max-w-3xl text-sm text-muted">{phase.summary}</p>
          </div>
          <ol aria-label={`Events: ${phase.label}`} className="flex flex-col gap-2">
            {journey.stops.slice(phase.first, phase.last + 1).map((stop) => (
              <EventEntry
                key={stop.event.id}
                stop={stop}
                reference={reference}
                fetcher={fetcher}
                active={stop.index === index}
                onSelect={() => onIndex(stop.index)}
              />
            ))}
          </ol>
        </li>
      ))}
    </ol>
  );
}
