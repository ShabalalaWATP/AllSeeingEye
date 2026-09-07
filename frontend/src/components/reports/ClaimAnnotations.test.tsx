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
  expect(screen.queryByLabelText('Claim statement')).not.toBeInTheDocument();
});

it('keeps a draft while pagination, generation and another editor are locked', async () => {
  server.use(
    http.get('/api/claims', () =>
      HttpResponse.json({ items: [], total: 21, limit: 20, offset: 0 }),
    ),
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
  await user.type(screen.getByLabelText('Claim statement'), 'Keep this research draft');
  expect(screen.getByRole('button', { name: 'Next page' })).toBeDisabled();
  expect(screen.getByRole('button', { name: 'Generate proposed claims' })).toBeDisabled();
  expect(screen.getByRole('button', { name: 'Add a claim' })).toBeDisabled();
  expect(screen.getByLabelText('Claim statement')).toHaveValue('Keep this research draft');
  await user.click(screen.getByRole('button', { name: 'Cancel' }));
  expect(screen.getByRole('button', { name: 'Next page' })).toBeEnabled();
  expect(screen.getByRole('button', { name: 'Generate proposed claims' })).toBeEnabled();
});

it('prevents opening a draft or changing pages during generation and releases after failure', async () => {
  let finish: (() => void) | undefined;
  const pending = new Promise<void>((resolve) => {
    finish = resolve;
  });
  server.use(
    http.get('/api/claims', () =>
      HttpResponse.json({ items: [], total: 21, limit: 20, offset: 0 }),
    ),
    http.post('/api/claims/generate', async () => {
      await pending;
      return HttpResponse.json(
        { error: { code: 'unavailable', message: 'Provider unavailable.' } },
        { status: 503 },
      );
    }),
  );
  render(<ClaimAnnotations reportId="report-1" version={1} canCreate />);
  const user = userEvent.setup();
  await user.click(screen.getByRole('button', { name: 'Claim annotations and history' }));
  await user.click(await screen.findByRole('button', { name: 'Generate proposed claims' }));
  const add = screen.getByRole('button', { name: 'Add a claim' });
  const next = screen.getByRole('button', { name: 'Next page' });
  const locked = [add.hasAttribute('disabled'), next.hasAttribute('disabled')];
  await act(async () => {
    finish?.();
    await pending;
  });
  await screen.findByText('Provider unavailable.');
  expect(locked).toEqual([true, true]);
  expect(screen.getByRole('button', { name: 'Add a claim' })).toBeEnabled();
  expect(screen.getByRole('button', { name: 'Next page' })).toBeEnabled();
});
