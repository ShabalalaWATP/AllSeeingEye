import { screen, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { expect, it, vi } from 'vitest';
import { server } from '@/test/server';
import { renderApp } from '@/test/render';
import { monitorDetail } from '@/test/fixtures.monitors';
import { tokenFor, plainUser } from '@/test/fixtures';
import { useAuthStore } from '@/stores/auth';
import { saveBinaryFile } from '@/lib/downloadBinary';
vi.mock('@/lib/downloadBinary', () => ({ saveBinaryFile: vi.fn() }));
const route = '/annotation-monitors/monitor-1/transitions/transition-old';
function detail() {
  server.use(
    http.get('/api/annotation-monitors/:id/transitions/:transition', () =>
      HttpResponse.json(monitorDetail),
    ),
  );
}
it('exports only the exact stored transition digest even after newer corrections exist', async () => {
  detail();
  const bodies: unknown[] = [];
  server.use(
    http.post(
      '/api/annotation-monitors/:id/transitions/:transition/export',
      async ({ params, request }) => {
        expect(params.transition).toBe('transition-old');
        bodies.push(await request.json());
        return HttpResponse.json(monitorDetail);
      },
    ),
  );
  renderApp(route, 'user');
  await userEvent.click(
    await screen.findByRole('button', { name: 'Export exact transition JSON' }),
  );
  await waitFor(() =>
    expect(saveBinaryFile).toHaveBeenCalledWith(
      'annotation-transition-transition-old.json',
      expect.objectContaining({ type: 'application/json' }),
    ),
  );
  expect(bodies).toEqual([
    { expected_comparison_sha256: monitorDetail.comparison.comparison_sha256 },
  ]);
});
it('keeps missing historical transitions unavailable without requesting latest content', async () => {
  server.use(
    http.get('/api/annotation-monitors/:id/transitions/:transition', () =>
      HttpResponse.json(
        { error: { code: 'not_found', message: 'Retained transition no longer available.' } },
        { status: 404 },
      ),
    ),
  );
  renderApp(route, 'user');
  await screen.findByText(/Retained transition no longer available/);
  expect(
    screen.queryByRole('button', { name: 'Export exact transition JSON' }),
  ).not.toBeInTheDocument();
  expect(
    screen.queryByRole('region', { name: 'Frozen annotation comparison' }),
  ).not.toBeInTheDocument();
});
it('shows a failed export and saves no file', async () => {
  detail();
  server.use(
    http.post('/api/annotation-monitors/:id/transitions/:transition/export', () =>
      HttpResponse.json(
        { error: { code: 'conflict', message: 'Stored manifest failed its integrity check.' } },
        { status: 409 },
      ),
    ),
  );
  renderApp(route, 'user');
  await userEvent.click(
    await screen.findByRole('button', { name: 'Export exact transition JSON' }),
  );
  await screen.findByText('Stored manifest failed its integrity check.');
  expect(saveBinaryFile).not.toHaveBeenCalled();
});
it('aborts pending export on account change before any file can be saved', async () => {
  detail();
  let resolve: (() => void) | undefined;
  const pending = new Promise<void>((done) => {
    resolve = done;
  });
  let started = false;
  server.use(
    http.post('/api/annotation-monitors/:id/transitions/:transition/export', async () => {
      started = true;
      await pending;
      return HttpResponse.json(monitorDetail);
    }),
  );
  renderApp(route, 'user');
  await userEvent.click(
    await screen.findByRole('button', { name: 'Export exact transition JSON' }),
  );
  await waitFor(() => expect(started).toBe(true));
  act(() => useAuthStore.getState().setSession(tokenFor({ ...plainUser, id: 'different-person' })));
  await act(async () => {
    resolve?.();
    await pending;
  });
  expect(saveBinaryFile).not.toHaveBeenCalled();
});
