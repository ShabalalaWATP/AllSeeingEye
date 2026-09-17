import { render, screen, within } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';

import { aiPolicy, aiSummary, aiTotals, teamId, teamUsage } from '@/test/fixtures.aiUsage';
import { server } from '@/test/server';

import { TeamAiUsage } from './TeamAiUsage';

async function open() {
  const user = userEvent.setup();
  render(<TeamAiUsage teamId={teamId} />);
  await user.click(screen.getByText('AI allowance'));
}

describe('TeamAiUsage', () => {
  it('loads on first open and shows a member only their own attributed usage', async () => {
    let calls = 0;
    server.use(
      http.get(`/api/teams/${teamId}/ai-usage`, () => {
        calls += 1;
        return HttpResponse.json(teamUsage());
      }),
    );
    await open();
    expect(await screen.findByText(/2 requests, 40 tokens this month/)).toBeInTheDocument();
    expect(screen.queryByText(/Whole team/)).not.toBeInTheDocument();
    expect(screen.queryByRole('table')).not.toBeInTheDocument();
    expect(screen.getByText(/usage is recorded only/)).toBeInTheDocument();
    expect(calls).toBe(1);
  });

  it('shows Managers the team aggregate, allowance and member totals', async () => {
    server.use(
      http.get(`/api/teams/${teamId}/ai-usage`, () =>
        HttpResponse.json(
          teamUsage({
            view: 'manager',
            items: [aiSummary({ policy: aiPolicy({ scope: 'team', target_id: teamId }) })],
            team: aiTotals({ used_requests: 5, used_tokens: 900 }),
            members: [
              {
                user_id: '55555555-5555-4555-8555-555555555555',
                display_name: 'Ada Analyst',
                observed: aiTotals({
                  used_requests: 4,
                  used_tokens: 860,
                  used_input_tokens: 60,
                  used_output_tokens: 800,
                  estimated_cost: '0.0010',
                }),
              },
            ],
          }),
        ),
      ),
    );
    await open();
    expect(await screen.findByText(/5 requests, 900 tokens this month/)).toBeInTheDocument();
    const table = screen.getByRole('table', { name: 'AI usage by team member this month' });
    const row = within(table).getByText('Ada Analyst').closest('tr');
    expect(row).toHaveTextContent('860');
    expect(row).toHaveTextContent('USD 0.0010');
    expect(screen.getByRole('heading', { name: /Team · month allowance/ })).toBeInTheDocument();
  });

  it('shows a readable error when the team is unavailable', async () => {
    server.use(
      http.get(`/api/teams/${teamId}/ai-usage`, () =>
        HttpResponse.json({ error: { code: 'not_found', message: 'Not found.' } }, { status: 404 }),
      ),
    );
    await open();
    expect(await screen.findByText(/Not found/)).toBeInTheDocument();
  });
});
