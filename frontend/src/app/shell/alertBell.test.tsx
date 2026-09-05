import { screen, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';

import { useGlobeStore } from '@/stores/globe';
import { alert } from '@/test/fixtures';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';

describe('alert count and ops-room strip', () => {
  it('stays quiet when the count cannot be fetched or is zero', async () => {
    server.use(
      http.get('/api/warning/alerts', () =>
        HttpResponse.json({ error: { code: 'server_error', message: 'Boom' } }, { status: 500 }),
      ),
    );
    renderApp('/reports', 'user');
    const bell = await screen.findByRole('link', { name: 'Alerts' });
    expect(bell).toHaveAttribute('href', '/warning');
    server.use(
      http.get('/api/warning/alerts', () => HttpResponse.json({ items: [], unacknowledged: 0 })),
    );
    renderApp('/reports', 'user');
    expect(await screen.findByRole('link', { name: 'Alerts, 0 unacknowledged' })).toBeVisible();
  });

  it('shows three alerts on the wall and counts the rest', async () => {
    const many = [1, 2, 3, 4].map((n) => ({
      ...alert,
      id: `${String(n)}1111111-1111-4111-8111-111111111111`,
      title: `Alert ${String(n)}`,
      summary: n === 4 ? '' : alert.summary,
    }));
    server.use(
      http.get('/api/warning/alerts', () =>
        HttpResponse.json({ items: many, unacknowledged: many.length }),
      ),
    );
    useGlobeStore.setState({ opsRoom: true });
    renderApp('/', 'user');
    const strip = await screen.findByRole('complementary', { name: 'Unacknowledged alerts' });
    expect(within(strip).getByText('Alert 1')).toBeInTheDocument();
    expect(within(strip).queryByText('Alert 4')).not.toBeInTheDocument();
    expect(within(strip).getByText('1 more on the warning page')).toBeInTheDocument();
    useGlobeStore.setState({ opsRoom: false });
  });
});
