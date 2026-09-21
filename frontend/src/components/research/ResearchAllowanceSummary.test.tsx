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
  it.each([
    [0, '0 runs recorded today (UTC)'],
    [1, '1 run recorded today (UTC)'],
    [37, '37 runs recorded today (UTC)'],
  ] as const)(
    'shows unlimited research with %i recorded runs and no allowance reset or exhausted state',
    async (used, recorded) => {
      server.use(
        http.get('/api/research-usage/me', () =>
          HttpResponse.json(
            researchAllowance({
              tier: 5,
              label: 'Level 5',
              limit: null,
              remaining: null,
              used,
              period: 'day',
            }),
          ),
        ),
      );
      render(<ResearchAllowanceSummary />);
      expect(await screen.findByText('Level 5 · Unlimited research runs')).toBeInTheDocument();
      expect(screen.getByText('No limit on research runs.')).toBeInTheDocument();
      expect(screen.getByText(recorded)).toBeInTheDocument();
      expect(screen.getByText(/AI provider limits also apply/)).toBeInTheDocument();
      expect(
        screen.queryByText(/remaining|Resets|Your research allowance is used/),
      ).not.toBeInTheDocument();
      expect(screen.queryByText(/null/)).not.toBeInTheDocument();
    },
  );

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
