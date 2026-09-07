import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { expect, it } from 'vitest';
import { server } from '@/test/server';
import { renderApp } from '@/test/render';
import { annotationMonitor, monitorTransition } from '@/test/fixtures.monitors';
import type { MonitorUpdate } from '@/lib/api/annotationMonitors';
it.each(['resume_catch_up', 'resume_rebaseline'] as const)(
  'sends the explicit %s action with checkpoint CAS',
  async (action) => {
    const bodies: MonitorUpdate[] = [];
    server.use(
      http.get('/api/annotation-monitors/:id', () =>
        HttpResponse.json({ ...annotationMonitor, status: 'paused' }),
      ),
      http.get('/api/annotation-monitors/:id/transitions', () =>
        HttpResponse.json({ items: [], total: 0, offset: 0, limit: 20 }),
      ),
      http.patch('/api/annotation-monitors/:id', async ({ request }) => {
        bodies.push((await request.json()) as MonitorUpdate);
        return HttpResponse.json({ ...annotationMonitor, revision: 2 });
      }),
    );
    renderApp('/annotation-monitors/monitor-1', 'user');
    await screen.findByRole('button', { name: 'Resume and catch up' });
    if (action === 'resume_rebaseline') {
      await userEvent.click(
        screen.getByLabelText('I want to skip pending differences and start a fresh baseline.'),
      );
      await userEvent.click(
        screen.getByRole('button', { name: 'Confirm fresh baseline and resume' }),
      );
    } else await userEvent.click(screen.getByRole('button', { name: 'Resume and catch up' }));
    await waitFor(() =>
      expect(bodies).toEqual([{ expected_revision: 1, action, rebaseline: false }]),
    );
    await screen.findByRole('button', { name: 'Pause monitoring' });
  },
);
it('pages visible monitor choices and recovers an unavailable list', async () => {
  let fail = true;
  server.use(
    http.get('/api/annotation-monitors', ({ request }) => {
      const offset = Number(new URL(request.url).searchParams.get('offset'));
      if (fail)
        return HttpResponse.json(
          { error: { code: 'unavailable', message: 'Monitor list unavailable.' } },
          { status: 503 },
        );
      return HttpResponse.json({
        items: offset === 0 ? [annotationMonitor] : [],
        total: 21,
        offset,
        limit: 20,
      });
    }),
  );
  renderApp('/annotation-monitors', 'user');
  await screen.findByText('Monitor list unavailable.');
  fail = false;
  await userEvent.click(screen.getByRole('button', { name: 'Refresh monitors' }));
  await screen.findByRole('link', { name: annotationMonitor.name });
  await userEvent.click(screen.getByRole('button', { name: 'Next monitor page' }));
  await screen.findByText(/No monitors in this selection/);
  await userEvent.click(screen.getByRole('button', { name: 'Previous monitor page' }));
  await screen.findByRole('link', { name: annotationMonitor.name });
});
it('retains paged silent transition history and restricts editing to authorised managers', async () => {
  server.use(
    http.get('/api/annotation-monitors/:id', () =>
      HttpResponse.json({ ...annotationMonitor, created_by: 'someone-else' }),
    ),
    http.get('/api/annotation-monitors/:id/transitions', ({ request }) => {
      const offset = Number(new URL(request.url).searchParams.get('offset'));
      return HttpResponse.json({
        items: [
          {
            ...monitorTransition,
            id: offset === 0 ? 'old' : 'next',
            sequence: offset === 0 ? 1 : 21,
            kind: 'rebaseline',
            changed_categories: [],
          },
        ],
        total: 21,
        offset,
        limit: 20,
      });
    }),
  );
  renderApp('/annotation-monitors/monitor-1', 'user');
  await screen.findByRole('link', { name: 'Transition 1: Fresh baseline' });
  expect(screen.queryByRole('button', { name: 'Pause monitoring' })).not.toBeInTheDocument();
  expect(
    screen.queryByRole('button', { name: 'Remove monitor and history' }),
  ).not.toBeInTheDocument();
  await userEvent.click(screen.getByRole('button', { name: 'Next transition page' }));
  await screen.findByRole('link', { name: 'Transition 21: Fresh baseline' });
  expect(screen.getByRole('link', { name: 'Transition 21: Fresh baseline' })).toHaveAttribute(
    'href',
    '/annotation-monitors/monitor-1/transitions/next',
  );
  await userEvent.click(screen.getByRole('button', { name: 'Previous transition page' }));
  await screen.findByRole('link', { name: 'Transition 1: Fresh baseline' });
});
