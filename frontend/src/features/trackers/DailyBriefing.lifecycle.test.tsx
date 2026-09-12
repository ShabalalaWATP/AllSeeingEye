import { act, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { http, HttpResponse } from 'msw';
import { afterEach, expect, it, vi } from 'vitest';

import { report } from '@/test/fixtures';
import { apiError } from '@/test/handlers';
import { reportJob } from '@/test/reportJobFixture';
import { server } from '@/test/server';
import { DailyBriefing } from './DailyBriefing';

const response = (running = false) => ({
  job: reportJob({
    status: running ? 'running' : 'completed',
    report_id: running ? null : report.report.id,
  }),
  next_refresh_at: new Date(Date.now() + 86_400_000).toISOString(),
  coverage_note: 'Connected sources only.',
});
const show = () =>
  render(
    <MemoryRouter>
      <DailyBriefing />
    </MemoryRouter>,
  );
afterEach(() => vi.useRealTimers());

it('checks for a new briefing when its refresh boundary arrives', async () => {
  vi.useFakeTimers({ toFake: ['setTimeout', 'clearTimeout'] });
  const start = vi.fn(() => HttpResponse.json(response()));
  server.use(http.post('/api/live-monitor/briefing', start));
  show();
  await vi.waitFor(() =>
    expect(screen.getByText('Shelling was reported overnight.')).toBeInTheDocument(),
  );
  await act(() => vi.advanceTimersByTimeAsync(86_400_000));
  await vi.waitFor(() => expect(start).toHaveBeenCalledTimes(2));
});

it('defers a completed daily refresh while hidden, then admits it once visible', async () => {
  vi.useFakeTimers({ toFake: ['setTimeout', 'clearTimeout'] });
  const start = vi.fn(() => HttpResponse.json(response()));
  server.use(http.post('/api/live-monitor/briefing', start));
  show();
  await vi.waitFor(() =>
    expect(screen.getByText('Shelling was reported overnight.')).toBeInTheDocument(),
  );
  Object.defineProperty(document, 'visibilityState', { configurable: true, value: 'hidden' });
  await act(() => vi.advanceTimersByTimeAsync(86_400_000));
  expect(start).toHaveBeenCalledTimes(1);
  Object.defineProperty(document, 'visibilityState', { configurable: true, value: 'visible' });
  act(() => {
    document.dispatchEvent(new Event('visibilitychange'));
  });
  await vi.waitFor(() => expect(start).toHaveBeenCalledTimes(2));
  act(() => {
    document.dispatchEvent(new Event('visibilitychange'));
  });
  expect(start).toHaveBeenCalledTimes(2);
});

it('never admits work from an initially hidden tab and resumes when it becomes visible', async () => {
  vi.useFakeTimers({ toFake: ['setTimeout', 'clearTimeout'] });
  const start = vi.fn(() => HttpResponse.json(response()));
  server.use(http.post('/api/live-monitor/briefing', start));
  Object.defineProperty(document, 'visibilityState', { configurable: true, value: 'hidden' });
  show();
  await act(() => vi.advanceTimersByTimeAsync(60_000));
  expect(start).not.toHaveBeenCalled();
  Object.defineProperty(document, 'visibilityState', { configurable: true, value: 'visible' });
  act(() => {
    document.dispatchEvent(new Event('visibilitychange'));
  });
  await vi.waitFor(() =>
    expect(screen.getByText('Shelling was reported overnight.')).toBeInTheDocument(),
  );
  expect(start).toHaveBeenCalledTimes(1);
});

it('suspends background polling and cancels its timers on unmount', async () => {
  vi.useFakeTimers({ toFake: ['setTimeout', 'clearTimeout'] });
  const read = vi.fn(() => HttpResponse.json(response().job));
  server.use(
    http.post('/api/live-monitor/briefing', () => HttpResponse.json(response(true))),
    http.get('/api/report-jobs/:id', read),
  );
  const view = show();
  await vi.waitFor(() => expect(screen.getByText(/Preparing the latest/)).toBeInTheDocument());
  Object.defineProperty(document, 'visibilityState', { configurable: true, value: 'hidden' });
  await act(() => vi.advanceTimersByTimeAsync(10_000));
  expect(read).not.toHaveBeenCalled();
  Object.defineProperty(document, 'visibilityState', { configurable: true, value: 'visible' });
  view.unmount();
  await act(() => vi.advanceTimersByTimeAsync(10_000));
  expect(read).not.toHaveBeenCalled();
});

it('stops polling after a job read fails', async () => {
  vi.useFakeTimers({ toFake: ['setTimeout', 'clearTimeout'] });
  const read = vi.fn(() => apiError(503, 'unavailable', 'Progress unavailable.'));
  server.use(
    http.post('/api/live-monitor/briefing', () => HttpResponse.json(response(true))),
    http.get('/api/report-jobs/:id', read),
  );
  show();
  await vi.waitFor(() => expect(screen.getByText(/Preparing the latest/)).toBeInTheDocument());
  await act(() => vi.advanceTimersByTimeAsync(5_000));
  await vi.waitFor(() =>
    expect(screen.getByRole('alert')).toHaveTextContent('Progress unavailable.'),
  );
  await act(() => vi.advanceTimersByTimeAsync(30_000));
  expect(read).toHaveBeenCalledTimes(1);
});

it('rejects a mismatched report instead of showing another briefing', async () => {
  server.use(
    http.post('/api/live-monitor/briefing', () => HttpResponse.json(response())),
    http.get('/api/reports/:id', () =>
      HttpResponse.json({ ...report, report: { ...report.report, id: 'different' } }),
    ),
  );
  show();
  expect(await screen.findByRole('alert')).toHaveTextContent('different briefing');
  expect(screen.queryByText('Shelling was reported overnight.')).not.toBeInTheDocument();
});
