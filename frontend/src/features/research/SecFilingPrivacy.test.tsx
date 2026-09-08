import { act, render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { expect, it, vi } from 'vitest';
import { server } from '@/test/server';
import { applySession } from '@/test/render';
import { plainUser, tokenFor } from '@/test/fixtures';
import { secPage, secChoice, secReceipt } from '@/test/fixtures.secFilings';
import { invalidateWorkspaceAccess } from '@/lib/workspaceAccess';
import { useAuthStore } from '@/stores/auth';
import { saveBinaryFile } from '@/lib/downloadBinary';
import { DocumentResearchInput } from './DocumentResearchInput';
vi.mock('@/lib/downloadBinary', () => ({ saveBinaryFile: vi.fn() }));
async function setup() {
  applySession('user');
  server.use(http.post('/api/research/sec/filings', () => HttpResponse.json(secPage())));
  const changed = vi.fn();
  const view = render(<DocumentResearchInput onChange={changed} />);
  await userEvent.click(screen.getByRole('button', { name: 'Find an SEC filing' }));
  fireEvent.change(screen.getByLabelText('SEC company identifier (CIK)'), {
    target: { value: '320193' },
  });
  await userEvent.click(screen.getByRole('button', { name: 'Discover SEC filings' }));
  await screen.findByText('Filing metadata, documents not imported yet');
  return { ...view, changed };
}
it('cancels an in-flight import, suppresses duplicate dispatch and ignores the late receipt', async () => {
  let finish: (() => void) | undefined;
  const pending = new Promise<void>((resolve) => {
    finish = resolve;
  });
  let count = 0;
  server.use(
    http.post('/api/research/sec/filings/:id/import', async () => {
      count++;
      await pending;
      return HttpResponse.json(secReceipt());
    }),
  );
  const { changed } = await setup();
  const button = screen.getByRole('button', { name: `Import document ${secChoice().accession}` });
  fireEvent.click(button);
  fireEvent.click(button);
  await waitFor(() => expect(count).toBe(1));
  await userEvent.click(screen.getByRole('button', { name: 'Cancel SEC request' }));
  await act(async () => {
    finish?.();
    await pending;
  });
  expect(screen.getByText('SEC request cancelled.')).toBeInTheDocument();
  expect(changed).not.toHaveBeenCalledWith(secReceipt().id);
});
it('clears metadata and attached IDs when access changes or the account switches', async () => {
  server.use(
    http.post('/api/research/sec/filings/:id/import', () => HttpResponse.json(secReceipt())),
  );
  const { changed } = await setup();
  await userEvent.click(
    screen.getByRole('button', { name: `Import document ${secChoice().accession}` }),
  );
  await screen.findByRole('heading', { name: 'Attached filing document: filing.htm' });
  act(() => invalidateWorkspaceAccess());
  expect(
    screen.queryByRole('heading', { name: 'Attached filing document: filing.htm' }),
  ).not.toBeInTheDocument();
  await waitFor(() => expect(changed).toHaveBeenLastCalledWith(null));
  await userEvent.click(screen.getByRole('button', { name: 'Find an SEC filing' }));
  fireEvent.change(screen.getByLabelText('SEC company identifier (CIK)'), {
    target: { value: '320193' },
  });
  act(() => useAuthStore.getState().setSession(tokenFor({ ...plainUser, id: 'another-user' })));
  expect(screen.queryByDisplayValue('320193')).not.toBeInTheDocument();
});
it('downloads only the imported opaque selection and saves original bytes as a local attachment', async () => {
  server.use(
    http.post('/api/research/sec/filings/:id/import', () => HttpResponse.json(secReceipt())),
    http.get('/api/research/sec/filings/:id/original', ({ params }) => {
      expect(params.id).toBe(secChoice().selection_id);
      return new HttpResponse('original filing bytes', {
        headers: { 'Content-Type': 'application/octet-stream' },
      });
    }),
  );
  await setup();
  expect(
    screen.queryByRole('button', { name: 'Download temporary original document' }),
  ).not.toBeInTheDocument();
  await userEvent.click(
    screen.getByRole('button', { name: `Import document ${secChoice().accession}` }),
  );
  await userEvent.click(
    await screen.findByRole('button', { name: 'Download temporary original document' }),
  );
  await waitFor(() =>
    expect(saveBinaryFile).toHaveBeenCalledWith(
      `sec-${secChoice().accession}-filing.htm`,
      expect.objectContaining({ type: 'application/octet-stream' }),
    ),
  );
});
it('aborts a pending download on account change and saves no file', async () => {
  let finish: (() => void) | undefined;
  const pending = new Promise<void>((resolve) => {
    finish = resolve;
  });
  let started = false;
  server.use(
    http.post('/api/research/sec/filings/:id/import', () => HttpResponse.json(secReceipt())),
    http.get('/api/research/sec/filings/:id/original', async () => {
      started = true;
      await pending;
      return new HttpResponse('original');
    }),
  );
  await setup();
  await userEvent.click(
    screen.getByRole('button', { name: `Import document ${secChoice().accession}` }),
  );
  await userEvent.click(
    await screen.findByRole('button', { name: 'Download temporary original document' }),
  );
  await waitFor(() => expect(started).toBe(true));
  act(() => useAuthStore.getState().setSession(tokenFor({ ...plainUser, id: 'another-user' })));
  await act(async () => {
    finish?.();
    await pending;
  });
  expect(saveBinaryFile).not.toHaveBeenCalled();
});
it('rejects an already expired imported input and clears discovery when switching attachment method', async () => {
  server.use(
    http.post('/api/research/sec/filings/:id/import', () =>
      HttpResponse.json(secReceipt({ expires_at: new Date(Date.now() - 1000).toISOString() })),
    ),
  );
  const { changed } = await setup();
  await userEvent.click(
    screen.getByRole('button', { name: `Import document ${secChoice().accession}` }),
  );
  await screen.findByText('The imported input has expired. Discover and import the filing again.');
  expect(
    screen.queryByRole('heading', { name: 'Attached filing document: filing.htm' }),
  ).not.toBeInTheDocument();
  expect(changed).toHaveBeenLastCalledWith(null);
  await userEvent.click(screen.getByRole('button', { name: 'Upload a document' }));
  expect(screen.queryByText('Filing metadata, documents not imported yet')).not.toBeInTheDocument();
  expect(screen.getByLabelText('Document or media')).toBeInTheDocument();
});
