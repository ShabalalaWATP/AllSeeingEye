import { act, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { expect, it } from 'vitest';
import { invalidateWorkspaceAccess } from '@/lib/workspaceAccess';
import { report } from '@/test/fixtures';
import { server } from '@/test/server';
import { ClaimAnnotations } from './ClaimAnnotations';

it('loads annotations only when opened and preserves the selected report version', async () => {
  const calls: URL[] = [];
  server.use(
    http.get('/api/claims', ({ request }) => {
      calls.push(new URL(request.url));
      return HttpResponse.json({ items: [], total: 0, limit: 20, offset: 0 });
    }),
  );
  render(<ClaimAnnotations reportId="report-1" version={3} />);
  expect(calls).toHaveLength(0);
  await userEvent.click(screen.getByRole('button', { name: 'Claim annotations and history' }));
  expect(
    await screen.findByText('No claim annotations for this report version.'),
  ).toBeInTheDocument();
  expect(calls[0]?.searchParams.get('report_id')).toBe('report-1');
  expect(calls[0]?.searchParams.get('version_number')).toBe('3');
});

it('shows a failed private request without pretending the ledger is empty', async () => {
  server.use(
    http.get('/api/claims', () =>
      HttpResponse.json(
        { error: { code: 'not_found', message: 'Claim report unavailable.' } },
        { status: 404 },
      ),
    ),
  );
  render(<ClaimAnnotations reportId="report-1" version={1} />);
  await userEvent.click(screen.getByRole('button', { name: 'Claim annotations and history' }));
  expect(await screen.findByRole('alert')).toBeInTheDocument();
  expect(
    screen.queryByText('No claim annotations for this report version.'),
  ).not.toBeInTheDocument();
});

it('clears unsaved private claim text after access invalidation', async () => {
  server.use(
    http.get('/api/claims', () => HttpResponse.json({ items: [], total: 0, limit: 20, offset: 0 })),
  );
  render(
    <ClaimAnnotations
      reportId="report-1"
      version={1}
      evidence={report.version.evidence}
      canCreate
    />,
  );
  const user = userEvent.setup();
  await user.click(screen.getByRole('button', { name: 'Claim annotations and history' }));
  await user.click(await screen.findByRole('button', { name: 'Add a claim' }));
  await user.type(screen.getByLabelText('Claim statement'), 'Private unfinished annotation');
  act(() => invalidateWorkspaceAccess());
  await waitFor(() =>
    expect(screen.queryByDisplayValue('Private unfinished annotation')).not.toBeInTheDocument(),
  );
  await waitFor(() => expect(screen.getByLabelText('Claim statement')).toHaveValue(''));
});
