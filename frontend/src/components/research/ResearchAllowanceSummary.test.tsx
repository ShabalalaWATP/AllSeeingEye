import { act, render, screen } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';

import { invalidateResearchUsage } from '@/lib/researchUsageEvents';
import { researchAllowance } from '@/test/fixtures.researchUsage';
import { apiError } from '@/test/handlers';
import { server } from '@/test/server';

import { ResearchAllowanceSummary } from './ResearchAllowanceSummary';

describe('ResearchAllowanceSummary', () => {
  it('shows remaining runs, reset time and what consumes an allowance', async () => {
    render(<ResearchAllowanceSummary />);
    expect(await screen.findByText('3 of 4 research runs remaining')).toBeInTheDocument();
    expect(screen.getByText(/Level 1 · 4 runs per week/)).toBeInTheDocument();
    expect(screen.getByText(/28 Sept? 2026, 00:00 UTC/)).toBeInTheDocument();
    expect(
      screen.getByText(/Manual research and subscription runs share this allowance/),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Browsing, map tools and feed refreshes do not count/),
    ).toBeInTheDocument();
  });

  it('refreshes after admitted work and when returning to the page', async () => {
    let used = 1;
    server.use(
      http.get('/api/research-usage/me', () =>
        HttpResponse.json(researchAllowance({ used, remaining: 4 - used })),
      ),
    );
    render(<ResearchAllowanceSummary />);
    await screen.findByText('3 of 4 research runs remaining');
    used = 2;
    act(() => invalidateResearchUsage());
    await screen.findByText('2 of 4 research runs remaining');
    used = 4;
    await act(() => window.dispatchEvent(new Event('focus')));
    expect(await screen.findByText('0 of 4 research runs remaining')).toBeInTheDocument();
    expect(screen.getByText(/Your research allowance is used/)).toBeInTheDocument();
  });

  it('explains lookup failures and offers a retry instead of claiming unlimited access', async () => {
    let failed = true;
    server.use(
      http.get('/api/research-usage/me', () =>
        failed
          ? apiError(503, 'unavailable', 'Allowance could not be loaded.')
          : HttpResponse.json(researchAllowance()),
      ),
    );
    const user = userEvent.setup();
    render(<ResearchAllowanceSummary />);
    expect(await screen.findByText('Allowance could not be loaded.')).toBeInTheDocument();
    failed = false;
    await user.click(screen.getByRole('button', { name: 'Retry research allowance' }));
    expect(await screen.findByText('3 of 4 research runs remaining')).toBeInTheDocument();
  });
});
