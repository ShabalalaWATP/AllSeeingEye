import { screen, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { beforeEach, expect, it } from 'vitest';

import { economyNews, economySnapshot } from '@/test/fixtures.economy';
import type { EconomyExplainer } from '@/lib/api/economyExplainer';
import { economyExplainer, explainerState } from '@/test/fixtures.economyExplainer';
import { report } from '@/test/fixtures';
import { reportJob } from '@/test/reportJobFixture';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';

const briefing = {
  job: reportJob({ status: 'paused', report_id: report.report.id }),
  next_refresh_at: new Date(Date.now() + 86_400_000).toISOString(),
  coverage_note: 'Official economic context and collected reporting.',
  window_days: 2,
  period_from: '2026-09-10T12:00:00Z',
  period_to: '2026-09-12T12:00:00Z',
};

beforeEach(() =>
  server.use(
    http.get('/api/economy', () => HttpResponse.json(economySnapshot)),
    http.get('/api/economy/news', () => HttpResponse.json(economyNews)),
    http.post('/api/economy/briefing', () => HttpResponse.json(briefing)),
  ),
);

const useExplainer = (body: EconomyExplainer) =>
  server.use(http.get('/api/economy/explainer', () => HttpResponse.json(body)));

it('leads with a plain-English world summary, its short lists and its provenance', async () => {
  renderApp('/economy', 'user');
  const panel = within(await screen.findByRole('region', { name: 'The world economy right now' }));
  expect(
    await panel.findByText('The world economy is growing slowly while price rises keep easing.'),
  ).toBeVisible();
  expect(panel.getByText(/Output grew by 2.4% in 2024/)).toBeVisible();
  const drivers = within(panel.getByRole('region', { name: 'What is driving it' }));
  expect(drivers.getAllByRole('listitem')).toHaveLength(2);
  const watch = within(panel.getByRole('region', { name: 'What to watch' }));
  expect(watch.getByText('Whether price rises keep easing next year.')).toBeVisible();
  expect(panel.getByText(/The figures are the source of truth/)).toBeVisible();
  expect(panel.getByText(/Model plain-english-fixture/)).toBeVisible();
  expect(panel.queryByTestId('explainer-badge')).not.toBeInTheDocument();
});

it('places the country summary beside that country figures and keeps the takeaway visible', async () => {
  const { user } = renderApp('/economy?region=GB', 'user');
  const panel = within(
    await screen.findByRole('region', { name: 'United Kingdom in plain English' }),
  );
  expect(panel.getByText(/The United Kingdom took a knock and is now edging back/)).toBeVisible();
  const more = panel.getByText('Read the rest');
  expect(panel.getByText(/that part of the picture is missing/)).not.toBeVisible();
  await user.click(more);
  expect(panel.getByText(/that part of the picture is missing/)).toBeVisible();
});

it('explains each indicator through a keyboard reachable disclosure, careful note first', async () => {
  const { user } = renderApp('/economy?region=GB', 'user');
  const indicators = await screen.findByRole('region', {
    name: 'United Kingdom economic indicators',
  });
  const disclosures = within(indicators).getAllByText('What does this mean?');
  expect(disclosures.length).toBeGreaterThanOrEqual(4);
  const inflation = disclosures[2]!;
  await user.click(inflation);
  const meaning = inflation.closest('details')!;
  const careful = within(meaning).getByText(/A lower rate does not necessarily mean/);
  const plain = within(meaning).getByText(/How quickly the prices in the shops go up/);
  expect(careful).toBeVisible();
  expect(plain).toBeVisible();
  // The project's careful note is always read before the model's everyday wording.
  expect(careful.compareDocumentPosition(plain) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  expect(within(meaning).getByText(/Written by the model from these figures/)).toBeVisible();
});

it('says nothing has been written yet without hiding the figures', async () => {
  useExplainer(explainerState('empty', 'No plain-English summary has been written yet.'));
  renderApp('/economy?region=GB', 'user');
  const panel = within(await screen.findByRole('region', { name: 'The world economy right now' }));
  expect(panel.getByRole('status')).toHaveTextContent(
    'No plain-English summary has been written yet.',
  );
  expect(
    await screen.findByText(/No plain-English summary for United Kingdom is available yet/),
  ).toBeVisible();
  expect(
    await screen.findByRole('region', { name: 'United Kingdom economic indicators' }),
  ).toBeInTheDocument();
});

it('shows an updating state while a fresh summary is being written', async () => {
  useExplainer(explainerState('generating', 'A fresh plain-English summary is being written.'));
  renderApp('/economy', 'user');
  const panel = within(await screen.findByRole('region', { name: 'The world economy right now' }));
  expect(panel.getByTestId('explainer-badge')).toHaveTextContent('Updating');
  expect(panel.getByRole('status')).toHaveTextContent('being written');
});

it('keeps a stale summary visible and says the figures have moved on', async () => {
  useExplainer(explainerState('stale', null));
  renderApp('/economy', 'user');
  const panel = within(await screen.findByRole('region', { name: 'The world economy right now' }));
  expect(panel.getByTestId('explainer-badge')).toHaveTextContent('Figures moved on');
  expect(panel.getByText(/The world economy is growing slowly/)).toBeVisible();
  expect(panel.getByText(/The figures have moved on since this was written/)).toBeVisible();
});

it('reports a spent allowance as an honest empty state, never an error page', async () => {
  useExplainer(
    explainerState(
      'unavailable',
      'The AI usage allowance is spent, so no written summary was produced. The figures on this page are unaffected.',
    ),
  );
  renderApp('/economy', 'user');
  const panel = within(await screen.findByRole('region', { name: 'The world economy right now' }));
  expect(panel.getByRole('status')).toHaveTextContent('The AI usage allowance is spent');
  expect(panel.queryByText(/The world economy is growing slowly/)).not.toBeInTheDocument();
});

it('shows figures only when a summary failed its checks', async () => {
  useExplainer(explainerState('validation_failed', 'It failed the automatic checks.'));
  renderApp('/economy?region=GB', 'user');
  expect(
    await screen.findByText(/Only the figures are shown until a summary passes the checks/),
  ).toBeVisible();
  expect(
    await screen.findByText(
      /The written summary for United Kingdom could not be checked against the figures/,
    ),
  ).toBeVisible();
  expect(
    await screen.findByRole('region', { name: 'United Kingdom economic indicators' }),
  ).toBeInTheDocument();
});

it('recovers a failed explainer request without hiding the indicators', async () => {
  server.use(
    http.get('/api/economy/explainer', () =>
      HttpResponse.json(
        { error: { code: 'unavailable', message: 'Explainer unavailable' } },
        { status: 503 },
      ),
    ),
  );
  const { user } = renderApp('/economy', 'user');
  expect(await screen.findByText('Explainer unavailable')).toBeVisible();
  expect(
    await screen.findByRole('region', { name: 'Worldwide economic indicators' }),
  ).toBeInTheDocument();
  server.use(http.get('/api/economy/explainer', () => HttpResponse.json(economyExplainer)));
  await user.click(screen.getByRole('button', { name: 'Retry summary' }));
  const panel = within(screen.getByRole('region', { name: 'The world economy right now' }));
  expect(await panel.findByText(/The world economy is growing slowly/)).toBeVisible();
});

it('offers the rewrite control to administrators only, and posts the refresh', async () => {
  renderApp('/economy', 'user');
  await screen.findByRole('region', { name: 'The world economy right now' });
  expect(screen.queryByRole('button', { name: 'Rewrite summary' })).not.toBeInTheDocument();
});

it('lets an administrator force one rewrite and shows the new text', async () => {
  useExplainer(explainerState('stale', null));
  let posted = 0;
  server.use(
    http.post('/api/economy/explainer/refresh', () => {
      posted += 1;
      return HttpResponse.json(economyExplainer);
    }),
  );
  const { user } = renderApp('/economy', 'admin');
  const button = await screen.findByRole('button', { name: 'Rewrite summary' });
  await user.click(button);
  expect(posted).toBe(1);
  const panel = within(screen.getByRole('region', { name: 'The world economy right now' }));
  expect(await panel.findByText(/The world economy is growing slowly/)).toBeVisible();
  expect(screen.queryByTestId('explainer-badge')).not.toBeInTheDocument();
});

it('reports a refused administrator rewrite without losing the visible summary', async () => {
  server.use(
    http.post('/api/economy/explainer/refresh', () =>
      HttpResponse.json(
        { error: { code: 'unavailable', message: 'The rewrite could not be started.' } },
        { status: 503 },
      ),
    ),
  );
  const { user } = renderApp('/economy', 'admin');
  await user.click(await screen.findByRole('button', { name: 'Rewrite summary' }));
  expect(await screen.findByText('The rewrite could not be started.')).toBeVisible();
  const panel = within(screen.getByRole('region', { name: 'The world economy right now' }));
  expect(panel.getByText(/The world economy is growing slowly/)).toBeVisible();
});

it('supersedes the templated headline lead once a checked summary exists', async () => {
  renderApp('/economy', 'user');
  const panel = await screen.findByRole('region', { name: 'Worldwide economic news' });
  await screen.findByText(/The world economy is growing slowly/);
  expect(panel).not.toHaveTextContent('The leading available reports include');
});

it('keeps the templated headline lead as a fallback when no summary is available', async () => {
  useExplainer(explainerState('empty', 'Nothing has been written yet.'));
  // No checked summary and no cited briefing: the attributed headline extract remains.
  server.use(
    http.post('/api/economy/briefing', () =>
      HttpResponse.json({ ...briefing, job: reportJob({ status: 'paused', report_id: null }) }),
    ),
  );
  renderApp('/economy', 'user');
  const panel = await screen.findByRole('region', { name: 'Worldwide economic news' });
  await within(panel).findByRole('list');
  expect(panel).toHaveTextContent('The leading available reports include');
});
