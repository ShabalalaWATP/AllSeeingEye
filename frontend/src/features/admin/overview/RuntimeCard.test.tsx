import { screen, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';

import { runtimeHealth } from '@/test/handlers.runtime';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';

describe('Runtime health card', () => {
  it('shows completed-cycle freshness and cumulative stream drops', async () => {
    const { user } = renderApp('/admin', 'admin');
    const card = await screen.findByRole('article', { name: 'Runtime health' });
    expect(await within(card).findByText('Workers are current')).toBeVisible();
    expect(within(card).getByText('Stream drops since restart')).toBeVisible();
    expect(within(card).getByText('7')).toBeVisible();
    await user.click(within(card).getByText('Worker freshness (1)'));
    expect(within(card).getByText('scheduler')).toBeVisible();
    expect(within(card).getByText('Current')).toBeVisible();
  });

  it('distinguishes a stalled worker from provider errors', async () => {
    server.use(
      http.get('/api/admin/runtime', () =>
        HttpResponse.json({
          ...runtimeHealth,
          ready: false,
          workers: [{ ...runtimeHealth.workers[0], name: 'scheduler', overdue: true }],
        }),
      ),
    );
    const { user } = renderApp('/admin', 'admin');
    const card = await screen.findByRole('article', { name: 'Runtime health' });
    expect(await within(card).findByText('Readiness degraded')).toBeVisible();
    await user.click(within(card).getByText('Worker freshness (1)'));
    expect(within(card).getByText('Overdue')).toBeVisible();
  });
});
