import { expect, it } from 'vitest';

import { liveEvent } from '@/test/fixtures';
import { eventResearchHref, researchHref } from './researchNavigation';

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
