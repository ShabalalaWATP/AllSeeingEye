import { render, screen, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { expect, it, vi } from 'vitest';
import { server } from '@/test/server';
import { renderApp, applySession } from '@/test/render';
import { comparisonSources } from '@/test/comparisonHandlers';
import { report, plainUser, tokenFor } from '@/test/fixtures';
import { annotationMonitor, monitorTransition, monitorDetail } from '@/test/fixtures.monitors';
import { comparisonClaimAfter } from '@/test/fixtures.comparisons';
import { useAuthStore } from '@/stores/auth';
import { invalidateWorkspaceAccess } from '@/lib/workspaceAccess';
import { AnnotationMonitorCreate } from './AnnotationMonitorCreate';
import { MonitorPrivacyBoundary } from './MonitorPrivacyBoundary';
import type { MonitorUpdate } from '@/lib/api/annotationMonitors';
function handlers(monitor = annotationMonitor) {
  server.use(
    http.get('/api/annotation-monitors/:id', () => HttpResponse.json(monitor)),
    http.get('/api/annotation-monitors/:id/transitions', () =>
      HttpResponse.json({ items: [monitorTransition], offset: 0, limit: 20, total: 1 }),
    ),
    http.get('/api/annotation-monitors', () =>
      HttpResponse.json({ items: [monitor], offset: 0, limit: 20, total: 1 }),
    ),
  );
}
it('creates only explicitly selected current roots with notifications off and a silent baseline', async () => {
  applySession('user');
  comparisonSources();
  const created = vi.fn();
  const bodies: unknown[] = [];
  server.use(
    http.post('/api/annotation-monitors', async ({ request }) => {
      bodies.push(await request.json());
      return HttpResponse.json(annotationMonitor);
    }),
  );
  render(<AnnotationMonitorCreate reportId={report.report.id} version={1} onCreated={created} />);
  expect(
    screen.getByText(/Team workspace alerts are shared with authorised team members/),
  ).toBeInTheDocument();
  expect(screen.getByRole('button', { name: 'Create silent baseline' })).toBeDisabled();
  await userEvent.type(screen.getByLabelText('Monitor name'), 'Correction watch');
  await userEvent.click(await screen.findByRole('checkbox', { name: /Select revision 2/ }));
  await userEvent.click(screen.getByLabelText('Selected claims'));
  expect(screen.getByLabelText('Create alerts for meaningful changes')).not.toBeChecked();
  await userEvent.click(screen.getByRole('button', { name: 'Create silent baseline' }));
  await waitFor(() => expect(created).toHaveBeenCalledOnce());
  expect(bodies).toEqual([
    {
      mode: 'selected_roots',
      name: 'Correction watch',
      selection: {
        report_id: report.report.id,
        version_number: 1,
        revisions: [
          { claim_id: comparisonClaimAfter.claim_id, revision_id: comparisonClaimAfter.id },
        ],
        identity_revisions: [],
        relationship_revisions: [],
      },
      categories: ['claim'],
      notify_on_change: false,
    },
  ]);
});
it('recovers a stale creation by clearing selected revisions and refreshing inventory', async () => {
  applySession('user');
  comparisonSources();
  server.use(
    http.post('/api/annotation-monitors', () =>
      HttpResponse.json(
        { error: { code: 'conflict', message: 'Selected revision is no longer latest.' } },
        { status: 409 },
      ),
    ),
  );
  render(<AnnotationMonitorCreate reportId={report.report.id} version={1} onCreated={vi.fn()} />);
  await userEvent.type(screen.getByLabelText('Monitor name'), 'Watch');
  await userEvent.click(await screen.findByRole('checkbox', { name: /Select revision 2/ }));
  await userEvent.click(screen.getByLabelText('Selected claims'));
  await userEvent.click(screen.getByRole('button', { name: 'Create silent baseline' }));
  await screen.findByText('Selected revision is no longer latest.');
  await userEvent.click(
    screen.getByRole('button', { name: 'Refresh inventory and clear selections' }),
  );
  expect(await screen.findByRole('checkbox', { name: /Select revision 2/ })).not.toBeChecked();
  expect(screen.getByRole('button', { name: 'Create silent baseline' })).toBeDisabled();
});
it('discards private monitor drafts on workspace, report version and account changes', async () => {
  applySession('user');
  comparisonSources();
  const body = (scope: string) => (
    <MonitorPrivacyBoundary scope={scope}>
      <AnnotationMonitorCreate reportId={report.report.id} version={1} onCreated={vi.fn()} />
    </MonitorPrivacyBoundary>
  );
  const { rerender } = render(body('v1'));
  await userEvent.type(screen.getByLabelText('Monitor name'), 'private one');
  act(() => invalidateWorkspaceAccess());
  expect(screen.getByLabelText('Monitor name')).toHaveValue('');
  await userEvent.type(screen.getByLabelText('Monitor name'), 'private two');
  rerender(body('v2'));
  expect(screen.getByLabelText('Monitor name')).toHaveValue('');
  await userEvent.type(screen.getByLabelText('Monitor name'), 'private three');
  act(() => useAuthStore.getState().setSession(tokenFor({ ...plainUser, id: 'other-person' })));
  expect(screen.getByLabelText('Monitor name')).toHaveValue('');
});
it('pauses with CAS, blocks a conflicting overwrite, and reloads the authoritative state', async () => {
  handlers();
  const bodies: MonitorUpdate[] = [];
  let failed = true;
  server.use(
    http.patch('/api/annotation-monitors/:id', async ({ request }) => {
      bodies.push((await request.json()) as MonitorUpdate);
      return failed
        ? HttpResponse.json(
            { error: { code: 'conflict', message: 'Checkpoint changed.' } },
            { status: 409 },
          )
        : HttpResponse.json({ ...annotationMonitor, status: 'paused', revision: 2 });
    }),
  );
  renderApp('/annotation-monitors/monitor-1', 'user');
  await userEvent.click(await screen.findByRole('button', { name: 'Pause monitoring' }));
  await screen.findByText(/Checkpoint changed/);
  expect(screen.getByRole('button', { name: 'Pause monitoring' })).toBeDisabled();
  failed = false;
  await userEvent.click(screen.getByRole('button', { name: 'Reload monitor state' }));
  await userEvent.click(await screen.findByRole('button', { name: 'Pause monitoring' }));
  await screen.findByRole('button', { name: 'Resume and catch up' });
  expect(bodies[0]).toEqual({ expected_revision: 1, action: 'pause', rebaseline: false });
});
it('shows unavailable state without treating a failed observation as unchanged', async () => {
  handlers({
    ...annotationMonitor,
    status: 'unavailable',
    unavailable_reason: 'Retained inputs are unavailable.',
  });
  renderApp('/annotation-monitors/monitor-1', 'user');
  await screen.findByText(/Retained inputs are unavailable/);
  expect(screen.getByRole('button', { name: 'Pause monitoring' })).toBeInTheDocument();
  expect(screen.getByRole('region', { name: 'Recorded transitions' })).toBeInTheDocument();
  expect(screen.getByRole('button', { name: 'Remove monitor and history' })).toBeInTheDocument();
});
it('requires permanent-removal confirmation, allows cancellation and sends the exact CAS token', async () => {
  handlers();
  const removed = vi.fn();
  server.use(
    http.delete('/api/annotation-monitors/:id', ({ request }) => {
      removed(new URL(request.url).searchParams.get('expected_revision'));
      return new HttpResponse(null, { status: 204 });
    }),
  );
  renderApp('/annotation-monitors/monitor-1', 'user');
  await userEvent.click(await screen.findByRole('button', { name: 'Remove monitor and history' }));
  expect(screen.getByRole('button', { name: 'Permanently remove monitor' })).toBeDisabled();
  await userEvent.click(screen.getByRole('button', { name: 'Cancel removal' }));
  expect(removed).not.toHaveBeenCalled();
  await userEvent.click(screen.getByRole('button', { name: 'Remove monitor and history' }));
  await userEvent.click(
    screen.getByLabelText('I understand this monitor and its history will be permanently removed.'),
  );
  await userEvent.click(screen.getByRole('button', { name: 'Permanently remove monitor' }));
  await waitFor(() => expect(removed).toHaveBeenCalledWith('1'));
  await screen.findByRole('heading', { name: 'Annotation monitoring' });
});
it('opens the stored transition from paged history rather than fetching current report content', async () => {
  handlers();
  server.use(
    http.get('/api/annotation-monitors/:id/transitions/:transition', ({ params }) => {
      expect(params.transition).toBe('transition-old');
      return HttpResponse.json(monitorDetail);
    }),
  );
  renderApp('/annotation-monitors/monitor-1', 'user');
  await userEvent.click(
    await screen.findByRole('link', { name: 'Transition 1: Annotation revision' }),
  );
  await screen.findByRole('heading', { name: 'Stored monitoring transition' });
  await screen.findByText('Original analytical claim');
  expect(screen.getByText(/Notification policy revision 1/)).toBeInTheDocument();
});
