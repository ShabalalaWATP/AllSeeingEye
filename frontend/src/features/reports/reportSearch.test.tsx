import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { MemoryRouter } from 'react-router';
import { describe, expect, it } from 'vitest';

import { reportSummary } from '@/test/fixtures';
import { apiError } from '@/test/handlers';
import { applySession } from '@/test/render';
import { server } from '@/test/server';

import { ReportSearch } from './ReportSearch';

const available = { available: true, indexed: 1, total: 1, limit: 1000, batch_size: 8 };

function renderSearch() {
  applySession('user');
  render(
    <MemoryRouter>
      <ReportSearch />
    </MemoryRouter>,
  );
  return userEvent.setup();
}

describe('Semantic report search', () => {
  it('explains the missing model without making an embeddings call', async () => {
    server.use(
      http.get('/api/report-search', () => HttpResponse.json({ ...available, available: false })),
    );
    renderSearch();
    expect(
      await screen.findByText(/An administrator can enable a model profile/),
    ).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Search reports' })).not.toBeInTheDocument();
  });

  it('indexes only when requested and renders semantic scores and version links', async () => {
    let indexed = 0;
    let searchBody: unknown;
    server.use(
      http.get('/api/report-search', () => HttpResponse.json({ ...available, indexed })),
      http.post('/api/report-search/index', () => {
        indexed = 1;
        return HttpResponse.json(available);
      }),
      http.post('/api/report-search/query', async ({ request }) => {
        searchBody = await request.json();
        return HttpResponse.json({
          items: [{ report: reportSummary, score: 0.87 }],
          indexed: 1,
          total: 1,
        });
      }),
    );
    const user = renderSearch();
    await user.click(await screen.findByRole('button', { name: 'Index next 8 reports' }));
    expect(await screen.findByText(/1 of 1 current saved reports indexed/)).toBeInTheDocument();
    await user.type(screen.getByLabelText('Report search'), 'Merchant shipping');
    await user.click(screen.getByRole('button', { name: 'Search reports' }));
    expect(await screen.findByText('Similarity 0.87')).toBeInTheDocument();
    expect(
      screen.getByRole('link', { name: /Intelligence summary: Ukraine, version 1/ }),
    ).toHaveAttribute('href', `/reports/${reportSummary.id}`);
    expect(searchBody).toEqual({ query: 'Merchant shipping', limit: 10 });
  });

  it('handles missing reports, availability retry and query errors', async () => {
    server.use(
      http.get('/api/report-search', () => apiError(503, 'unavailable', 'Try again later.')),
    );
    const user = renderSearch();
    expect(await screen.findByText(/Try again later/)).toBeInTheDocument();
    server.use(
      http.get('/api/report-search', () =>
        HttpResponse.json({ ...available, indexed: 0, total: 0 }),
      ),
    );
    await user.click(screen.getByRole('button', { name: 'Retry search availability' }));
    expect(await screen.findByText(/Generate a report before/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Search reports' })).toBeDisabled();
  });

  it('shows indexing failures, rate limits and a cleared empty result', async () => {
    server.use(
      http.get('/api/report-search', () => HttpResponse.json({ ...available, total: 2 })),
      http.post('/api/report-search/index', () =>
        apiError(400, 'invalid_request', 'Embeddings unavailable.'),
      ),
      http.post('/api/report-search/query', () => apiError(429, 'rate_limited', 'Slow down.')),
    );
    const user = renderSearch();
    await user.click(await screen.findByRole('button', { name: 'Index next 8 reports' }));
    expect(await screen.findByText('Embeddings unavailable.')).toBeInTheDocument();
    await user.type(screen.getByLabelText('Report search'), 'Ships');
    await user.click(screen.getByRole('button', { name: 'Search reports' }));
    expect(await screen.findByText(/Too many attempts/)).toBeInTheDocument();
    server.use(
      http.post('/api/report-search/query', () =>
        HttpResponse.json({ items: [], indexed: 0, total: 2 }),
      ),
    );
    await waitFor(() =>
      expect(screen.getByRole('button', { name: 'Search reports' })).toBeEnabled(),
    );
    await user.click(screen.getByRole('button', { name: 'Search reports' }));
    expect(await screen.findByText(/No indexed reports are available/)).toBeInTheDocument();
    expect(screen.queryByText(/Too many attempts/)).not.toBeInTheDocument();
  });
});
