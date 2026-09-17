import { render, screen } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';

import { aiPreview, aiTotals, teamId } from '@/test/fixtures.aiUsage';
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
        return HttpResponse.json(
          aiPreview({ observed: aiTotals({ used_requests: 3, used_tokens: 30 }) }),
        );
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
          : HttpResponse.json(aiPreview());
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

  it('names the model and spend for the previewed destination', async () => {
    server.use(
      http.get('/api/admin/ai-usage/preview', () =>
        HttpResponse.json(
          aiPreview({
            observed: aiTotals({
              used_requests: 9,
              used_tokens: 3000,
              used_input_tokens: 1000,
              used_output_tokens: 2000,
              estimated_cost: '0.0026',
            }),
            model: {
              policy: 'personal',
              profile_id: '55555555-5555-4555-8555-555555555555',
              profile_name: 'Luna personal',
              model: 'gpt-5.6-luna',
              provider: 'openai_compatible',
              reasoning_effort: 'max',
              mechanical_effort: 'medium',
              unavailable: null,
            },
          }),
        ),
      ),
    );
    const user = mount();
    await user.selectOptions(screen.getByLabelText('Charged to'), adminUser.id);
    await user.click(screen.getByRole('button', { name: 'Preview allowance' }));

    expect(await screen.findByText('gpt-5.6-luna')).toBeInTheDocument();
    expect(screen.getByText(/Personal override/)).toBeInTheDocument();
    expect(screen.getByText(/lowered to medium for mechanical work/)).toBeInTheDocument();
    expect(screen.getByText(/Estimated spend: USD 0.0026/)).toBeInTheDocument();
  });

  it('explains why a destination has no usable model instead of naming one', async () => {
    server.use(
      http.get('/api/admin/ai-usage/preview', () =>
        HttpResponse.json(
          aiPreview({
            model: {
              policy: null,
              profile_id: null,
              profile_name: '',
              model: '',
              provider: null,
              reasoning_effort: null,
              mechanical_effort: null,
              unavailable: 'No global model is assigned.',
            },
          }),
        ),
      ),
    );
    const user = mount();
    await user.selectOptions(screen.getByLabelText('Charged to'), adminUser.id);
    await user.click(screen.getByRole('button', { name: 'Preview allowance' }));

    expect(await screen.findByText(/No global model is assigned/)).toBeInTheDocument();
  });

  it('offers a limit for the previewed person or team', async () => {
    server.use(http.get('/api/admin/ai-usage/preview', () => HttpResponse.json(aiPreview())));
    const asked: [string, string][] = [];
    const user = userEvent.setup();
    render(
      <AiUsagePreview
        users={[adminUser]}
        teams={teams}
        onEditLimit={(scope, target) => asked.push([scope, target])}
      />,
    );
    await user.selectOptions(screen.getByLabelText('Charged to'), adminUser.id);
    await user.click(screen.getByRole('button', { name: 'Preview allowance' }));
    await user.click(await screen.findByRole('button', { name: 'Set a limit for this account' }));

    await user.selectOptions(screen.getByLabelText('Destination (optional)'), teamId);
    await user.click(screen.getByRole('button', { name: 'Preview allowance' }));
    await user.click(await screen.findByRole('button', { name: 'Set a limit for this team' }));
    expect(asked).toEqual([
      ['user', adminUser.id],
      ['team', teamId],
    ]);
  });
});
