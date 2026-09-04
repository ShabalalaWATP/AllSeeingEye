import { screen } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';

import { auditPageOne, auditPageTwo } from '@/test/fixtures';
import { apiError } from '@/test/handlers';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';

import { summariseDetails } from './AdminAuditPage';

describe('AdminAuditPage', () => {
  it('lists entries and loads more with the next_before cursor', async () => {
    const seen: (string | null)[] = [];
    server.use(
      http.get('/api/admin/audit-log', ({ request }) => {
        const url = new URL(request.url);
        seen.push(url.searchParams.get('before'));
        expect(url.searchParams.get('limit')).toBe('100');
        return url.searchParams.get('before') === null
          ? HttpResponse.json({ items: auditPageOne, next_before: 118 })
          : HttpResponse.json({ items: auditPageTwo, next_before: null });
      }),
    );
    const { user } = renderApp('/admin/audit', 'admin');
    expect(await screen.findByText('login_succeeded')).toBeInTheDocument();
    expect(screen.getByText('{"note":"entry 119"}')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Load more' }));
    expect(await screen.findByText('login_failed')).toBeInTheDocument();
    expect(screen.getByText('login_succeeded')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Load more' })).not.toBeInTheDocument();
    expect(seen).toEqual([null, '118']);
  });

  it('shows the empty state', async () => {
    server.use(
      http.get('/api/admin/audit-log', () => HttpResponse.json({ items: [], next_before: null })),
    );
    renderApp('/admin/audit', 'admin');
    expect(await screen.findByText('No audit entries yet.')).toBeInTheDocument();
  });

  it('shows load errors', async () => {
    server.use(http.get('/api/admin/audit-log', () => apiError(403, 'forbidden', 'Admins only.')));
    renderApp('/admin/audit', 'admin');
    expect(await screen.findByRole('alert')).toHaveTextContent('Admins only.');
  });

  it('summarises details as truncated plain text', () => {
    expect(summariseDetails({})).toBe('');
    expect(summariseDetails({ a: 1 })).toBe('{"a":1}');
    const long = summariseDetails({ text: 'x'.repeat(200) });
    expect(long).toHaveLength(120);
    expect(long.endsWith('...')).toBe(true);
  });
});
