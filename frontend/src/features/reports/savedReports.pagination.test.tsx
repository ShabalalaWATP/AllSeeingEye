import { act, renderHook, screen, waitFor } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { expect, it, vi } from 'vitest';

import * as listing from '@/lib/api/reportListing';
import type { ReportOrigin, ReportPage } from '@/lib/api/reportListing';
import { invalidateWorkspaceAccess } from '@/lib/workspaceAccess';
import { reportSummary } from '@/test/fixtures';
import { applySession, renderApp } from '@/test/render';
import { server } from '@/test/server';
import { useSavedReports } from './useSavedReports';

const items = Array.from({ length: 51 }, (_, index) => ({
  ...reportSummary,
  id: `d73c2988-d2ca-4482-9e39-${String(index).padStart(12, '0')}`,
  title: `Report ${index + 1}`,
}));
const page = (offset: number): ReportPage => ({
  items: items.slice(offset, offset + 50),
  limit: 50,
  offset,
  has_more: offset === 0,
});

it.each([
  ['research', '/research/saved'],
  ['subscription', '/subscriptions/saved'],
  ['geolocation', '/geolocation/saved'],
] as const)('pages the server-filtered %s section', async (origin, path) => {
  const requests: string[] = [];
  server.use(
    http.get('/api/reports', ({ request }) => {
      const query = new URL(request.url).searchParams;
      expect(query.get('origin')).toBe(origin);
      expect(query.get('limit')).toBe('50');
      requests.push(query.get('offset') ?? '');
      return HttpResponse.json(page(Number(query.get('offset'))));
    }),
  );
  const { user } = renderApp(path, 'user');
  await screen.findByRole('link', { name: 'Report 1' });
  expect(screen.getByRole('button', { name: 'Previous reports' })).toBeDisabled();
  await user.click(screen.getByRole('button', { name: 'Next reports' }));
  expect(await screen.findByRole('link', { name: 'Report 51' })).toBeVisible();
  expect(screen.queryByRole('link', { name: 'Report 1' })).not.toBeInTheDocument();
  expect(screen.getByRole('button', { name: 'Next reports' })).toBeDisabled();
  await user.click(screen.getByRole('button', { name: 'Previous reports' }));
  expect(await screen.findByRole('link', { name: 'Report 1' })).toBeVisible();
  expect(requests).toEqual(['0', '50', '0']);
});

it('keeps later-page controls available after an error or a deleted last result', async () => {
  let failed = false;
  server.use(
    http.get('/api/reports', ({ request }) => {
      const offset = Number(new URL(request.url).searchParams.get('offset'));
      if (offset === 0) return HttpResponse.json(page(0));
      if (!failed) {
        failed = true;
        return HttpResponse.error();
      }
      return HttpResponse.json({ ...page(50), items: [] });
    }),
  );
  const { user } = renderApp('/research/saved', 'user');
  await screen.findByRole('link', { name: 'Report 1' });
  await user.click(screen.getByRole('button', { name: 'Next reports' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('The server could not be reached.');
  expect(screen.getByText('Page 2')).toBeVisible();
  await user.click(screen.getByRole('button', { name: 'Retry reports' }));
  expect(
    await screen.findByText('No reports on this page. Return to the previous page.'),
  ).toBeVisible();
  expect(
    screen.queryByText('No saved research yet. Ask a question to create your first report.'),
  ).not.toBeInTheDocument();
  await user.click(screen.getByRole('button', { name: 'Previous reports' }));
  expect(await screen.findByRole('link', { name: 'Report 1' })).toBeVisible();
});

it.each(['account', 'access', 'origin'] as const)(
  'discards late pages after an %s change',
  async (change) => {
    applySession('user');
    let finish!: (value: ReportPage) => void;
    const current = { ...page(50), offset: 0, items: [{ ...items[0]!, title: 'Current scope' }] };
    const fetch = vi
      .spyOn(listing, 'fetchReportPage')
      .mockResolvedValueOnce(page(0))
      .mockImplementationOnce(
        () =>
          new Promise((resolve) => {
            finish = resolve;
          }),
      )
      .mockResolvedValueOnce(current);
    const { result, rerender } = renderHook(({ origin }) => useSavedReports(origin), {
      initialProps: { origin: 'research' as ReportOrigin },
    });
    await waitFor(() => expect(result.current.canNext).toBe(true));
    act(() => result.current.next());
    await waitFor(() => expect(fetch).toHaveBeenCalledTimes(2));
    expect(result.current.data).toBeNull();
    act(() => {
      if (change === 'account') applySession('admin');
      else if (change === 'access') invalidateWorkspaceAccess();
      else rerender({ origin: 'subscription' });
    });
    await waitFor(() => expect(result.current.data?.items[0]?.title).toBe('Current scope'));
    expect(fetch.mock.calls[1]?.[2].aborted).toBe(true);
    expect(fetch.mock.calls[2]?.[1]).toBe(0);
    expect(result.current.pageNumber).toBe(1);
    await act(async () => {
      finish(page(50));
      await Promise.resolve();
    });
    expect(result.current.data?.items[0]?.title).toBe('Current scope');
  },
);
