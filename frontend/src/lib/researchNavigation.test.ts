import { expect, it } from 'vitest';

import { liveEvent } from '@/test/fixtures';
import {
  EVENT_CONTEXT_HOURS,
  eventResearchHref,
  eventResearchPeriod,
  readResearchDraftDates,
  researchHref,
  subscriptionHref,
} from './researchNavigation';

it('encodes a bounded draft without permitting query parameter injection', () => {
  const url = new URL(
    researchHref('Question? &parent=private#fragment', ' gb '),
    'http://local.test',
  );
  expect(url.pathname).toBe('/research');
  expect(url.searchParams.get('question')).toBe('Question? &parent=private#fragment');
  expect(url.searchParams.get('country')).toBe('GB');
  expect(url.searchParams.has('parent')).toBe(false);
  expect(url.hash).toBe('');
  expect(
    new URL(researchHref('x'.repeat(2000), 'not-country'), 'http://local.test').searchParams.get(
      'question',
    ),
  ).toHaveLength(1000);
  expect(
    new URL(researchHref('Question?', 'not-country'), 'http://local.test').searchParams.has(
      'country',
    ),
  ).toBe(false);
});

it('carries a valid assistant reporting period into a reviewable research draft', () => {
  const until = new Date(Date.now() - 60_000).toISOString();
  const since = new Date(Date.now() - 48 * 3_600_000).toISOString();
  const url = new URL(researchHref('What changed?', 'GB', { since, until }), 'http://local.test');
  expect(readResearchDraftDates(url.searchParams)).toEqual({ since, until });
  url.searchParams.set('until', new Date(Date.now() + 86_400_000).toISOString());
  expect(readResearchDraftDates(url.searchParams)).toBeNull();
  expect(readResearchDraftDates(new URLSearchParams({ since }))).toBeNull();
});

it('opens a bounded subscription draft without smuggling route parameters', () => {
  const url = new URL(subscriptionHref('Monitor? &enabled=true', ' gb '), 'http://local.test');
  expect(url.pathname).toBe('/subscriptions');
  expect(url.searchParams.get('question')).toBe('Monitor? &enabled=true');
  expect(url.searchParams.get('country')).toBe('GB');
  expect(url.searchParams.has('enabled')).toBe(false);
});

it('uses the original headline as an attributed question rather than an identity conclusion', () => {
  const event = liveEvent({
    title: 'Unverified company claim',
    title_en: 'Machine-translated claim',
    country_iso: null,
  });
  const url = new URL(eventResearchHref(event), 'http://local.test');
  expect(url.searchParams.get('question')).toContain('report titled "Unverified company claim"');
  expect(url.searchParams.get('question')).toContain('supports or challenges');
  expect(url.searchParams.has('country')).toBe(false);
  expect(url.searchParams.has('research_focus')).toBe(false);
  expect(url.searchParams.has('subject')).toBe(false);
  expect(url.searchParams.get('question')).not.toContain('Machine-translated claim');
});

const HOUR = 3_600_000;
const minuteIso = (ms: number) => new Date(Math.floor(ms / 60_000) * 60_000).toISOString();

it('carries the event time as a period around it and its mapped position into the question', () => {
  const now = Date.now();
  const at = now - 10 * 24 * HOUR;
  const event = liveEvent({
    published_at: new Date(at).toISOString(),
    point: { lat: 48.51234, lon: -35.8712 },
    geo_confidence: 'city',
  });
  const url = new URL(eventResearchHref(event, now), 'http://local.test');
  const question = url.searchParams.get('question') ?? '';
  expect(question).toContain(
    `It was reported at ${new Date(at).toISOString().slice(0, 16).replace('T', ' ')} UTC`,
  );
  expect(question).toContain('mapped near latitude 48.51, longitude -35.87 (city-level position)');
  expect(question).toMatch(/established facts\.$/);
  expect(url.searchParams.get('country')).toBe('DE');
  expect(readResearchDraftDates(url.searchParams)).toEqual({
    since: minuteIso(at - EVENT_CONTEXT_HOURS * HOUR),
    until: minuteIso(at + EVENT_CONTEXT_HOURS * HOUR),
  });
  // No geometry or area parameter: the position is context for the question only.
  expect([...url.searchParams.keys()].sort()).toEqual(['country', 'question', 'since', 'until']);
});

it('never lets the period reach past now and falls back to the observed time', () => {
  const now = Date.now();
  const at = now - 2 * HOUR;
  const event = liveEvent({ published_at: null, observed_at: new Date(at).toISOString() });
  expect(eventResearchPeriod(event, now)).toEqual({
    since: minuteIso(at - EVENT_CONTEXT_HOURS * HOUR),
    until: minuteIso(now),
  });
});

it('omits unusable times and imprecise positions rather than inventing context', () => {
  const now = Date.now();
  const future = liveEvent({ published_at: new Date(now + 10 * 24 * HOUR).toISOString() });
  expect(eventResearchPeriod(future, now)).toBeNull();
  const broken = liveEvent({ published_at: 'not a date', observed_at: 'also not a date' });
  expect(eventResearchPeriod(broken, now)).toBeNull();
  const brokenUrl = new URL(eventResearchHref(broken, now), 'http://local.test');
  expect(brokenUrl.searchParams.has('since')).toBe(false);
  expect(brokenUrl.searchParams.get('question')).not.toContain('reported at');
  const bare = liveEvent({ published_at: 'not a date', observed_at: '', point: null });
  expect(
    new URL(eventResearchHref(bare, now), 'http://local.test').searchParams.get('question'),
  ).toContain('"? Check its timing');
  for (const placement of [
    { geo_confidence: 'country' as const },
    { geo_confidence: 'none' as const },
    { point: null },
    { point: { lat: 95, lon: 10 } },
  ]) {
    const question = new URL(
      eventResearchHref(liveEvent(placement), now),
      'http://local.test',
    ).searchParams.get('question');
    expect(question).not.toContain('mapped near');
  }
});

it('keeps a long title within the question limit without losing the instruction', () => {
  const event = liveEvent({ title: 'Long title '.repeat(200) });
  const question =
    new URL(eventResearchHref(event), 'http://local.test').searchParams.get('question') ?? '';
  expect(question.length).toBeLessThanOrEqual(1000);
  expect(question).toMatch(/distinguish claims from established facts\.$/);
});
