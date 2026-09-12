import { act, screen, waitFor, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { beforeEach, expect, it, vi } from 'vitest';
import { economyNews, economySnapshot } from '@/test/fixtures.economy';
import { report } from '@/test/fixtures';
import { reportJob } from '@/test/reportJobFixture';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';

const briefing = (status: 'paused' | 'running' | 'completed' = 'paused') => ({
  job: reportJob({ status, report_id: status === 'completed' ? report.report.id : null }),
  next_refresh_at: new Date(Date.now() + 86_400_000).toISOString(),
  coverage_note: 'Official economic context and collected reporting; chart prices are separate.',
});
beforeEach(() =>
  server.use(
    http.get('/api/economy', () => HttpResponse.json(economySnapshot)),
    http.get('/api/economy/news', () => HttpResponse.json(economyNews)),
    http.post('/api/economy/briefing', () => HttpResponse.json(briefing())),
  ),
);

it('provides global headlines first, each country focus, explicit market gaps and one economic briefing', async () => {
  const { user } = renderApp('/economy', 'user');
  expect(
    await screen.findByRole('heading', { name: 'Worldwide economic news' }),
  ).toBeInTheDocument();
  expect(
    await screen.findByRole('region', { name: 'Worldwide economic indicators' }),
  ).toBeInTheDocument();
  const focus = within(screen.getByRole('navigation', { name: 'Economy country focus' }));
  expect(focus.getAllByRole('button')).toHaveLength(6);
  await user.click(focus.getByRole('button', { name: 'Iran' }));
  expect(
    await screen.findByRole('region', { name: 'Iran economic indicators' }),
  ).toBeInTheDocument();
  expect(screen.getByText('Iranian exchange feed unavailable')).toBeInTheDocument();
  const news = within(screen.getByRole('region', { name: 'Iran reporting' }));
  expect(news.getByRole('link', { name: 'Iran reports new trade figures' })).toHaveAttribute(
    'href',
    'https://www.tehrantimes.com/economy',
  );
  expect(news.queryByText(/UK economic release/)).not.toBeInTheDocument();
  expect(news.getByText('State-affiliated source')).toBeInTheDocument();
  expect(screen.getByRole('link', { name: 'Review research progress' })).toBeInTheDocument();
});

it('recovers provider errors without hiding the other independent panel', async () => {
  server.use(
    http.get('/api/economy', () =>
      HttpResponse.json(
        { error: { code: 'unavailable', message: 'Economic provider unavailable' } },
        { status: 503 },
      ),
    ),
  );
  const { user } = renderApp('/economy?region=GB', 'user');
  expect(await screen.findByText('Economic provider unavailable')).toBeVisible();
  expect(screen.getByRole('region', { name: 'United Kingdom reporting' })).toHaveTextContent(
    'UK economic release',
  );
  server.use(http.get('/api/economy', () => HttpResponse.json(economySnapshot)));
  await user.click(screen.getByRole('button', { name: 'Retry indicators' }));
  expect(
    await screen.findByRole('region', { name: 'United Kingdom economic indicators' }),
  ).toBeInTheDocument();
});

it('shows sourced daily analysis and a full exportable report link', async () => {
  server.use(http.post('/api/economy/briefing', () => HttpResponse.json(briefing('completed'))));
  renderApp('/economy', 'user');
  const analysis = within(await screen.findByRole('region', { name: 'Daily economic analysis' }));
  expect(
    await analysis.findByRole('link', { name: 'Read full briefing and export' }),
  ).toHaveAttribute('href', `/reports/${report.report.id}`);
  expect(
    analysis.getAllByRole('link', { name: /Daily briefing reference/ }).length,
  ).toBeGreaterThan(0);
  expect(analysis.getByText(/Next refresh/)).toBeInTheDocument();
});

it('shows active briefing work and explicitly retries a failed admission', async () => {
  server.use(
    http.post('/api/economy/briefing', () =>
      HttpResponse.json(
        { error: { code: 'provider_unavailable', message: 'AI connection unavailable' } },
        { status: 503 },
      ),
    ),
  );
  const { user } = renderApp('/economy', 'user');
  expect(await screen.findByText('AI connection unavailable')).toBeVisible();
  server.use(http.post('/api/economy/briefing', () => HttpResponse.json(briefing('running'))));
  await user.click(screen.getByRole('button', { name: 'Retry economic briefing' }));
  expect(
    await screen.findByText(/Collecting evidence and preparing your daily economic briefing/),
  ).toBeInTheDocument();
});

it('refreshes public panels while reusing the same daily briefing', async () => {
  const admissions = vi.fn();
  const reads = vi.fn();
  server.use(
    http.post('/api/economy/briefing', () => {
      admissions();
      return HttpResponse.json(briefing());
    }),
    http.get('/api/economy', () => {
      reads();
      return HttpResponse.json(economySnapshot);
    }),
  );
  const { user } = renderApp('/economy?region=unexpected', 'user');
  expect(
    await screen.findByRole('region', { name: 'Worldwide economic indicators' }),
  ).toBeInTheDocument();
  await user.click(screen.getByRole('button', { name: 'Refresh news & indicators' }));
  await waitFor(() => expect(reads).toHaveBeenCalledTimes(2));
  expect(admissions).toHaveBeenCalledTimes(1);
});

it('retains a usable economy page when the news feed is empty or unavailable', async () => {
  server.use(
    http.get('/api/economy/news', () =>
      HttpResponse.json(
        { error: { code: 'provider_unavailable', message: 'News unavailable' } },
        { status: 503 },
      ),
    ),
  );
  const { user } = renderApp('/economy', 'user');
  expect(await screen.findByText('News unavailable')).toBeVisible();
  server.use(http.get('/api/economy/news', () => HttpResponse.json({ ...economyNews, items: [] })));
  await user.click(screen.getByRole('button', { name: 'Retry news' }));
  expect(await screen.findByText(/No economic headlines were collected/)).toBeVisible();
  expect(screen.getByRole('heading', { name: 'Economic fundamentals' })).toBeInTheDocument();
});

it('does not refresh panels in a hidden tab and cleans up periodic work', async () => {
  vi.useFakeTimers({ toFake: ['setInterval', 'clearInterval'] });
  const reads = vi.fn();
  server.use(
    http.get('/api/economy', () => {
      reads();
      return HttpResponse.json(economySnapshot);
    }),
  );
  const { unmount } = renderApp('/economy', 'user');
  await screen.findByRole('region', { name: 'Worldwide economic indicators' });
  const visibility = vi.spyOn(document, 'visibilityState', 'get').mockReturnValue('hidden');
  await act(async () => {
    await vi.advanceTimersByTimeAsync(300_000);
  });
  expect(reads).toHaveBeenCalledTimes(1);
  visibility.mockReturnValue('visible');
  await act(() => vi.advanceTimersByTimeAsync(300_000));
  await waitFor(() => expect(reads).toHaveBeenCalledTimes(2));
  unmount();
  await act(() => vi.advanceTimersByTimeAsync(300_000));
  expect(reads).toHaveBeenCalledTimes(2);
  vi.useRealTimers();
});
