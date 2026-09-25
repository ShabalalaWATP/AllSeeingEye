import { useMemo, useState } from 'react';

import { useReducedMotion } from '@/components/brand/useMotionPreferences';
import type { UkraineReference } from '@/lib/api/ukraine';
import { hasWebGl2 } from '@/lib/map/webgl';

import { JourneyStage } from './timeline/JourneyStage';
import { TimelineReadingList } from './timeline/TimelineReadingList';
import { buildJourney, clampIndex } from './timeline/journey';

type Fetcher = ((path: string) => Promise<Blob>) | undefined;

/** The page's ground colour, so the scene clears to the same shade as the card around it. */
function groundColour(): string {
  const value = getComputedStyle(document.documentElement).getPropertyValue('--color-ground');
  return value.trim() === '' ? '#07070b' : value.trim();
}

function PhaseSelector({
  phases,
  activePhase,
  onIndex,
}: {
  phases: ReturnType<typeof buildJourney>['phases'];
  activePhase: string | undefined;
  onIndex: (index: number) => void;
}) {
  return (
    <ol aria-label="Phases" className="flex gap-1 overflow-x-auto pb-1">
      {phases.map((phase) => (
        <li key={phase.id} className="shrink-0">
          <button
            type="button"
            aria-pressed={activePhase === phase.id}
            onClick={() => onIndex(phase.first)}
            title={phase.summary}
            className="flex min-h-11 flex-col rounded border border-line px-3 py-1 text-left text-xs text-muted aria-pressed:bg-surface-2 aria-pressed:text-text"
            style={activePhase === phase.id ? { borderColor: phase.colour } : undefined}
          >
            <span className="font-medium">{phase.label}</span>
            <span className="font-mono text-2xs">
              {phase.start.slice(0, 7)} to {phase.end ? phase.end.slice(0, 7) : 'now'}
            </span>
          </button>
        </li>
      ))}
    </ol>
  );
}

function ThemeFilter({
  themes,
  theme,
  onTheme,
}: {
  themes: UkraineReference['themes'];
  theme: string | null;
  onTheme: (theme: string | null) => void;
}) {
  const style =
    'min-h-9 rounded-full border border-line px-3 text-xs text-muted aria-pressed:border-ember aria-pressed:text-ember';
  return (
    <div role="group" aria-label="Theme" className="flex flex-wrap gap-1">
      <button
        type="button"
        aria-pressed={theme === null}
        onClick={() => onTheme(null)}
        className={style}
      >
        All themes
      </button>
      {Object.entries(themes).map(([key, label]) => (
        <button
          key={key}
          type="button"
          aria-pressed={theme === key}
          onClick={() => onTheme(theme === key ? null : key)}
          className={style}
        >
          {label}
        </button>
      ))}
    </div>
  );
}

/**
 * The war as a journey: a corridor of light the reader travels phase by phase, with the whole
 * timeline written out underneath as a list. The 3D layer is an enhancement and is left off
 * when the browser has no WebGL2 or the reader has asked for reduced motion.
 */
export function TimelineSection({
  reference,
  fetcher,
}: {
  reference: UkraineReference;
  fetcher?: Fetcher;
}) {
  const [theme, setTheme] = useState<string | null>(null);
  const [index, setIndex] = useState(0);
  const [playing, setPlaying] = useState(true);
  const reducedMotion = useReducedMotion();
  const [webgl] = useState(hasWebGl2);
  const enhanced = webgl && !reducedMotion;
  // The written list is folded away when the moving view can tell the story; without it,
  // the list is the timeline, so it opens.
  const [listOpen, setListOpen] = useState(!enhanced);
  const journey = useMemo(() => buildJourney(reference, theme), [reference, theme]);
  const [background] = useState(groundColour);

  // A narrower theme can leave the stored index past the end; the render clamps it.
  const count = journey.stops.length;
  const safeIndex = clampIndex(index, count);
  const activePhase = journey.stops[safeIndex]?.phase.id;

  return (
    <section
      id="timeline"
      aria-labelledby="ukraine-timeline-heading"
      className="flex flex-col gap-3"
    >
      <h2 id="ukraine-timeline-heading" className="text-base font-semibold">
        Timeline of the war
      </h2>
      <p className="max-w-3xl text-sm text-muted">
        Travel the war from the Maidan revolution to the present. Scroll over the stage, drag it
        sideways, use the arrow keys or the slider, or pick a phase to jump. Every event is also
        written out in full in a list you can open below, which does not need the 3D view.
      </p>
      <PhaseSelector
        phases={journey.phases}
        activePhase={activePhase}
        onIndex={(next) => setIndex(next)}
      />
      <ThemeFilter
        themes={reference.themes}
        theme={theme}
        onTheme={(next) => {
          setTheme(next);
          setIndex(0);
        }}
      />
      {count > 0 ? (
        <JourneyStage
          journey={journey}
          reference={reference}
          fetcher={fetcher}
          index={safeIndex}
          onIndex={setIndex}
          playing={playing}
          onPlaying={setPlaying}
          enhanced={enhanced}
          background={background}
        />
      ) : null}
      {enhanced ? null : (
        <p className="text-xs text-muted">
          The moving view is off{' '}
          {webgl
            ? 'because you have asked for reduced motion'
            : 'because this browser has no WebGL2'}
          . The timeline reads in full below.
        </p>
      )}
      <details
        open={listOpen}
        onToggle={(event) => setListOpen(event.currentTarget.open)}
        className="group/list rounded-card border border-line bg-surface/60"
      >
        <summary className="flex min-h-11 cursor-pointer list-none items-center justify-between gap-3 px-4 text-sm font-medium text-text select-none [&::-webkit-details-marker]:hidden">
          <span className="flex items-center gap-2">
            <span
              aria-hidden="true"
              className="text-muted transition-transform group-open/list:rotate-90 motion-reduce:transition-none"
            >
              ▸
            </span>
            Read the full timeline as a list
          </span>
          <span className="font-mono text-2xs text-muted">
            {count} {count === 1 ? 'event' : 'events'}
          </span>
        </summary>
        <div className="flex flex-col gap-3 border-t border-line p-4">
          <TimelineReadingList
            journey={journey}
            reference={reference}
            fetcher={fetcher}
            index={safeIndex}
            onIndex={setIndex}
          />
          <p className="text-xs text-muted">
            Hand-written notes with a source on each card; later events reach the page through the
            updates above, not this list.
          </p>
        </div>
      </details>
    </section>
  );
}
