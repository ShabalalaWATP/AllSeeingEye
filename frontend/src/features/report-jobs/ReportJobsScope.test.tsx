import { render, screen, waitFor, within } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { MemoryRouter, Route, Routes, useLocation } from 'react-router';
import { expect, it } from 'vitest';
import type { ReportJob } from '@/lib/api/reportJobs';
import { adminUser, plainUser } from '@/test/fixtures';
import { applySession } from '@/test/render';
import { reportJob } from '@/test/reportJobFixture';
import { server } from '@/test/server';
import ReportJobsPage from './ReportJobsPage';

const desk = {
  id: '44444444-4444-4444-8444-444444444444',
  name: 'Northern desk',
  is_active: true,
  created_by: adminUser.id,
  created_at: '2026-09-06T10:00:00Z',
  updated_at: '2026-09-06T10:00:00Z',
  description: null,
};
const id = (index: number) => `00000000-0000-4000-8000-${String(index).padStart(12, '0')}`;
const row = (index: number, changes: Partial<ReportJob>) =>
  reportJob({ id: id(index), title: `Run ${index}`, status: 'completed', ...changes });
const own = row(1, { owner_id: adminUser.id, owner_name: adminUser.display_name });
const theirs = row(2, { owner_id: plainUser.id, owner_name: plainUser.display_name });
const team = row(3, { owner_id: plainUser.id, owner_name: null, team_id: desk.id });

function Address() {
  return <output data-testid="address">{useLocation().search}</output>;
}
const address = () => screen.getByTestId('address').textContent;

function mount(session: 'admin' | 'user', path = '/research/jobs') {
  applySession(session);
  const urls: URL[] = [];
  server.use(
    http.get('/api/teams', () => HttpResponse.json({ items: [desk] })),
    http.get('/api/teams/:id', () => HttpResponse.json({ team: desk, members: [] })),
    http.get('/api/report-jobs', ({ request }) => {
      const url = new URL(request.url);
      urls.push(url);
      if (url.searchParams.get('scope') === 'all')
        return HttpResponse.json({ items: [own, theirs, team], next_cursor: null });
      return HttpResponse.json({
        items: url.searchParams.get('cursor') ? [row(9, {})] : [own],
        next_cursor: url.searchParams.get('cursor') ? null : 'next',
      });
    }),
  );
  render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route
          path="/research/jobs"
          element={
            <>
              <ReportJobsPage />
              <Address />
            </>
          }
        />
      </Routes>
    </MemoryRouter>,
  );
  return urls;
}

it('defaults administrators to their own runs and widens to all users explicitly', async () => {
  const urls = mount('admin');
  const user = userEvent.setup();
  expect(await screen.findByRole('link', { name: /Run 1/ })).toHaveTextContent('Personal');
  const scope = screen.getByRole('group', { name: 'Whose research runs to show' });
  expect(within(scope).getByRole('button', { name: 'Mine and my teams' })).toHaveAttribute(
    'aria-pressed',
    'true',
  );
  expect(
    screen.getByText(/your personal research runs and research runs from your current teams/i),
  ).toBeVisible();
  expect(urls.every((url) => !url.searchParams.has('scope'))).toBe(true);

  // The page position belongs to one scope and resets when the scope changes.
  await user.click(screen.getByRole('button', { name: 'Older runs' }));
  await screen.findByRole('link', { name: /Run 9/ });
  await user.click(within(scope).getByRole('button', { name: 'All users' }));
  expect(await screen.findByRole('link', { name: /Run 2/ })).toHaveTextContent(
    'Personal: Uma User',
  );
  expect(screen.getByRole('link', { name: /Run 3/ })).toHaveTextContent('Team: Northern desk');
  expect(screen.getByRole('link', { name: /Run 1/ })).not.toHaveTextContent('Personal:');
  expect(screen.getByText('Page 1')).toBeVisible();
  expect(screen.getByText(/every user's personal research runs/i)).toBeVisible();
  const last = urls.at(-1)!;
  expect(last.searchParams.get('scope')).toBe('all');
  expect(last.searchParams.has('cursor')).toBe(false);
  expect(address()).toBe('?scope=all');

  // Other filters keep the chosen scope in the address.
  const filters = screen.getByRole('group', { name: 'Show research runs' });
  await user.click(within(filters).getByRole('button', { name: 'Finished' }));
  await waitFor(() => expect(address()).toBe('?scope=all&status=finished'));
  expect(urls.at(-1)!.searchParams.get('scope')).toBe('all');
});

it('opens the administrative view from the address', async () => {
  const urls = mount('admin', '/research/jobs?scope=all');
  await screen.findByRole('link', { name: /Run 2/ });
  expect(urls.every((url) => url.searchParams.get('scope') === 'all')).toBe(true);
});

it('never offers or requests every user’s runs for other roles', async () => {
  const urls = mount('user', '/research/jobs?scope=all');
  await screen.findByRole('link', { name: /Run 1/ });
  expect(screen.queryByRole('group', { name: /Whose research runs/ })).not.toBeInTheDocument();
  expect(urls.every((url) => !url.searchParams.has('scope'))).toBe(true);
});
