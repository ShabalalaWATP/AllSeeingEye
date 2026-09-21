import { screen, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';

import { renderApp } from '@/test/render';
import { server } from '@/test/server';

const failure = (message: string) =>
  HttpResponse.json({ error: { code: 'server_error', message } }, { status: 500 });

describe('reports page states', () => {
  it('shows errors for the products and the report list', async () => {
    server.use(
      http.get('/api/reports/templates', () => failure('Templates boom')),
      http.get('/api/reports', () => failure('Reports boom')),
    );
    renderApp('/research/saved?template=intsum', 'user');
    expect(await screen.findByText('Templates boom')).toBeInTheDocument();
    expect(await screen.findByText('Reports boom')).toBeInTheDocument();
    expect(screen.queryByRole('form', { name: 'Generate a report' })).not.toBeInTheDocument();
  });

  it('disables generation when there are no products', async () => {
    server.use(http.get('/api/reports/templates', () => HttpResponse.json({ items: [] })));
    renderApp('/research/saved?template=intsum', 'user');
    const form = await screen.findByRole('form', { name: 'Generate a report' });
    expect(within(form).getByRole('button', { name: 'Generate' })).toBeDisabled();
  });

  it('says so when there are no reports yet', async () => {
    server.use(
      http.get('/api/reports', () =>
        HttpResponse.json({ items: [], limit: 50, offset: 0, has_more: false }),
      ),
    );
    renderApp('/research/saved', 'user');
    expect(
      await screen.findByText('No saved research yet. Ask a question to create your first report.'),
    ).toBeInTheDocument();
  });
});
