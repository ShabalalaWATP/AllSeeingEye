/**
 * The stage: the WebGL corridor where the browser allows it, a static phase gradient where it
 * does not, with the active event's card legible on its own panel over the top. The reading
 * list underneath carries the same events for assistive technology and for everyone else.
 */
import { useRef } from 'react';

import type { UkraineReference } from '@/lib/api/ukraine';

import { JourneyCanvas } from './JourneyCanvas';
import { JourneyCard, type Fetcher } from './JourneyCard';
import { JourneyControls } from './JourneyControls';
import type { Journey } from './journey';
import { useJourneyTravel } from './useJourneyTravel';

/** A quiet gradient of the phase colours, used when the 3D layer is off. */
function StaticBackdrop({ colours }: { colours: string[] }) {
  const stops = colours.length > 1 ? colours : [...colours, ...colours, '#2a2a36'];
  return (
    <div
      aria-hidden="true"
      data-testid="journey-backdrop"
      className="absolute inset-0 opacity-40"
      style={{ backgroundImage: `linear-gradient(105deg, ${stops.join(', ')})` }}
    />
  );
}

export function JourneyStage({
  journey,
  reference,
  fetcher,
  index,
  onIndex,
  playing,
  onPlaying,
  enhanced,
  background,
}: {
  journey: Journey;
  reference: UkraineReference;
  fetcher: Fetcher;
  index: number;
  onIndex: (index: number) => void;
  playing: boolean;
  onPlaying: (playing: boolean) => void;
  enhanced: boolean;
  background: string;
}) {
  const stageRef = useRef<HTMLDivElement | null>(null);
  const controlsRef = useRef<HTMLDivElement | null>(null);
  const { stops } = journey;
  const stop = stops[index];
  const colours = stops.map((item) => item.phase.colour);
  useJourneyTravel(stageRef, controlsRef, { count: stops.length, index, onIndex });

  return (
    <div ref={controlsRef} className="overflow-hidden rounded-card border border-line bg-ground">
      <div
        ref={stageRef}
        data-testid="journey-stage"
        className="relative h-[clamp(20rem,58vh,32rem)] touch-pan-y select-none"
      >
        {enhanced ? (
          <JourneyCanvas
            key={colours.join('|')}
            colours={colours}
            index={index}
            playing={playing}
            background={background}
          />
        ) : (
          <StaticBackdrop colours={colours} />
        )}
        <div
          aria-hidden="true"
          className="pointer-events-none absolute inset-0 bg-linear-to-t from-ground via-ground/55 to-transparent"
        />
        {stop ? (
          <p
            aria-hidden="true"
            className="pointer-events-none absolute top-3 right-4 font-mono text-4xl leading-none font-semibold text-text/10 sm:top-5 sm:right-6 sm:text-6xl"
          >
            {stop.event.on.slice(0, 4)}
          </p>
        ) : null}
        {stop ? <JourneyCard stop={stop} reference={reference} fetcher={fetcher} /> : null}
        <p aria-live="polite" className="sr-only">
          {stop
            ? `Event ${index + 1} of ${stops.length}. ${stop.date}. ${stop.event.title}. ${stop.phase.label}.`
            : 'No events match this theme.'}
        </p>
      </div>
      <JourneyControls
        stops={stops}
        index={index}
        onIndex={onIndex}
        playing={playing}
        onPlaying={onPlaying}
        showPlay={enhanced}
      />
    </div>
  );
}
