import { act, render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { expect, it, vi } from 'vitest';
import { server } from '@/test/server';
import { applySession } from '@/test/render';
import { secPage, secChoice, secReceipt } from '@/test/fixtures.secFilings';
import { DocumentResearchInput } from './DocumentResearchInput';
async function setup() {
  applySession('user');
  const changed = vi.fn();
  render(<DocumentResearchInput onChange={changed} />);
  await userEvent.click(screen.getByRole('button', { name: 'Find an SEC filing' }));
  fireEvent.change(screen.getByLabelText('SEC company identifier (CIK)'), {
    target: { value: '320193' },
  });
  return changed;
}
it('cancels discovery and ignores its late metadata without double dispatch', async () => {
  let finish: (() => void) | undefined;
  const pending = new Promise<void>((resolve) => {
    finish = resolve;
  });
  let count = 0;
  server.use(
    http.post('/api/research/sec/filings', async () => {
      count++;
      await pending;
      return HttpResponse.json(secPage());
    }),
  );
  await setup();
  const button = screen.getByRole('button', { name: 'Discover SEC filings' });
  fireEvent.click(button);
  fireEvent.click(button);
  await waitFor(() => expect(count).toBe(1));
  await userEvent.click(screen.getByRole('button', { name: 'Cancel SEC request' }));
  await act(async () => {
    finish?.();
    await pending;
  });
  expect(screen.queryByText('Filing metadata, documents not imported yet')).not.toBeInTheDocument();
});
it('surfaces failed document extraction and supports an explicit import retry', async () => {
  let fail = true;
  server.use(
    http.post('/api/research/sec/filings', () => HttpResponse.json(secPage())),
    http.post('/api/research/sec/filings/:id/import', () =>
      fail
        ? HttpResponse.json(
            {
              error: {
                code: 'invalid_request',
                message: 'The primary document could not be extracted.',
              },
            },
            { status: 422 },
          )
        : HttpResponse.json(secReceipt()),
    ),
  );
  const changed = await setup();
  await userEvent.click(screen.getByRole('button', { name: 'Discover SEC filings' }));
  await userEvent.click(
    await screen.findByRole('button', { name: `Import document ${secChoice().accession}` }),
  );
  await screen.findByText('The primary document could not be extracted.');
  expect(changed).not.toHaveBeenCalledWith(secReceipt().id);
  fail = false;
  await userEvent.click(
    screen.getByRole('button', { name: `Import document ${secChoice().accession}` }),
  );
  await screen.findByRole('heading', { name: 'Attached filing document: filing.htm' });
  await userEvent.click(screen.getByRole('button', { name: 'Find an SEC filing' }));
  expect(changed).toHaveBeenLastCalledWith(secReceipt().id);
  await userEvent.click(screen.getByRole('button', { name: 'Remove filing attachment' }));
  expect(changed).toHaveBeenLastCalledWith(null);
});
it('preserves the imported research input when an original download is cancelled', async () => {
  let finish: (() => void) | undefined;
  const pending = new Promise<void>((resolve) => {
    finish = resolve;
  });
  server.use(
    http.post('/api/research/sec/filings', () => HttpResponse.json(secPage())),
    http.post('/api/research/sec/filings/:id/import', () => HttpResponse.json(secReceipt())),
    http.get('/api/research/sec/filings/:id/original', async () => {
      await pending;
      return new HttpResponse('original');
    }),
  );
  const changed = await setup();
  await userEvent.click(screen.getByRole('button', { name: 'Discover SEC filings' }));
  await userEvent.click(
    await screen.findByRole('button', { name: `Import document ${secChoice().accession}` }),
  );
  await userEvent.click(
    await screen.findByRole('button', { name: 'Download temporary original document' }),
  );
  await userEvent.click(screen.getByRole('button', { name: 'Cancel SEC request' }));
  await act(async () => {
    finish?.();
    await pending;
  });
  expect(
    screen.getByRole('heading', { name: 'Attached filing document: filing.htm' }),
  ).toBeInTheDocument();
  expect(changed).toHaveBeenLastCalledWith(secReceipt().id);
});
