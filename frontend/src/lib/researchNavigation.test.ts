import { expect, it } from 'vitest';

import { liveEvent } from '@/test/fixtures';
import {
  eventResearchHref,
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
