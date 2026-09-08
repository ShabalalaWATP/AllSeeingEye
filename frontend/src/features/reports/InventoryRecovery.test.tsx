import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { expect, it, vi } from 'vitest';
import { server } from '@/test/server';
import { renderApp } from '@/test/render';
import { annotationMonitor, monitorTransition, monitorDetail } from '@/test/fixtures.monitors';
import { saveBinaryFile } from '@/lib/downloadBinary';
import type { MonitorUpdate } from '@/lib/api/annotationMonitors';
vi.mock('@/lib/downloadBinary', () => ({ saveBinaryFile: vi.fn() }));
const unavailable = {
  ...annotationMonitor,
  mode: 'report_inventory',
  status: 'unavailable',
  unavailable_reason: 'Inventory capacity exceeded.',
};
function setup() {
  server.use(
    http.get('/api/annotation-monitors/:id', () => HttpResponse.json(unavailable)),
    http.get('/api/annotation-monitors/:id/transitions', () =>
      HttpResponse.json({ items: [monitorTransition], total: 1, limit: 20, offset: 0 }),
    ),
  );
}
it('keeps authorised retained transitions readable and exportable after inventory overflow', async () => {
  setup();
  server.use(
    http.get('/api/annotation-monitors/:id/transitions/:transition', () =>
      HttpResponse.json(monitorDetail),
    ),
    http.post(
      '/api/annotation-monitors/:id/transitions/:transition/export',
      async ({ request }) => {
        expect(await request.json()).toEqual({
          expected_comparison_sha256: monitorDetail.comparison.comparison_sha256,
        });
        return HttpResponse.json(monitorDetail);
      },
    ),
  );
  renderApp('/annotation-monitors/monitor-1', 'user');
  await screen.findByText(/Inventory capacity exceeded/);
  await userEvent.click(
    await screen.findByRole('link', { name: 'Transition 1: Annotation revision' }),
  );
  await userEvent.click(
    await screen.findByRole('button', { name: 'Export exact transition JSON' }),
  );
  await waitFor(() =>
    expect(saveBinaryFile).toHaveBeenCalledWith(
      'annotation-transition-transition-old.json',
      expect.objectContaining({ type: 'application/json' }),
    ),
  );
});
it('offers explicit recovery with CAS while preserving a capacity failure instead of claiming success', async () => {
  setup();
  const requests: MonitorUpdate[] = [];
  server.use(
    http.patch('/api/annotation-monitors/:id', async ({ request }) => {
      const body = (await request.json()) as MonitorUpdate;
      requests.push(body);
      return body.action === 'resume_rebaseline'
        ? HttpResponse.json(
            { error: { code: 'capacity', message: 'Complete inventory still exceeds 20 roots.' } },
            { status: 422 },
          )
        : HttpResponse.json({ ...annotationMonitor, mode: 'report_inventory', revision: 2 });
    }),
  );
  renderApp('/annotation-monitors/monitor-1', 'user');
  await screen.findByRole('button', { name: 'Resume and catch up' });
  expect(screen.getByRole('button', { name: 'Pause monitoring' })).toBeEnabled();
  await userEvent.click(
    screen.getByLabelText('I want to skip pending differences and start a fresh baseline.'),
  );
  await userEvent.click(screen.getByRole('button', { name: 'Confirm fresh baseline and resume' }));
  await screen.findByText('Complete inventory still exceeds 20 roots.');
  expect(screen.getByText(/Status: unavailable/)).toBeInTheDocument();
  await userEvent.click(screen.getByRole('button', { name: 'Resume and catch up' }));
  await screen.findByText(/Status: active/);
  expect(
    requests.map((item) => ({ action: item.action, revision: item.expected_revision })),
  ).toEqual([
    { action: 'resume_rebaseline', revision: 1 },
    { action: 'resume_catch_up', revision: 1 },
  ]);
});
it('surfaces denied historical access without substituting or exposing a previous comparison', async () => {
  setup();
  server.use(
    http.get('/api/annotation-monitors/:id/transitions', () =>
      HttpResponse.json(
        { error: { code: 'forbidden', message: 'Current report access is unavailable.' } },
        { status: 403 },
      ),
    ),
  );
  renderApp('/annotation-monitors/monitor-1', 'user');
  await screen.findByText(/Current report access is unavailable/);
  expect(
    screen.queryByRole('link', { name: 'Transition 1: Annotation revision' }),
  ).not.toBeInTheDocument();
  expect(
    screen.queryByRole('region', { name: 'Frozen annotation comparison' }),
  ).not.toBeInTheDocument();
});
