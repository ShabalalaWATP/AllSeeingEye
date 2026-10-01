import { act, screen, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { expect, it } from 'vitest';

import type { ReportPage } from '@/lib/api/reportListing';
import { reportSummary } from '@/test/fixtures';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';

const ORIGINS = ['research', 'subscription', 'geolocation'] as const;
const items = Array.from({ length: 53 }, (_, index) => ({
  ...reportSummary,
  id: `d73c2988-d2ca-4482-9e39-${String(index).padStart(12, '0')}`,
  title: `Report ${index + 1}`,
  origin: ORIGINS[index % 3] ?? 'research',
}));

function page(offset: number, rows = items): ReportPage {
  return {
    items: rows.slice(offset, offset + 50),
    limit: 50,
    offset,
    has_more: rows.length > offset + 50,
  };
}

function serve(requests: URLSearchParams[], respond = (_query: URLSearchParams) => page(0)) {
  server.use(
    http.get('/api/reports', ({ request }) => {
      const query = new URL(request.url).searchParams;
      requests.push(query);
      return HttpResponse.json(respond(query));
    }),
  );
}

it('lists requested work from every origin with its origin, workspace and status', async () => {
  const requests: URLSearchParams[] = [];
  serve(requests);
  renderApp('/reports/saved', 'user');
  const table = await screen.findByRole('table', { name: 'Saved reports' });
  expect(requests[0]?.get('group')).toBe('requested');
  expect(requests[0]?.has('origin')).toBe(false);
  const first = within(table).getByRole('link', { name: 'Report 1' }).closest('tr')!;
  expect(within(first).getByText('Research')).toBeVisible();
  expect(within(first).getByText('Personal')).toBeVisible();
  expect(within(first).getByText('Ready')).toBeVisible();
  const second = within(table).getByRole('link', { name: 'Report 2' }).closest('tr')!;
  expect(within(second).getByText('Subscription update')).toBeVisible();
  expect(screen.getByText('Showing 50 reports, page 1.')).toBeVisible();
  expect(screen.getByLabelText('Show')).toHaveValue('requested');
});

it('filters on the server and keeps the filter and page in the address', async () => {
  const requests: URLSearchParams[] = [];
  serve(requests, (query) => page(Number(query.get('offset'))));
  const { router, user } = renderApp('/reports/saved', 'user');
  await screen.findByRole('link', { name: 'Report 1' });
  await user.click(screen.getByRole('button', { name: 'Next reports' }));
  expect(await screen.findByRole('link', { name: 'Report 51' })).toBeVisible();
  expect(router.state.location.search).toBe('?page=2');
  await user.selectOptions(screen.getByLabelText('Show'), 'subscription');
  await screen.findByRole('link', { name: 'Report 1' });
  expect(router.state.location.search).toBe('?origin=subscription');
  const last = requests.at(-1)!;
  expect([last.get('origin'), last.get('offset'), last.has('group')]).toEqual([
    'subscription',
    '0',
    false,
  ]);
  // Back returns to the earlier filter and page.
  await act(() => router.navigate(-1));
  expect(await screen.findByRole('link', { name: 'Report 51' })).toBeVisible();
  expect(screen.getByLabelText('Show')).toHaveValue('requested');
  expect(requests.at(-1)?.get('offset')).toBe('50');
});

it('opens a deep link to an older page of one origin and ignores unknown filters', async () => {
  const requests: URLSearchParams[] = [];
  serve(requests, (query) => page(Number(query.get('offset'))));
  renderApp('/reports/saved?origin=geolocation&page=2', 'user');
  await screen.findByRole('link', { name: 'Report 51' });
  expect([requests[0]?.get('origin'), requests[0]?.get('offset')]).toEqual(['geolocation', '50']);
  expect(screen.getByLabelText('Show')).toHaveValue('geolocation');
  const fallback: URLSearchParams[] = [];
  serve(fallback);
  renderApp('/reports/saved?origin=everything&page=-4', 'user');
  await screen.findAllByRole('link', { name: 'Report 1' });
  expect([fallback[0]?.get('group'), fallback[0]?.get('offset')]).toEqual(['requested', '0']);
});

it('distinguishes no reports from no matches and offers the wider filter', async () => {
  serve([], () => page(0, []));
  const first = renderApp('/reports/saved', 'user');
  expect(
    await screen.findByText('No saved reports yet. Ask a question to create your first report.'),
  ).toBeVisible();
  first.unmount();
  const requests: URLSearchParams[] = [];
  serve(requests, (query) => (query.get('origin') ? page(0, []) : page(0)));
  const { user } = renderApp('/reports/saved?origin=subscription', 'user');
  expect(await screen.findByText('No subscription updates match this filter.')).toBeVisible();
  await user.click(screen.getByRole('button', { name: 'Show all requested work' }));
  expect(await screen.findByRole('link', { name: 'Report 1' })).toBeVisible();
  expect(requests.at(-1)?.get('group')).toBe('requested');
});

it('keeps the filter when a failed page is retried', async () => {
  let failed = false;
  const requests: URLSearchParams[] = [];
  server.use(
    http.get('/api/reports', ({ request }) => {
      const query = new URL(request.url).searchParams;
      requests.push(query);
      if (!failed) {
        failed = true;
        return HttpResponse.error();
      }
      return HttpResponse.json(page(0));
    }),
  );
  const { user } = renderApp('/reports/saved?origin=research', 'user');
  expect(await screen.findByRole('alert')).toHaveTextContent('The server could not be reached.');
  await user.click(screen.getByRole('button', { name: 'Retry reports' }));
  expect(await screen.findByRole('link', { name: 'Report 1' })).toBeVisible();
  expect(requests.map((query) => query.get('origin'))).toEqual(['research', 'research']);
  expect(screen.getByLabelText('Show')).toHaveValue('research');
});

it.each(['/research/saved', '/subscriptions/saved', '/geolocation/saved'])(
  'links %s to every saved report',
  async (path) => {
    serve([]);
    renderApp(path, 'user');
    expect(await screen.findByRole('link', { name: 'All saved reports' })).toHaveAttribute(
      'href',
      '/reports/saved',
    );
  },
);
