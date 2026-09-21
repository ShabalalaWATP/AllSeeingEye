import { screen, waitFor } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';

import { researchAllowance } from '@/test/fixtures.researchUsage';
import { apiError } from '@/test/handlers';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';

describe('research allowance admission', () => {
  it('shows the server reset explanation, preserves the question and refreshes a stale allowance', async () => {
    let rejected = false;
    const message = 'Your research allowance is used. It resets on 28 September at 00:00 UTC.';
    server.use(
      http.get('/api/research-usage/me', () =>
        HttpResponse.json(researchAllowance(rejected ? { used: 4, remaining: 0 } : {})),
      ),
      http.post('/api/report-jobs', () => {
        rejected = true;
        return apiError(429, 'research_usage_limit', message, undefined, { 'Retry-After': '3600' });
      }),
    );
    const { user, router } = renderApp('/research?question=What%20changed%3F', 'user');
    expect(await screen.findByText('3 of 4 research runs remaining')).toBeVisible();
    const start = await screen.findByRole('button', { name: 'Start research' });
    await waitFor(() => expect(start).toBeEnabled());
    await user.click(start);
    expect(await screen.findByRole('alert')).toHaveTextContent(message);
    expect(await screen.findByText('0 of 4 research runs remaining')).toBeVisible();
    expect(screen.getByLabelText('Your question')).toHaveValue('What changed?');
    expect(router.state.location.pathname).toBe('/research');
  });
});
