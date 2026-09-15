import { render, screen } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';

import { aiOverride, aiPage, aiPolicy, aiSummary, aiTotals } from '@/test/fixtures.aiUsage';
import { apiError } from '@/test/handlers';
import { server } from '@/test/server';

import { AiUsageSummary } from './AiUsageSummary';

describe('AiUsageSummary', () => {
  it('shows observed usage when no allowance policy is configured', async () => {
    server.use(
      http.get('/api/ai-usage/me', () =>
        HttpResponse.json(
          aiPage({
            observed: aiTotals({ used_requests: 3, used_tokens: 1200, unknown_requests: 1 }),
          }),
        ),
      ),
    );
    render(<AiUsageSummary />);
    expect(
      await screen.findByText(/3 requests, 1,200 tokens this month, 1 with unconfirmed usage/),
    ).toBeInTheDocument();
    expect(screen.getByText(/usage is recorded without a limit/)).toBeInTheDocument();
  });

  it('uses the effective override limit and warns when an allowance is exhausted', async () => {
    server.use(
      http.get('/api/ai-usage/me', () =>
        HttpResponse.json(
          aiPage({
            items: [
              aiSummary({
                policy: aiPolicy({ scope: 'user', target_id: aiPolicy().id }),
                request_limit: 0,
                override: aiOverride(),
                remaining_requests: 0,
              }),
            ],
          }),
        ),
      ),
    );
    render(<AiUsageSummary />);
    expect(await screen.findByText('Blocked')).toBeInTheDocument();
    expect(screen.getByText(/Temporary override until/)).toBeInTheDocument();
    expect(screen.getByRole('status')).toHaveTextContent('nearly or fully used');
    expect(screen.getByRole('heading', { name: /Personal · month allowance/ })).toBeInTheDocument();
  });

  it('reports a failure and retries on request', async () => {
    let calls = 0;
    server.use(
      http.get('/api/ai-usage/me', () => {
        calls += 1;
        return calls === 1
          ? apiError(503, 'unavailable', 'Usage is unavailable.')
          : HttpResponse.json(aiPage({ items: [aiSummary()] }));
      }),
    );
    const user = userEvent.setup();
    render(<AiUsageSummary />);
    await user.click(await screen.findByRole('button', { name: 'Retry' }));
    expect(await screen.findByText('1 / 10')).toBeInTheDocument();
    expect(screen.getByRole('progressbar', { name: 'Tokens used' })).toHaveAttribute(
      'aria-valuenow',
      '10',
    );
  });
});
