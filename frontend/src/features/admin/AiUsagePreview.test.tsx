import { render, screen } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';

import { aiTotals, teamId } from '@/test/fixtures.aiUsage';
import { adminUser } from '@/test/fixtures';
import { team } from '@/test/fixtures.teams';
import { apiError } from '@/test/handlers';
import { server } from '@/test/server';

import { AiUsagePreview } from './AiUsagePreview';

const teams = [{ ...team, id: teamId, name: 'Northern desk' }];

function mount() {
  const user = userEvent.setup();
  render(<AiUsagePreview users={[adminUser]} teams={teams} />);
  return user;
}

describe('AiUsagePreview', () => {
  it('needs an account before previewing', () => {
    mount();
    expect(screen.getByRole('button', { name: 'Preview allowance' })).toBeDisabled();
  });

  it('previews an account in a team destination with no applicable policy', async () => {
    let query = '';
    server.use(
      http.get('/api/admin/ai-usage/preview', ({ request }) => {
        query = new URL(request.url).search;
        return HttpResponse.json({
          items: [],
          observed: aiTotals({ used_requests: 3, used_tokens: 30 }),
          unknown_calls: 0,
        });
      }),
    );
    const user = mount();
    await user.selectOptions(screen.getByLabelText('Charged to'), adminUser.id);
    await user.selectOptions(screen.getByLabelText('Destination (optional)'), teamId);
    await user.click(screen.getByRole('button', { name: 'Preview allowance' }));

    expect(
      await screen.findByText('No active policy applies to this destination.'),
    ).toBeInTheDocument();
    expect(screen.queryByRole('status')).not.toBeInTheDocument();
    expect(query).toBe(`?user_id=${adminUser.id}&team_id=${teamId}`);

    await user.selectOptions(screen.getByLabelText('Destination (optional)'), '');
    expect(
      screen.queryByText('No active policy applies to this destination.'),
    ).not.toBeInTheDocument();
  });

  it('previews a personal workspace and clears the result after a failure', async () => {
    let fail = false;
    let query = '';
    server.use(
      http.get('/api/admin/ai-usage/preview', ({ request }) => {
        query = new URL(request.url).search;
        return fail
          ? apiError(404, 'not_found', 'Account not found.')
          : HttpResponse.json({ items: [], observed: aiTotals(), unknown_calls: 0 });
      }),
    );
    const user = mount();
    await user.selectOptions(screen.getByLabelText('Charged to'), adminUser.id);
    await user.click(screen.getByRole('button', { name: 'Preview allowance' }));
    expect(await screen.findByText(/No active policy applies/)).toBeInTheDocument();
    expect(query).toBe(`?user_id=${adminUser.id}`);

    fail = true;
    await user.click(screen.getByRole('button', { name: 'Preview allowance' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Account not found.');
    expect(screen.queryByText(/No active policy applies/)).not.toBeInTheDocument();
  });
});
