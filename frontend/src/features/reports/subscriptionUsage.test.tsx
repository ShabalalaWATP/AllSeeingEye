import { screen, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { expect, it } from 'vitest';

import { schedule } from '@/test/fixtures';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';

const secondId = 'e3e3e3e3-e3e3-4e3e-8e3e-e3e3e3e3e3e3';

it('shows owner and selected subscription UTC-month usage without implying currency spend', async () => {
  server.use(
    http.get('/api/schedules', () =>
      HttpResponse.json({
        items: [schedule, { ...schedule, id: secondId, name: 'Second update' }],
      }),
    ),
    http.get('/api/schedules/usage', () =>
      HttpResponse.json({
        scope: 'owner',
        subscription_id: null,
        month_start: '2026-09-01T00:00:00Z',
        month_end: '2026-10-01T00:00:00Z',
        policy_version: 'subscription-monthly-budget-v1',
        used: { requests: 3, output_tokens: 1234 },
        limit: { requests: 800, output_tokens: 24_000_000 },
      }),
    ),
    http.get('/api/schedules/:id/usage', ({ params }) =>
      HttpResponse.json({
        scope: 'subscription',
        subscription_id: params.id,
        month_start: '2026-09-01T00:00:00Z',
        month_end: '2026-10-01T00:00:00Z',
        policy_version: 'subscription-monthly-budget-v1',
        used: { requests: params.id === secondId ? 2 : 1, output_tokens: 500 },
        limit: { requests: 240, output_tokens: 8_000_000 },
      }),
    ),
  );
  const { user } = renderApp('/research/recurring', 'user');
  const panel = within(await screen.findByRole('region', { name: 'Monthly AI provider usage' }));
  expect(await panel.findByText(/3 of 800 model requests/)).toBeVisible();
  expect(await panel.findByText(/1 of 240 model requests/)).toBeVisible();
  expect(panel.getByText(/^Resets .* UTC/)).toBeVisible();
  expect(panel.getByText(/not complete research runs or currency/)).toBeVisible();
  await user.selectOptions(panel.getByLabelText('Subscription usage'), secondId);
  expect(await panel.findByText(/2 of 240 model requests/)).toBeVisible();
  expect(panel.queryByText(/1 of 240 model requests/)).not.toBeInTheDocument();
});
