import { render, screen, within } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';

import type { AiOverride, AiOverrideInput } from '@/lib/api/aiUsage';
import { aiOverride, aiPolicy, policyId } from '@/test/fixtures.aiUsage';
import { apiError } from '@/test/handlers';
import { server } from '@/test/server';

import { AiPolicyOverrides } from './AiPolicyOverrides';

const overridesPath = `/api/admin/ai-usage/policies/${policyId}/overrides`;

function mount(items: AiOverride[] = []) {
  server.use(http.get(overridesPath, () => HttpResponse.json({ items })));
  const user = userEvent.setup();
  render(<AiPolicyOverrides policy={aiPolicy()} label="Everyone" />);
  return user;
}

async function setDates(user: ReturnType<typeof userEvent.setup>, from: string, until: string) {
  const starts = screen.getByLabelText('Starts');
  const expires = screen.getByLabelText('Expires');
  await user.clear(starts);
  if (from) await user.type(starts, from);
  await user.clear(expires);
  if (until) await user.type(expires, until);
}

describe('AiPolicyOverrides', () => {
  it('shows recorded limits and hides revoke for revoked overrides', async () => {
    mount([
      aiOverride({
        requests: { state: 'limit', value: 0 },
        tokens: { state: 'limit', value: 250 },
      }),
      aiOverride({
        id: '55555555-3333-4333-8333-333333333333',
        requests: { state: 'unlimited', value: null },
        revoked_at: '2026-09-03T00:00:00Z',
      }),
    ]);
    const list = await screen.findByRole('list', { name: 'Recorded overrides' });
    const [active, revoked] = within(list).getAllByRole('listitem');
    expect(active).toHaveTextContent('Requests Blocked (0) · Tokens 250');
    expect(within(active!).getByRole('button', { name: 'Revoke' })).toBeInTheDocument();
    expect(revoked).toHaveTextContent('Requests Unlimited · Tokens Keep policy limit');
    expect(revoked).toHaveTextContent('· revoked');
    expect(within(revoked!).queryByRole('button', { name: 'Revoke' })).not.toBeInTheDocument();
  });

  it('reports a failure to load overrides without a loading note', async () => {
    server.use(
      http.get(overridesPath, () => apiError(403, 'forbidden', 'Administrator MFA required.')),
    );
    render(<AiPolicyOverrides policy={aiPolicy()} label="Everyone" />);
    expect(await screen.findByRole('alert')).toHaveTextContent('Administrator MFA required.');
    expect(screen.queryByText('Loading overrides')).not.toBeInTheDocument();
  });

  it('requires explicit limits to be whole numbers', async () => {
    const user = mount();
    await screen.findByText('No overrides recorded.');
    await user.selectOptions(screen.getByLabelText('Request override'), 'limit');
    await user.click(screen.getByRole('button', { name: 'Add override' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('must be a whole number');

    await user.type(screen.getByLabelText('Request limit'), '5');
    await user.selectOptions(screen.getByLabelText('Token override'), 'limit');
    await user.type(screen.getByLabelText('Token limit'), '2.5');
    await user.click(screen.getByRole('button', { name: 'Add override' }));
    expect(screen.getByRole('alert')).toHaveTextContent('must be a whole number');
  });

  it('requires an end time after the start time', async () => {
    const user = mount();
    await screen.findByText('No overrides recorded.');
    await setDates(user, '2026-09-10T10:00', '2026-09-10T09:00');
    await user.click(screen.getByRole('button', { name: 'Add override' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Choose an end time after');

    await setDates(user, '', '2026-09-10T09:00');
    await user.click(screen.getByRole('button', { name: 'Add override' }));
    expect(screen.getByRole('alert')).toHaveTextContent('Choose an end time after');
  });

  it('creates explicit limit overrides and prepends them', async () => {
    let body: AiOverrideInput | null = null;
    server.use(
      http.post(overridesPath, async ({ request }) => {
        body = (await request.json()) as AiOverrideInput;
        return HttpResponse.json(
          aiOverride({
            id: '66666666-3333-4333-8333-333333333333',
            requests: { state: 'limit', value: 12 },
            tokens: { state: 'unlimited', value: null },
          }),
          { status: 201 },
        );
      }),
    );
    const user = mount([aiOverride()]);
    await screen.findByRole('list', { name: 'Recorded overrides' });
    await user.selectOptions(screen.getByLabelText('Request override'), 'limit');
    await user.type(screen.getByLabelText('Request limit'), '12');
    await user.selectOptions(screen.getByLabelText('Token override'), 'unlimited');
    await setDates(user, '2026-09-10T10:00', '2026-09-11T10:00');
    await user.click(screen.getByRole('button', { name: 'Add override' }));

    const list = screen.getByRole('list', { name: 'Recorded overrides' });
    expect(await within(list).findByText(/Requests 12 · Tokens Unlimited/)).toBeInTheDocument();
    expect(within(list).getAllByRole('listitem')[0]).toHaveTextContent('Requests 12');
    expect(body).toMatchObject({
      requests: { state: 'limit', value: 12 },
      tokens: { state: 'unlimited' },
      effective_from: new Date('2026-09-10T10:00').toISOString(),
      expires_at: new Date('2026-09-11T10:00').toISOString(),
    });
  });

  it('reports failures to create or revoke an override', async () => {
    server.use(
      http.post(overridesPath, () => apiError(422, 'invalid_request', 'Override overlaps.')),
      http.delete('/api/admin/ai-usage/overrides/:id', () =>
        apiError(404, 'not_found', 'Override not found.'),
      ),
    );
    const user = mount([aiOverride()]);
    const list = await screen.findByRole('list', { name: 'Recorded overrides' });
    await user.click(screen.getByRole('button', { name: 'Add override' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Override overlaps.');
    expect(within(list).getAllByRole('listitem')).toHaveLength(1);

    await user.click(within(list).getByRole('button', { name: 'Revoke' }));
    expect(await screen.findByText('Override not found.')).toBeInTheDocument();
    expect(within(list).getByRole('button', { name: 'Revoke' })).toBeInTheDocument();
  });
});
