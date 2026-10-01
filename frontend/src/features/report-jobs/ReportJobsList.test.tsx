import { act, render, screen, waitFor, within } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router';
import { http, HttpResponse } from 'msw';
import { expect, it } from 'vitest';
import type { ReportJob } from '@/lib/api/reportJobs';
import { invalidateWorkspaceAccess } from '@/lib/workspaceAccess';
import { applySession } from '@/test/render';
import { reportJob } from '@/test/reportJobFixture';
import { server } from '@/test/server';
import ReportJobsPage from './ReportJobsPage';

const id = (index: number) => `00000000-0000-4000-8000-${String(index).padStart(12, '0')}`;
const row = (index: number, changes: Partial<ReportJob> = {}) =>
  reportJob({ id: id(index), title: `Run ${index}`, status: 'completed', ...changes });

function mount(path = '/research/jobs') {
  applySession('user');
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/research/jobs" element={<ReportJobsPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

function recordQueries(pages: (url: URL) => { items: ReportJob[]; next_cursor: string | null }) {
  const urls: URL[] = [];
  server.use(
    http.get('/api/report-jobs', ({ request }) => {
      const url = new URL(request.url);
      urls.push(url);
      return HttpResponse.json(pages(url));
    }),
  );
  return urls;
}

it('pages through every matching run with server cursors and returns to the newest page', async () => {
  const urls = recordQueries((url) =>
    url.searchParams.get('cursor') === 'page-2'
      ? { items: [row(21)], next_cursor: null }
      : { items: [row(1), row(2)], next_cursor: 'page-2' },
  );
  const user = userEvent.setup();
  mount();
  await screen.findByRole('link', { name: /Run 1/ });
  const pages = screen.getByRole('navigation', { name: 'Research run pages' });
  expect(within(pages).getByRole('button', { name: 'Newer runs' })).toBeDisabled();
  await user.click(within(pages).getByRole('button', { name: 'Older runs' }));
  await screen.findByRole('link', { name: /Run 21/ });
  expect(screen.queryByRole('link', { name: /^Run 1/ })).not.toBeInTheDocument();
  expect(screen.getByText('Page 2')).toBeVisible();
  expect(within(pages).getByRole('button', { name: 'Older runs' })).toBeDisabled();
  await user.click(within(pages).getByRole('button', { name: 'Newer runs' }));
  await screen.findByRole('link', { name: /Run 1/ });
  expect(urls.map((url) => url.searchParams.get('cursor'))).toEqual([null, 'page-2', null]);
  expect(urls.every((url) => url.searchParams.get('status') === 'all')).toBe(true);
  expect(urls.every((url) => !url.searchParams.has('include_briefings'))).toBe(true);
});

it('filters on the server, distinguishes resumable work and resets the page on filter change', async () => {
  const urls = recordQueries((url) => {
    if (url.searchParams.get('status') === 'attention')
      return {
        items: [
          row(3, { status: 'paused', can_resume: true }),
          row(4, { status: 'failed', can_resume: false }),
        ],
        next_cursor: null,
      };
    return url.searchParams.get('cursor')
      ? { items: [row(9)], next_cursor: null }
      : { items: [row(1)], next_cursor: 'next' };
  });
  const user = userEvent.setup();
  mount();
  await screen.findByRole('link', { name: /Run 1/ });
  await user.click(screen.getByRole('button', { name: 'Older runs' }));
  await screen.findByRole('link', { name: /Run 9/ });
  const filters = screen.getByRole('group', { name: 'Show research runs' });
  await user.click(within(filters).getByRole('button', { name: 'Needs attention' }));
  expect(within(filters).getByRole('button', { name: 'Needs attention' })).toHaveAttribute(
    'aria-pressed',
    'true',
  );
  expect(await screen.findByRole('link', { name: /Run 3/ })).toHaveTextContent('Can resume');
  expect(screen.getByRole('link', { name: /Run 4/ })).toHaveTextContent('Cannot resume');
  expect(screen.getByText('Page 1')).toBeVisible();
  const last = urls.at(-1)!;
  expect(last.searchParams.get('status')).toBe('attention');
  expect(last.searchParams.has('cursor')).toBe(false);
});

it('reveals automatic briefings only on request and labels them', async () => {
  const urls = recordQueries((url) => ({
    items: url.searchParams.get('include_briefings')
      ? [row(1), row(2, { origin: 'briefing', title: 'Daily briefing' })]
      : [row(1)],
    next_cursor: null,
  }));
  const user = userEvent.setup();
  mount();
  await screen.findByRole('link', { name: /Run 1/ });
  expect(screen.queryByText('Automatic briefing')).not.toBeInTheDocument();
  await user.click(screen.getByRole('checkbox', { name: 'Show automatic briefings' }));
  expect(await screen.findByRole('link', { name: /Daily briefing/ })).toHaveTextContent(
    'Automatic briefing',
  );
  expect(urls.at(-1)!.searchParams.get('include_briefings')).toBe('true');
});

it('opens with briefings shown from a workspace link', async () => {
  const urls = recordQueries(() => ({ items: [], next_cursor: null }));
  mount('/research/jobs?briefings=1');
  expect(await screen.findByRole('checkbox', { name: 'Show automatic briefings' })).toBeChecked();
  await waitFor(() => expect(urls.at(-1)?.searchParams.get('include_briefings')).toBe('true'));
});

it('keeps a failed page distinct from an empty result and recovers on retry', async () => {
  let fail = true;
  server.use(
    http.get('/api/report-jobs', () =>
      fail
        ? HttpResponse.json({ error: { code: 'unavailable', message: 'Down.' } }, { status: 503 })
        : HttpResponse.json({ items: [], next_cursor: null }),
    ),
  );
  const user = userEvent.setup();
  mount('/research/jobs?status=running');
  expect(await screen.findByRole('button', { name: 'Retry research progress' })).toBeVisible();
  expect(screen.queryByText(/No running research/)).not.toBeInTheDocument();
  fail = false;
  await user.click(screen.getByRole('button', { name: 'Retry research progress' }));
  expect(await screen.findByText(/No running research/)).toBeVisible();
});

it('clears the page position and previous results when access changes', async () => {
  const urls = recordQueries((url) =>
    url.searchParams.get('cursor')
      ? { items: [row(30)], next_cursor: null }
      : { items: [row(1)], next_cursor: 'next' },
  );
  const user = userEvent.setup();
  mount();
  await screen.findByRole('link', { name: /Run 1/ });
  await user.click(screen.getByRole('button', { name: 'Older runs' }));
  await screen.findByRole('link', { name: /Run 30/ });
  act(() => invalidateWorkspaceAccess());
  expect(screen.queryByRole('link', { name: /Run 30/ })).not.toBeInTheDocument();
  await screen.findByRole('link', { name: /Run 1/ });
  expect(urls.at(-1)!.searchParams.has('cursor')).toBe(false);
});
