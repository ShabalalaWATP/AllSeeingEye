import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { expect, it } from 'vitest';
import { server } from '@/test/server';
import { applySession } from '@/test/render';
import { report } from '@/test/fixtures';
import { annotationMonitor } from '@/test/fixtures.monitors';
import { comparisonSources } from '@/test/comparisonHandlers';
import { AnnotationMonitorsSection } from './AnnotationMonitorsSection';
it('opens opt-in report controls, cancels private drafts and refreshes the scoped list after creating', async () => {
  applySession('user');
  comparisonSources();
  let created = false;
  const queries: string[] = [];
  server.use(
    http.get('/api/annotation-monitors', ({ request }) => {
      queries.push(request.url);
      return HttpResponse.json({
        items: created ? [annotationMonitor] : [],
        offset: 0,
        limit: 20,
        total: created ? 1 : 0,
      });
    }),
    http.post('/api/annotation-monitors', () => {
      created = true;
      return HttpResponse.json(annotationMonitor);
    }),
  );
  render(
    <MemoryRouter>
      <AnnotationMonitorsSection reportId={report.report.id} version={1} canCreate />
    </MemoryRouter>,
  );
  expect(queries).toHaveLength(0);
  await userEvent.click(screen.getByRole('button', { name: 'Monitor annotations' }));
  await screen.findByText(/No monitors in this selection/);
  expect(new URL(queries[0]!).searchParams.get('version_number')).toBe('1');
  await userEvent.click(screen.getByRole('button', { name: 'Create an annotation monitor' }));
  await userEvent.type(screen.getByLabelText('Monitor name'), 'Cancelled private draft');
  await userEvent.click(screen.getByRole('button', { name: 'Cancel monitor creation' }));
  expect(screen.queryByLabelText('Monitor name')).not.toBeInTheDocument();
  await userEvent.click(screen.getByRole('button', { name: 'Create an annotation monitor' }));
  expect(screen.getByLabelText('Monitor name')).toHaveValue('');
  await userEvent.type(screen.getByLabelText('Monitor name'), 'Watch');
  await userEvent.click(await screen.findByRole('checkbox', { name: /Select revision 2/ }));
  await userEvent.click(screen.getByLabelText('Selected claims'));
  await userEvent.click(screen.getByRole('button', { name: 'Create silent baseline' }));
  await screen.findByRole('link', { name: annotationMonitor.name });
  await waitFor(() => expect(screen.queryByLabelText('Monitor name')).not.toBeInTheDocument());
});
it('does not expose creation to a read-only report viewer', async () => {
  server.use(
    http.get('/api/annotation-monitors', () =>
      HttpResponse.json({ items: [], total: 0, offset: 0, limit: 20 }),
    ),
  );
  render(
    <MemoryRouter>
      <AnnotationMonitorsSection reportId={report.report.id} version={1} canCreate={false} />
    </MemoryRouter>,
  );
  await userEvent.click(screen.getByRole('button', { name: 'Monitor annotations' }));
  await screen.findByText(/No monitors in this selection/);
  expect(
    screen.queryByRole('button', { name: 'Create an annotation monitor' }),
  ).not.toBeInTheDocument();
});
