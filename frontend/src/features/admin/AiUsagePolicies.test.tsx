import { render, screen, within } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';

import type { AiOverrideInput, AiPolicyInput } from '@/lib/api/aiUsage';
import {
  aiOverride,
  aiPolicy,
  aiSummary,
  aiTotals,
  policyId,
  teamId,
} from '@/test/fixtures.aiUsage';
import { adminUser } from '@/test/fixtures';
import { server } from '@/test/server';

import { AiUsagePolicies } from './AiUsagePolicies';

const team = {
  id: teamId,
  name: 'Northern desk',
  is_active: true,
  created_by: adminUser.id,
  created_at: '2026-09-01T00:00:00Z',
  updated_at: '2026-09-01T00:00:00Z',
  description: null,
};

function setup(policies = [aiPolicy()]) {
  server.use(http.get('/api/admin/ai-usage/policies', () => HttpResponse.json(policies)));
  const user = userEvent.setup();
  render(<AiUsagePolicies users={[adminUser]} teams={[team]} />);
  return user;
}

describe('AiUsagePolicies', () => {
  it('lists active policies and creates a system work policy without a target', async () => {
    let body: AiPolicyInput | null = null;
    server.use(
      http.post('/api/admin/ai-usage/policies', async ({ request }) => {
        body = (await request.json()) as AiPolicyInput;
        return HttpResponse.json(
          aiPolicy({
            id: '66666666-6666-4666-8666-666666666666',
            scope: 'system',
            request_limit: 0,
          }),
          { status: 201 },
        );
      }),
    );
    const user = setup([aiPolicy(), aiPolicy({ id: policyId.replace('1', '9'), enabled: false })]);
    const table = await screen.findByRole('table', { name: 'Active AI allowance policies' });
    expect(within(table).getAllByRole('row')).toHaveLength(2);
    await user.selectOptions(screen.getByLabelText('Scope'), 'system');
    expect(screen.queryByLabelText('Team')).not.toBeInTheDocument();
    await user.type(screen.getByLabelText('Requests'), '0');
    await user.click(screen.getByRole('button', { name: 'Add policy' }));
    expect(await within(table).findByText('System work')).toBeInTheDocument();
    expect(body).toEqual({
      scope: 'system',
      period: 'month',
      request_limit: 0,
      token_limit: null,
      enabled: true,
    });
  });

  it('rejects malformed limits and requires a team target before saving', async () => {
    const user = setup([]);
    await screen.findByText(/No policies are active/);
    await user.type(screen.getByLabelText('Tokens'), '1.5');
    await user.click(screen.getByRole('button', { name: 'Add policy' }));
    expect(await screen.findByText(/Limits must be whole numbers/)).toBeInTheDocument();
    await user.clear(screen.getByLabelText('Tokens'));
    await user.selectOptions(screen.getByLabelText('Scope'), 'team');
    await user.click(screen.getByRole('button', { name: 'Add policy' }));
    expect(await screen.findByText(/Choose the user or team/)).toBeInTheDocument();
  });

  it('adds a dated blocked override and revokes it', async () => {
    let created: AiOverrideInput | null = null;
    server.use(
      http.get(`/api/admin/ai-usage/policies/${policyId}/overrides`, () =>
        HttpResponse.json({ items: [] }),
      ),
      http.post(`/api/admin/ai-usage/policies/${policyId}/overrides`, async ({ request }) => {
        created = (await request.json()) as AiOverrideInput;
        return HttpResponse.json(aiOverride(), { status: 201 });
      }),
      http.delete('/api/admin/ai-usage/overrides/:id', () =>
        HttpResponse.json(aiOverride({ revoked_at: '2026-09-02T00:00:00Z' })),
      ),
    );
    const user = setup();
    await user.click(await screen.findByRole('button', { name: 'Overrides for Everyone' }));
    const panel = screen.getByRole('region', { name: 'Temporary overrides for Everyone' });
    await within(panel).findByText('No overrides recorded.');
    await user.selectOptions(within(panel).getByLabelText('Request override'), 'blocked');
    await user.click(within(panel).getByRole('button', { name: 'Add override' }));
    const list = await within(panel).findByRole('list', { name: 'Recorded overrides' });
    expect(list).toHaveTextContent('Requests Blocked · Tokens Keep policy limit');
    expect(created).toMatchObject({ requests: { state: 'blocked' }, tokens: { state: 'inherit' } });
    await user.click(within(list).getByRole('button', { name: 'Revoke' }));
    expect(await within(list).findByText(/revoked/)).toBeInTheDocument();
  });

  it('previews system work with unconfirmed calls', async () => {
    let query = '';
    server.use(
      http.get('/api/admin/ai-usage/preview', ({ request }) => {
        query = new URL(request.url).search;
        return HttpResponse.json({
          items: [aiSummary({ policy: aiPolicy({ scope: 'system' }) })],
          observed: aiTotals({ used_requests: 7, used_tokens: 700 }),
          unknown_calls: 2,
        });
      }),
    );
    const user = setup();
    await screen.findByRole('table', { name: 'Active AI allowance policies' });
    await user.selectOptions(screen.getByLabelText('Charged to'), '__system__');
    expect(screen.getByLabelText('Destination (optional)')).toBeDisabled();
    await user.click(screen.getByRole('button', { name: 'Preview allowance' }));
    expect(await screen.findByText(/2 provider calls have unconfirmed usage/)).toBeInTheDocument();
    expect(screen.getByText(/7 requests, 700 tokens this month/)).toBeInTheDocument();
    expect(query).toBe('?system=true');
  });
});
