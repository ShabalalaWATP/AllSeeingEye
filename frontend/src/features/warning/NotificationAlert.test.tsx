import { act, render, screen } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { MemoryRouter } from 'react-router';
import { expect, it, vi } from 'vitest';
import { invalidateWorkspaceAccess } from '@/lib/workspaceAccess';
import { alert } from '@/test/fixtures.warning';
import { applySession } from '@/test/render';
import { server } from '@/test/server';
import { NotificationAlert } from './NotificationAlert';

function mount(id: string | null) {
  applySession('user');
  return render(
    <MemoryRouter initialEntries={[id === null ? '/warning' : `/warning?alert=${id}`]}>
      <NotificationAlert />
    </MemoryRouter>,
  );
}

it.each([null, 'not-an-alert'])(
  'does not fetch or render an invalid notification ID: %s',
  async (id) => {
    const requested = vi.fn();
    server.use(
      http.get('/api/warning/alerts/:id', () => {
        requested();
        return HttpResponse.json(alert);
      }),
    );
    mount(id);
    await act(async () => {
      await Promise.resolve();
    });
    expect(screen.queryByRole('region', { name: 'Opened notification' })).not.toBeInTheDocument();
    expect(requested).not.toHaveBeenCalled();
  },
);

it('loads the selected alert through the authenticated API then clears details after access changes', async () => {
  let allowed = true;
  const receivedAuth = vi.fn();
  server.use(
    http.get('/api/warning/alerts/:id', ({ request, params }) => {
      expect(params.id).toBe(alert.id);
      receivedAuth(request.headers.get('Authorization'));
      return allowed ? HttpResponse.json(alert) : new HttpResponse(null, { status: 404 });
    }),
  );
  mount(alert.id);
  expect(screen.getByText('Loading the alert securely…')).toBeVisible();
  expect(await screen.findByRole('heading', { name: alert.title })).toBeVisible();
  expect(screen.getByText(alert.summary)).toBeVisible();
  expect(receivedAuth).toHaveBeenCalledWith(expect.stringMatching(/^Bearer /));
  allowed = false;
  act(() => invalidateWorkspaceAccess());
  expect(screen.queryByRole('heading', { name: alert.title })).not.toBeInTheDocument();
  expect(
    await screen.findByText('This alert is unavailable or your access has changed.'),
  ).toBeVisible();
});

it('shows an unavailable alert without retaining private details', async () => {
  server.use(http.get('/api/warning/alerts/:id', () => new HttpResponse(null, { status: 404 })));
  mount(alert.id);
  expect(
    await screen.findByText('This alert is unavailable or your access has changed.'),
  ).toBeVisible();
  expect(screen.queryByRole('heading', { name: alert.title })).not.toBeInTheDocument();
});
