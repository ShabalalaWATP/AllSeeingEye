import { describe, expect, it } from 'vitest';

import type { UkraineReference } from '@/lib/api/ukraine';
import { ukraineReference } from '@/test/fixtures.ukraineReference';

import {
  PATH_MARGIN,
  STOP_SPACING,
  TRAVEL_THRESHOLD,
  approach,
  buildJourney,
  clamp01,
  clampIndex,
  formatEventDate,
  pathLength,
  pathPoint,
  phaseColour,
  stopProgress,
  travelSteps,
} from './journey';
import * as shaders from './journeyShaders';

const event = (
  id: string,
  phase: string,
  on: string,
  theme = 'ground',
): UkraineReference['events'][number] => ({
  id,
  phase_id: phase,
  on,
  title: `Event ${id}`,
  text: `What happened at ${id}.`,
  theme,
  wikidata_id: null,
  image_id: null,
  links: [],
});

const reference: UkraineReference = {
  ...ukraineReference,
  phases: [
    { ...ukraineReference.phases[0]!, id: 'invasion' },
    { ...ukraineReference.phases[1]!, id: '2026' },
  ],
  events: [
    event('c', '2026', '2026-01-15', 'diplomacy'),
    event('a', 'invasion', '2022-02-24'),
    event('b', 'invasion', '2022-03-25', 'diplomacy'),
  ],
};

describe('buildJourney', () => {
  it('sorts events by date and groups them under their phase', () => {
    const { stops, phases } = buildJourney(reference);
    expect(stops.map((stop) => stop.event.id)).toEqual(['a', 'b', 'c']);
    expect(stops.map((stop) => stop.index)).toEqual([0, 1, 2]);
    expect(phases.map((phase) => phase.id)).toEqual(['invasion', '2026']);
    expect(phases[0]).toMatchObject({ first: 0, last: 1, colour: '#ff5a3c' });
    expect(phases[1]).toMatchObject({ first: 2, last: 2 });
    expect(stops[0]?.date).toBe('24 February 2022');
  });

  it('breaks ties on identical dates by id so the order never wobbles', () => {
    const same = {
      ...reference,
      events: [event('z', 'invasion', '2022-02-24'), reference.events[1]!],
    };
    expect(buildJourney(same).stops.map((stop) => stop.event.id)).toEqual(['a', 'z']);
  });

  it('narrows to one theme and drops the phases left empty', () => {
    const { stops, phases } = buildJourney(reference, 'diplomacy');
    expect(stops.map((stop) => stop.event.id)).toEqual(['b', 'c']);
    expect(phases.map((phase) => phase.first)).toEqual([0, 1]);
    expect(buildJourney(reference, 'naval').stops).toHaveLength(0);
  });

  it('keeps events whose phase the notes do not describe', () => {
    const orphan = { ...reference, events: [event('x', 'missing', '2023-01-01')] };
    const { phases, stops } = buildJourney(orphan);
    expect(phases[0]?.label).toBe('Unplaced events');
    expect(stops[0]?.phase.colour).toMatch(/^#[0-9a-f]{6}$/);
  });
});

describe('phase colours and dates', () => {
  it('gives the named phases their own colour and cycles the palette for others', () => {
    expect(phaseColour('kursk', 0)).toBe('#22d3ee');
    expect(phaseColour('unknown-phase', 0)).toBe(phaseColour('another-phase', 10));
    expect(phaseColour('unknown-phase', -1)).toMatch(/^#[0-9a-f]{6}$/);
  });

  it('writes dates the way a reader says them and passes rubbish through', () => {
    expect(formatEventDate('2014-02-27')).toBe('27 February 2014');
    expect(formatEventDate('not a date')).toBe('not a date');
  });
});

describe('path maths', () => {
  it('spaces the stops evenly along the corridor', () => {
    expect(pathLength(1)).toBe(PATH_MARGIN * 2);
    expect(pathLength(3)).toBe(PATH_MARGIN * 2 + STOP_SPACING * 2);
    expect(stopProgress(0, 1)).toBe(0.5);
    expect(stopProgress(0, 3)).toBeCloseTo(PATH_MARGIN / pathLength(3), 6);
    expect(stopProgress(9, 3)).toBeCloseTo(stopProgress(2, 3), 6);
  });

  it('clamps indexes and fractions', () => {
    expect(clampIndex(-4, 5)).toBe(0);
    expect(clampIndex(9, 5)).toBe(4);
    expect(clampIndex(1, 0)).toBe(0);
    expect(clamp01(-2)).toBe(0);
    expect(clamp01(2)).toBe(1);
    expect(clamp01(Number.NaN)).toBe(0);
  });

  it('runs the centreline away from the viewer with a sway', () => {
    const start = pathPoint(0, 100);
    const end = pathPoint(1, 100);
    expect(start[2]).toBeCloseTo(0, 10);
    expect(end[2]).toBe(-100);
    expect(pathPoint(0.25, 100)[0]).not.toBeCloseTo(start[0], 3);
    expect(pathPoint(2, 100)[2]).toBe(-100);
  });

  it('eases towards a target and settles exactly on it', () => {
    expect(approach(0, 1, 0)).toBe(0);
    const step = approach(0, 1, 1 / 60);
    expect(step).toBeGreaterThan(0);
    expect(step).toBeLessThan(1);
    expect(approach(0.9999, 1, 1)).toBe(1);
  });

  it('turns an accumulated gesture into whole steps with a remainder', () => {
    expect(travelSteps(TRAVEL_THRESHOLD * 2 + 10)).toEqual({ steps: 2, rest: 10 });
    expect(travelSteps(-TRAVEL_THRESHOLD - 5)).toEqual({ steps: -1, rest: -5 });
    expect(travelSteps(10)).toEqual({ steps: 0, rest: 10 });
  });
});

describe('the scene shaders', () => {
  const sources = Object.entries(shaders);

  it('never redeclare the attributes and matrices three.js injects', () => {
    const injected =
      /\b(?:attribute\s+(?:vec3\s+position|vec3\s+normal|vec2\s+uv|mat4\s+instanceMatrix)|uniform\s+mat4\s+(?:projectionMatrix|modelViewMatrix|modelMatrix|viewMatrix))\b/;
    expect(sources).toHaveLength(8);
    for (const [name, source] of sources) {
      expect(`${name}: ${injected.test(source)}`).toBe(`${name}: false`);
      expect(source).toContain('void main()');
    }
  });

  it('name every custom uniform and attribute so nothing collides with three.js', () => {
    for (const [name, source] of sources) {
      for (const [, kind, symbol] of source.matchAll(/(uniform|attribute)\s+\w+\s+(\w+)/g)) {
        expect(`${name}: ${kind} ${symbol}`).toMatch(/: uniform u|: attribute a/);
      }
    }
  });
});
