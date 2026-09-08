import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { expect, it, vi } from 'vitest';
import { server } from '@/test/server';
import { applySession, renderApp } from '@/test/render';
import { report } from '@/test/fixtures';
import { annotationMonitor } from '@/test/fixtures.monitors';
import { comparisonSources } from '@/test/comparisonHandlers';
import { annotationMonitorSchema } from '@/lib/api/annotationMonitors';
import type { AnnotationMonitor, MonitorCreate } from '@/lib/api/annotationMonitors';
import { AnnotationMonitorCreate } from './AnnotationMonitorCreate';
import { MonitorConfiguration } from './MonitorConfiguration';
import { AnnotationMonitorList } from './AnnotationMonitorList';
const emptySelection = {
  report_id: report.report.id,
  version_number: 1,
  revisions: [],
  identity_revisions: [],
  relationship_revisions: [],
};
const inventoryMonitor: AnnotationMonitor = {
  ...annotationMonitor,
  mode: 'report_inventory',
  selection: emptySelection,
};
function setup() {
  applySession('user');
  comparisonSources();
}
it('creates a silent inventory baseline for an empty saved report without selecting roots', async () => {
  setup();
  const created = vi.fn();
  const bodies: MonitorCreate[] = [];
  server.use(
    http.post('/api/annotation-monitors', async ({ request }) => {
      bodies.push((await request.json()) as MonitorCreate);
      return HttpResponse.json(inventoryMonitor);
    }),
  );
  render(<AnnotationMonitorCreate reportId={report.report.id} version={1} onCreated={created} />);
  expect(screen.getByLabelText('Selected annotations')).toBeChecked();
  await userEvent.click(screen.getByLabelText('Whole saved report inventory'));
  expect(screen.queryByRole('button', { name: /Browse revisions/ })).not.toBeInTheDocument();
  expect(screen.queryByLabelText('Annotation type')).not.toBeInTheDocument();
  await userEvent.type(screen.getByLabelText('Monitor name'), 'All future reviews');
  expect(screen.getByRole('button', { name: 'Create silent baseline' })).toBeDisabled();
  await userEvent.click(screen.getByLabelText('Claims'));
  expect(screen.getByLabelText('Create alerts for meaningful changes')).not.toBeChecked();
  await userEvent.click(screen.getByRole('button', { name: 'Create silent baseline' }));
  await waitFor(() => expect(created).toHaveBeenCalledOnce());
  expect(bodies).toEqual([
    {
      mode: 'report_inventory',
      name: 'All future reviews',
      selection: emptySelection,
      categories: ['claim'],
      notify_on_change: false,
    },
  ]);
  expect(
    screen.getByText(/Categories control alerts, not which roots are enrolled/),
  ).toBeInTheDocument();
});
it('clears selected roots and category choices when switching mode instead of leaking them into an inventory request', async () => {
  setup();
  render(<AnnotationMonitorCreate reportId={report.report.id} version={1} onCreated={vi.fn()} />);
  await userEvent.click(await screen.findByRole('checkbox', { name: /Select revision 2/ }));
  await userEvent.click(screen.getByLabelText('Selected claims'));
  await userEvent.click(screen.getByLabelText('Whole saved report inventory'));
  expect(screen.getByLabelText('Claims')).not.toBeChecked();
  await userEvent.click(screen.getByLabelText('Identity reviews'));
  await userEvent.click(screen.getByLabelText('Selected annotations'));
  expect(await screen.findByRole('checkbox', { name: /Select revision 2/ })).not.toBeChecked();
  expect(screen.queryByLabelText('Selected claims')).not.toBeInTheDocument();
  expect(screen.getByRole('button', { name: 'Create silent baseline' })).toBeDisabled();
});
it('allows future inventory category configuration with explicit policy rebaseline but offers no mode edit', async () => {
  const save = vi.fn();
  render(<MonitorConfiguration monitor={inventoryMonitor} busy={false} onSave={save} />);
  expect(screen.queryByLabelText('Whole saved report inventory')).not.toBeInTheDocument();
  await userEvent.click(screen.getByLabelText('Organisation relationships'));
  expect(screen.getByRole('button', { name: 'Save monitor configuration' })).toBeDisabled();
  await userEvent.click(
    screen.getByLabelText(
      'I confirm a fresh baseline for this notification policy, skipping pending differences.',
    ),
  );
  await userEvent.click(screen.getByRole('button', { name: 'Save monitor configuration' }));
  expect(save).toHaveBeenCalledWith(
    expect.objectContaining({
      categories: ['claim', 'relationship'],
      rebaseline: true,
      action: 'configure',
    }),
  );
  expect(save.mock.calls[0]?.[0]).not.toHaveProperty('mode');
});
it('shows mode and retained checkpoint capacity limits when inventory monitoring becomes unavailable', async () => {
  const value = {
    ...inventoryMonitor,
    status: 'unavailable',
    unavailable_reason: 'Inventory exceeds capacity.',
  };
  server.use(
    http.get('/api/annotation-monitors/:id', () => HttpResponse.json(value)),
    http.get('/api/annotation-monitors/:id/transitions', () =>
      HttpResponse.json({ items: [], total: 0, limit: 20, offset: 0 }),
    ),
  );
  renderApp('/annotation-monitors/monitor-1', 'user');
  await screen.findByText(/Monitoring mode: Whole saved report inventory/);
  expect(screen.getByText(/20-root capacity rather than silently truncating/)).toBeInTheDocument();
  expect(screen.getByText(/last valid checkpoint inventory/)).toBeInTheDocument();
  expect(
    screen.getByText('This checkpoint contains 0 of at most 20 annotations.'),
  ).toBeInTheDocument();
  expect(screen.getByRole('button', { name: 'Pause monitoring' })).toBeInTheDocument();
  expect(screen.getByRole('button', { name: 'Resume and catch up' })).toBeInTheDocument();
});
it('identifies inventory monitors in a scoped list and preserves selected mode for historical records', async () => {
  const { mode: omitted, ...legacy } = annotationMonitor;
  expect(annotationMonitorSchema.parse(legacy).mode).toBe(omitted);
  server.use(
    http.get('/api/annotation-monitors', () =>
      HttpResponse.json({ items: [inventoryMonitor], total: 1, offset: 0, limit: 20 }),
    ),
  );
  render(
    <MemoryRouter>
      <AnnotationMonitorList scope={{ reportId: report.report.id, version: 1 }} />
    </MemoryRouter>,
  );
  await screen.findByText(/Whole saved report inventory; version 1/);
});
it('rejects over-capacity creation visibly and never claims a partial baseline succeeded', async () => {
  setup();
  const created = vi.fn();
  server.use(
    http.post('/api/annotation-monitors', () =>
      HttpResponse.json(
        { error: { code: 'capacity', message: 'More than 20 annotation roots.' } },
        { status: 422 },
      ),
    ),
  );
  render(<AnnotationMonitorCreate reportId={report.report.id} version={1} onCreated={created} />);
  await userEvent.click(screen.getByLabelText('Whole saved report inventory'));
  await userEvent.type(screen.getByLabelText('Monitor name'), 'Inventory');
  await userEvent.click(screen.getByLabelText('Claims'));
  await userEvent.click(screen.getByRole('button', { name: 'Create silent baseline' }));
  await screen.findByText('More than 20 annotation roots.');
  expect(created).not.toHaveBeenCalled();
  expect(screen.getByText(/No partial inventory baseline is created/)).toBeInTheDocument();
  await userEvent.click(screen.getByRole('button', { name: 'Clear inventory choices and retry' }));
  expect(screen.getByLabelText('Claims')).not.toBeChecked();
});
