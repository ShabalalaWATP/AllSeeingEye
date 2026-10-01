import { screen, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { beforeEach, expect, it } from 'vitest';

import { economyNews, economySnapshot } from '@/test/fixtures.economy';
import { report } from '@/test/fixtures';
import { reportJob } from '@/test/reportJobFixture';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';

beforeEach(() =>
  server.use(
    http.get('/api/economy', () => HttpResponse.json(economySnapshot)),
    http.get('/api/economy/news', () => HttpResponse.json(economyNews)),
    http.post('/api/economy/briefing', () =>
      HttpResponse.json({
        job: reportJob({ status: 'paused', report_id: report.report.id }),
        next_refresh_at: new Date(Date.now() + 86_400_000).toISOString(),
        coverage_note: 'Official economic context and collected reporting.',
        window_days: 2,
        period_from: '2026-09-10T12:00:00Z',
        period_to: '2026-09-12T12:00:00Z',
      }),
    ),
  ),
);

function nameOf(element: Element): string {
  const label = element.getAttribute('aria-label');
  if (label !== null) return label;
  return (element.getAttribute('aria-labelledby') ?? '')
    .split(' ')
    .map((id) => document.getElementById(id)?.textContent ?? '')
    .join(' ')
    .trim();
}

it('gives every landmark on the economy page a unique name', async () => {
  renderApp('/economy?region=GB', 'user');
  await screen.findByRole('region', { name: 'United Kingdom in plain English' });
  const world = await screen.findByRole('region', { name: 'The world economy right now' });
  await within(world).findByRole('list', { name: 'What is driving it' });
  const landmarks = ['region', 'navigation', 'complementary', 'search', 'form'].flatMap((role) =>
    screen.queryAllByRole(role).map((element) => `${role}: ${nameOf(element)}`),
  );
  const duplicates = landmarks.filter((name, index) => landmarks.indexOf(name) !== index);
  expect(duplicates).toEqual([]);
});

it('keeps the page header inside a landmark named by the page heading', async () => {
  renderApp('/economy', 'user');
  const heading = await screen.findByRole('heading', { level: 1, name: 'Economy' });
  const page = screen.getByRole('region', { name: 'Economy' });
  expect(page).toContainElement(heading.closest('header'));
  // Focus scrolling in the page keeps controls clear of the fixed Eye launcher.
  expect(page).toHaveClass('overflow-y-auto', 'scroll-pb-28');
});
