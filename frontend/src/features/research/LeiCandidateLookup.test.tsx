import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { expect, it, vi } from 'vitest';
import { server } from '@/test/server';
import { LeiCandidateLookup } from './LeiCandidateLookup';

it('discloses public search and waits for explicit search and candidate confirmation', async () => {
  const search = vi.fn();
  const confirm = vi.fn();
  server.use(
    http.post('/api/research/lei-candidates', async ({ request }) => {
      search(await request.json());
      return HttpResponse.json({
        items: [
          { lei: '5493001KJTIIGC8Y1R12', name: 'Example', jurisdiction: 'GB', status: 'ACTIVE' },
          {
            lei: '5493001KJTIIGC8Y1R13',
            name: 'Example Two',
            jurisdiction: 'US',
            status: 'ACTIVE',
          },
        ],
      });
    }),
  );
  render(<LeiCandidateLookup initialName="Example" disabled={false} confirm={confirm} />);
  expect(screen.getByText(/typed company name.*optional country to GLEIF/)).toBeInTheDocument();
  fireEvent.change(screen.getByLabelText('Company name for GLEIF'), {
    target: { value: 'Example Ltd' },
  });
  expect(search).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole('button', { name: 'Search GLEIF' }));
  await screen.findByRole('button', { name: 'Confirm Example (5493001KJTIIGC8Y1R12)' });
  expect(search).toHaveBeenCalledWith({ name: 'Example Ltd', country: null });
  expect(confirm).not.toHaveBeenCalled();
  fireEvent.click(
    screen.getByRole('button', { name: 'Confirm Example Two (5493001KJTIIGC8Y1R13)' }),
  );
  expect(confirm).toHaveBeenCalledWith('5493001KJTIIGC8Y1R13');
  await waitFor(() =>
    expect(
      screen.queryByText('Example Two · US · ACTIVE · 5493001KJTIIGC8Y1R13'),
    ).not.toBeInTheDocument(),
  );
});

it('shows empty results without selecting an identifier', async () => {
  server.use(http.post('/api/research/lei-candidates', () => HttpResponse.json({ items: [] })));
  const confirm = vi.fn();
  render(<LeiCandidateLookup initialName="Missing" disabled={false} confirm={confirm} />);
  fireEvent.click(screen.getByRole('button', { name: 'Search GLEIF' }));
  expect(await screen.findByRole('status')).toHaveTextContent('No candidates');
  expect(confirm).not.toHaveBeenCalled();
});
