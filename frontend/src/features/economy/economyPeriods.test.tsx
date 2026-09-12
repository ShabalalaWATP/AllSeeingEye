import { act, screen, waitFor, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { beforeEach, expect, it } from 'vitest';
import { economyNews, economySnapshot } from '@/test/fixtures.economy';
import { report } from '@/test/fixtures';
import { reportJob } from '@/test/reportJobFixture';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';

function period(days: number, completed = false) {
  return {
    job: reportJob({
      status: completed ? 'completed' : 'paused',
      report_id: completed ? report.report.id : null,
    }),
    next_refresh_at: new Date(Date.now() + 86_400_000).toISOString(),
    coverage_note: 'Available sources only; archive coverage may be incomplete.',
    window_days: days,
    period_from: new Date(Date.parse(economyNews.as_of) - days * 86_400_000).toISOString(),
    period_to: economyNews.as_of,
  };
}
beforeEach(() =>
  server.use(
    http.get('/api/economy', () => HttpResponse.json(economySnapshot)),
    http.get('/api/economy/news', ({ request }) =>
      HttpResponse.json({
        ...economyNews,
        window_hours: Number(new URL(request.url).searchParams.get('days')) * 24,
      }),
    ),
    http.post('/api/economy/briefing', ({ request }) =>
      HttpResponse.json(period(Number(new URL(request.url).searchParams.get('days')))),
    ),
  ),
);

it('applies every period to both sources and research, preserving it when changing country', async () => {
  const admissions: number[] = [];
  server.use(
    http.post('/api/economy/briefing', ({ request }) => {
      const days = Number(new URL(request.url).searchParams.get('days'));
      admissions.push(days);
      return HttpResponse.json(period(days));
    }),
  );
  const { user, router } = renderApp('/economy?region=GB', 'user');
  const picker = within(await screen.findByRole('group', { name: 'Choose summary period' }));
  for (const days of [2, 5, 7, 14]) {
    await user.click(picker.getByRole('button', { name: `${days} Day` }));
    await waitFor(() =>
      expect(screen.getByText(/Reporting period:/)).toHaveTextContent('12 Sept 2026, 12:00 UTC'),
    );
    expect(picker.getByRole('button', { name: `${days} Day`, pressed: true })).toBeVisible();
    expect(screen.getByRole('heading', { name: `${days}-day economic summary` })).toBeVisible();
    expect(
      await within(screen.getByRole('region', { name: 'Worldwide economic news' })).findByText(
        `Past ${days} days · UTC`,
      ),
    ).toBeVisible();
    expect(router.state.location.search).toContain(`days=${days}`);
  }
  await user.click(
    within(screen.getByRole('navigation', { name: 'Economy country focus' })).getByRole('button', {
      name: 'China',
    }),
  );
  expect(router.state.location.search).toContain('days=14');
  expect(router.state.location.search).toContain('region=CN');
  expect(admissions).toEqual([2, 5, 7, 14]);
  expect(screen.getByText(/Reporting period:/)).toHaveTextContent('29 Aug 2026, 12:00 UTC');
});

it('hides a completed report immediately on period change, before the next response', async () => {
  let release = () => {
    throw new Error('Response gate was not initialised');
  };
  const gate = new Promise<void>((resolve) => {
    release = resolve;
  });
  server.use(
    http.post('/api/economy/briefing', async ({ request }) => {
      const days = Number(new URL(request.url).searchParams.get('days'));
      if (days === 5) await gate;
      return HttpResponse.json(period(days, days === 2));
    }),
  );
  const { user } = renderApp('/economy', 'user');
  await screen.findByRole('article', { name: 'Economic briefing summary' });
  await user.click(screen.getByRole('button', { name: '5 Day' }));
  expect(
    screen.queryByRole('article', { name: 'Economic briefing summary' }),
  ).not.toBeInTheDocument();
  expect(screen.queryByText(/From the 2-day briefing/)).not.toBeInTheDocument();
  expect(screen.queryByText(/Reporting period:/)).not.toBeInTheDocument();
  await act(async () => {
    release();
    await gate;
  });
  expect(await screen.findByText(/Reporting period:/)).toHaveTextContent('7 Sept 2026');
});

it('ignores a late response from an abandoned period', async () => {
  let release = () => {
    throw new Error('Response gate was not initialised');
  };
  let seen = false;
  const gate = new Promise<void>((resolve) => {
    release = resolve;
  });
  server.use(
    http.post('/api/economy/briefing', async ({ request }) => {
      const days = Number(new URL(request.url).searchParams.get('days'));
      if (days === 5) {
        seen = true;
        await gate;
      }
      return HttpResponse.json(period(days, days === 5));
    }),
  );
  const { user } = renderApp('/economy?days=5', 'user');
  await waitFor(() => expect(seen).toBe(true));
  await user.click(screen.getByRole('button', { name: '14 Day' }));
  await screen.findByText(/Reporting period:/);
  await act(async () => {
    release();
    await gate;
  });
  expect(screen.getByText(/Reporting period:/)).toHaveTextContent('29 Aug 2026');
  expect(
    screen.queryByRole('article', { name: 'Economic briefing summary' }),
  ).not.toBeInTheDocument();
});

it('places an attributed overview before exactly six worldwide stories', async () => {
  server.use(
    http.get('/api/economy/news', () =>
      HttpResponse.json({
        ...economyNews,
        items: Array.from({ length: 9 }, (_, index) => ({
          ...economyNews.items[0]!,
          id: String(index),
          title: `Economic headline ${index + 1}`,
        })),
      }),
    ),
  );
  renderApp('/economy', 'user');
  const panel = within(await screen.findByRole('region', { name: 'Worldwide economic news' }));
  const overview = await panel.findByText(/The leading available reports include/);
  const stories = panel.getByRole('list');
  expect(overview.compareDocumentPosition(stories) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  expect(within(stories).getAllByRole('listitem')).toHaveLength(6);
  expect(overview).toHaveTextContent('Bank of England');
});
