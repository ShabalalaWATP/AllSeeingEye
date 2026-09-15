import { render, screen, waitFor, within } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';

import type { AiPolicy, AiPolicyInput } from '@/lib/api/aiUsage';
import { aiPolicy, policyId, teamId } from '@/test/fixtures.aiUsage';
import { adminUser } from '@/test/fixtures';
import { team } from '@/test/fixtures.teams';
import { apiError } from '@/test/handlers';
import { server } from '@/test/server';

import { AiUsagePolicies } from './AiUsagePolicies';

const teams = [{ ...team, id: teamId, name: 'Northern desk' }];
const teamPolicy = aiPolicy({
  id: '77777777-7777-4777-8777-777777777777',
  scope: 'team',
  target_id: teamId,
  request_limit: null,
  token_limit: null,
  revision: 4,
});

function setup(policies: AiPolicy[] = [aiPolicy(), teamPolicy]) {
  server.use(
    http.get('/api/admin/ai-usage/policies', () => HttpResponse.json(policies)),
    http.get('/api/admin/ai-usage/policies/:id/overrides', () => HttpResponse.json({ items: [] })),
  );
  const user = userEvent.setup();
  render(<AiUsagePolicies users={[adminUser]} teams={teams} />);
  return user;
}

async function row(label: string) {
  const table = await screen.findByRole('table', { name: 'Active AI allowance policies' });
  return within(within(table).getByText(label).closest('tr')!);
}

describe('AiUsagePolicies states', () => {
  it('retries after the policy list fails to load', async () => {
    let fail = true;
    server.use(
      http.get('/api/admin/ai-usage/policies', () =>
        fail ? apiError(500, 'server_error', 'Policies unavailable.') : HttpResponse.json([]),
      ),
    );
    const user = userEvent.setup();
    render(<AiUsagePolicies users={[adminUser]} teams={teams} />);
    expect(await screen.findByText('Policies unavailable.')).toBeInTheDocument();
    fail = false;
    await user.click(screen.getByRole('button', { name: 'Retry' }));
    expect(await screen.findByText(/No policies are active/)).toBeInTheDocument();
    expect(screen.queryByText('Policies unavailable.')).not.toBeInTheDocument();
  });

  it('shows unlimited limits and edits a policy in place', async () => {
    let body: AiPolicyInput | null = null;
    server.use(
      http.put(`/api/admin/ai-usage/policies/${teamPolicy.id}`, async ({ request }) => {
        body = (await request.json()) as AiPolicyInput;
        return HttpResponse.json({ ...teamPolicy, request_limit: 20, revision: 5 });
      }),
    );
    const user = setup();
    const teamRow = await row('Team · Northern desk');
    expect(teamRow.getAllByText('Unlimited')).toHaveLength(2);
    expect(teamRow.getByText('Revision 4')).toBeInTheDocument();
    await user.click(teamRow.getByRole('button', { name: 'Edit Team · Northern desk' }));
    expect(screen.getByLabelText('Team')).toHaveValue(teamId);
    await user.type(screen.getByLabelText('Requests'), '20');
    await user.click(screen.getByRole('button', { name: 'Save policy' }));

    expect(await screen.findByText('Revision 5')).toBeInTheDocument();
    expect(body).toMatchObject({ scope: 'team', target_id: teamId, request_limit: 20 });
    expect(screen.getByRole('button', { name: 'Add policy' })).toBeInTheDocument();
    expect(screen.getAllByRole('row')).toHaveLength(3);
  });

  it('cancels an edit and reports a failed save', async () => {
    server.use(
      http.put(`/api/admin/ai-usage/policies/${policyId}`, () =>
        apiError(409, 'conflict', 'The policy changed. Reload before saving.'),
      ),
    );
    const user = setup();
    const globalRow = await row('Everyone');
    await user.click(globalRow.getByRole('button', { name: 'Edit Everyone' }));
    await user.click(screen.getByRole('button', { name: 'Cancel' }));
    expect(screen.getByRole('button', { name: 'Add policy' })).toBeInTheDocument();

    await user.click(globalRow.getByRole('button', { name: 'Edit Everyone' }));
    await user.clear(screen.getByLabelText('Requests'));
    await user.type(screen.getByLabelText('Requests'), '11');
    await user.click(screen.getByRole('button', { name: 'Save policy' }));
    expect(await screen.findByText('The policy changed. Reload before saving.')).toBeVisible();
    expect(screen.getByLabelText('Requests')).toHaveValue('11');
  });

  it('disables a policy that is being edited and whose overrides are open', async () => {
    let disabled = '';
    server.use(
      http.delete('/api/admin/ai-usage/policies/:id', ({ params }) => {
        disabled = String(params.id);
        return new HttpResponse(null, { status: 204 });
      }),
    );
    const user = setup();
    const teamRow = await row('Team · Northern desk');
    await user.click(teamRow.getByRole('button', { name: 'Overrides for Team · Northern desk' }));
    await screen.findByRole('region', { name: 'Temporary overrides for Team · Northern desk' });
    await user.click(teamRow.getByRole('button', { name: 'Edit Team · Northern desk' }));
    await user.click(teamRow.getByRole('button', { name: 'Disable Team · Northern desk' }));

    await waitFor(() => {
      expect(screen.queryByText('Team · Northern desk')).not.toBeInTheDocument();
    });
    expect(disabled).toBe(teamPolicy.id);
    expect(screen.queryByRole('region', { name: /Temporary overrides/ })).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Add policy' })).toBeInTheDocument();
  });

  it('keeps one editor and its overrides open when disabling another policy', async () => {
    server.use(
      http.delete(
        '/api/admin/ai-usage/policies/:id',
        () => new HttpResponse(null, { status: 204 }),
      ),
    );
    const user = setup();
    const globalRow = await row('Everyone');
    await user.click(globalRow.getByRole('button', { name: 'Overrides for Everyone' }));
    await screen.findByRole('region', { name: 'Temporary overrides for Everyone' });
    await user.click(globalRow.getByRole('button', { name: 'Edit Everyone' }));
    const teamRow = await row('Team · Northern desk');
    await user.click(teamRow.getByRole('button', { name: 'Disable Team · Northern desk' }));
    await waitFor(() => {
      expect(screen.queryByText('Team · Northern desk')).not.toBeInTheDocument();
    });
    // Editing and overrides for the same policy must not collide and duplicate the editor.
    expect(screen.getAllByLabelText('Scope')).toHaveLength(1);
    expect(screen.getByLabelText('Requests')).toHaveValue('10');
    expect(screen.getByRole('button', { name: 'Save policy' })).toBeInTheDocument();
    expect(screen.getByRole('region', { name: 'Temporary overrides for Everyone' })).toBeVisible();

    await user.click(globalRow.getByRole('button', { name: 'Overrides for Everyone' }));
    expect(screen.queryByRole('region', { name: /Temporary overrides/ })).not.toBeInTheDocument();
  });

  it('reports a failed disable and keeps the policy listed', async () => {
    server.use(
      http.delete('/api/admin/ai-usage/policies/:id', () =>
        apiError(403, 'forbidden', 'Administrator MFA required.'),
      ),
    );
    const user = setup();
    const globalRow = await row('Everyone');
    await user.click(globalRow.getByRole('button', { name: 'Disable Everyone' }));
    expect(await screen.findByText('Administrator MFA required.')).toBeInTheDocument();
    expect(screen.getByText('Everyone', { selector: 'span' })).toBeInTheDocument();
  });
});
