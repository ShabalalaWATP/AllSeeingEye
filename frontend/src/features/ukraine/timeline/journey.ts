/**
 * Ordering, colour and path maths for the timeline journey. Pure functions only: no three.js
 * and no DOM, so the reading experience, the controls and the scene all agree on where a stop
 * sits and what colour its phase is, and every rule here is unit tested.
 */
import type { UkraineReference } from '@/lib/api/ukraine';

export type TimelineEvent = UkraineReference['events'][number];
export type TimelinePhase = UkraineReference['phases'][number];

export type JourneyPhase = TimelinePhase & {
  /** CSS colour for the phase, shared with the scene. */
  colour: string;
  /** Index of the phase's first and last stop in the travel order. */
  first: number;
  last: number;
};

export interface JourneyStop {
  event: TimelineEvent;
  phase: JourneyPhase;
  index: number;
  /** The date as a reader sees it, for example "27 February 2014". */
  date: string;
}

export interface Journey {
  stops: JourneyStop[];
  phases: JourneyPhase[];
}

/** Cold blue in 2014, ember for the invasion, green where Ukraine advanced, steel for attrition. */
const PHASE_COLOURS: Record<string, string> = {
  background: '#5b8dd6',
  invasion: '#ff5a3c',
  'donbas-2022': '#f28c28',
  'counteroffensives-2022': '#4cc38a',
  bakhmut: '#8fa6c4',
  'counteroffensive-2023': '#f5c43f',
  'avdiivka-2024': '#c8603a',
  kursk: '#22d3ee',
  '2025': '#a07ce8',
  '2026': '#9fb4c7',
};

const FALLBACK_COLOURS = [
  '#5b8dd6',
  '#ff5a3c',
  '#f28c28',
  '#4cc38a',
  '#8fa6c4',
  '#f5c43f',
  '#c8603a',
  '#22d3ee',
  '#a07ce8',
  '#9fb4c7',
];

/** A named phase keeps its colour whatever the filter shows; anything else cycles the palette. */
export function phaseColour(id: string, order: number): string {
  const named = PHASE_COLOURS[id];
  if (named !== undefined) return named;
  const slot =
    ((order % FALLBACK_COLOURS.length) + FALLBACK_COLOURS.length) % FALLBACK_COLOURS.length;
  return FALLBACK_COLOURS[slot] ?? '#9fb4c7';
}

const dateFormatter = new Intl.DateTimeFormat('en-GB', {
  day: 'numeric',
  month: 'long',
  year: 'numeric',
  timeZone: 'UTC',
});

/** "2014-02-27" becomes "27 February 2014"; an unparseable date is shown as it was given. */
export function formatEventDate(iso: string): string {
  const parsed = new Date(`${iso}T00:00:00Z`);
  if (Number.isNaN(parsed.getTime())) return iso;
  return dateFormatter.format(parsed);
}

/**
 * Sorts the events into travel order and groups them under the phase each belongs to.
 * A theme narrows the journey; phases left with no stop drop out of the selector.
 */
export function buildJourney(reference: UkraineReference, theme: string | null = null): Journey {
  const known = new Map(reference.phases.map((phase, order) => [phase.id, { phase, order }]));
  const events = reference.events
    .filter((event) => theme === null || event.theme === theme)
    .slice()
    .sort((left, right) => left.on.localeCompare(right.on) || left.id.localeCompare(right.id));
  const phases: JourneyPhase[] = [];
  const byId = new Map<string, JourneyPhase>();
  const stops: JourneyStop[] = [];
  for (const event of events) {
    const index = stops.length;
    let phase = byId.get(event.phase_id);
    if (phase === undefined) {
      const match = known.get(event.phase_id);
      const source: TimelinePhase = match?.phase ?? {
        id: event.phase_id,
        label: 'Unplaced events',
        start: event.on,
        end: null,
        summary: 'These events name a phase that the reference notes do not describe.',
      };
      phase = {
        ...source,
        colour: phaseColour(source.id, match?.order ?? known.size + phases.length),
        first: index,
        last: index,
      };
      byId.set(event.phase_id, phase);
      phases.push(phase);
    }
    phase.last = index;
    stops.push({ event, phase, index, date: formatEventDate(event.on) });
  }
  return { stops, phases };
}

/** World units between two stops, and the straight run before the first and after the last. */
export const STOP_SPACING = 13;
export const PATH_MARGIN = 11;

export function pathLength(count: number): number {
  return PATH_MARGIN * 2 + Math.max(count - 1, 0) * STOP_SPACING;
}

export function clamp01(value: number): number {
  if (Number.isNaN(value)) return 0;
  return Math.min(1, Math.max(0, value));
}

/** Travel fraction of a stop, so the camera, the ribbon and the markers land together. */
export function stopProgress(index: number, count: number): number {
  if (count <= 1) return 0.5;
  return (PATH_MARGIN + clampIndex(index, count) * STOP_SPACING) / pathLength(count);
}

export function clampIndex(value: number, count: number): number {
  if (count <= 0) return 0;
  return Math.min(count - 1, Math.max(0, Math.round(value)));
}

/**
 * The centreline of the corridor at travel fraction t. A slow lateral sway and a gentle rise
 * keep the road from reading as a straight tunnel; both are deterministic so tests can assert them.
 */
export function pathPoint(t: number, length: number): [number, number, number] {
  const travelled = clamp01(t);
  return [
    Math.sin(travelled * Math.PI * 2.6) * 7.4,
    Math.sin(travelled * Math.PI * 1.7) * 1.7,
    -travelled * length,
  ];
}

/** Frame-rate independent easing towards a target; rate is the fraction closed per second. */
export function approach(current: number, target: number, delta: number, rate = 3.2): number {
  if (delta <= 0) return current;
  const eased = current + (target - current) * (1 - Math.exp(-rate * Math.min(delta, 0.25)));
  return Math.abs(target - eased) < 0.0002 ? target : eased;
}

/** Wheel and swipe travel: distance in pixels that counts as one step to the next event. */
export const TRAVEL_THRESHOLD = 90;

/** Whole steps contained in the accumulated gesture, with the remainder to carry forward. */
export function travelSteps(accumulated: number): { steps: number; rest: number } {
  const steps = Math.trunc(accumulated / TRAVEL_THRESHOLD);
  return { steps, rest: accumulated - steps * TRAVEL_THRESHOLD };
}
