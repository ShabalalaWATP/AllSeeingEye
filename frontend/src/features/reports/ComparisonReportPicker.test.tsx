import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { expect, it, vi } from 'vitest';
import { report } from '@/test/fixtures';
import { comparisonSources } from '@/test/comparisonHandlers';
import { server } from '@/test/server';
import { ComparisonReportPicker } from './ComparisonReportPicker';
import { ReportDiff } from './ReportDiff';
it('finds an older report through scoped search and pagination without a UUID field', async () => {
  const queries: string[] = [];
  const old = {
    ...report.report,
    id: 'old-report',
    title: 'Older archived research',
    latest_version: 3,
  };
  server.use(
    http.get('/api/annotation-comparisons/reports', ({ request }) => {
      const p = new URL(request.url).searchParams;
      queries.push(p.toString());
      return HttpResponse.json({
        items: p.get('offset') === '20' ? [old] : [report.report],
        total: 21,
        offset: Number(p.get('offset')),
        limit: 20,
      });
    }),
  );
  const chosen = vi.fn();
  render(
    <ComparisonReportPicker name="Selected after" current={report.report} onSelect={chosen} />,
  );
  await userEvent.click(screen.getByRole('button', { name: 'Choose selected after report' }));
  await screen.findByRole('button', { name: 'Next report choices' });
  await userEvent.type(screen.getByLabelText('Selected after: search report titles'), 'Older');
  await userEvent.click(screen.getByRole('button', { name: 'Search selected after reports' }));
  await waitFor(() => expect(queries.some((q) => q.includes('q=Older'))).toBe(true));
  await userEvent.click(screen.getByRole('button', { name: 'Next report choices' }));
  await userEvent.click(
    await screen.findByRole('button', { name: 'Use report: Older archived research' }),
  );
  expect(chosen).toHaveBeenCalledWith(old);
  expect(screen.queryByLabelText(/UUID/i)).not.toBeInTheDocument();
  expect(screen.queryByRole('button', { name: 'Next report choices' })).not.toBeInTheDocument();
});
it('recovers failed report choices and explains an empty search', async () => {
  let failed = true;
  server.use(
    http.get('/api/annotation-comparisons/reports', () =>
      failed
        ? HttpResponse.json(
            { error: { code: 'unavailable', message: 'Choices unavailable.' } },
            { status: 503 },
          )
        : HttpResponse.json({ items: [], total: 0, offset: 0, limit: 20 }),
    ),
  );
  render(
    <ComparisonReportPicker name="Selected before" current={report.report} onSelect={vi.fn()} />,
  );
  await userEvent.click(screen.getByRole('button', { name: 'Choose selected before report' }));
  await screen.findByText('Choices unavailable.');
  failed = false;
  await userEvent.click(screen.getByRole('button', { name: 'Retry report choices' }));
  await screen.findByText('No accessible report titles match this search.');
});
it('lets an operator return to the current report when a selected report becomes unavailable', async () => {
  comparisonSources();
  const old = { ...report.report, id: 'old-report', title: 'Older research', latest_version: 2 };
  server.use(
    http.get('/api/annotation-comparisons/reports', () =>
      HttpResponse.json({ items: [old], total: 1, limit: 20, offset: 0 }),
    ),
    http.get('/api/reports/old-report', () =>
      HttpResponse.json(
        { error: { code: 'not_found', message: 'Selected report unavailable.' } },
        { status: 404 },
      ),
    ),
  );
  render(<ReportDiff id={report.report.id} current={2} latest={2} />);
  await userEvent.click(screen.getByText('Compare versions'));
  await userEvent.click(screen.getByRole('button', { name: 'Compare annotations and confidence' }));
  await userEvent.click(
    await screen.findByRole('button', { name: 'Choose selected after report' }),
  );
  await userEvent.click(await screen.findByRole('button', { name: 'Use report: Older research' }));
  await screen.findByText('Selected report unavailable.');
  await userEvent.click(
    screen.getByRole('button', { name: 'Discard unavailable inputs and return to this report' }),
  );
  await screen.findByRole('button', { name: 'Compare exact selected inputs' });
  expect(screen.getByLabelText('Selected after: version')).toHaveValue('2');
});
