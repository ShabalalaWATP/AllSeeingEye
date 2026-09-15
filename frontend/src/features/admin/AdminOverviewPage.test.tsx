import { screen, waitFor, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';

import { aiPolicy, aiSummary, aiTotals } from '@/test/fixtures.aiUsage';
import { adminUser, llmProfiles, source, sourceHealth } from '@/test/fixtures';
import { apiError } from '@/test/handlers';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';

const card = (name: string) => screen.findByRole('article', { name });

describe('AdminOverviewPage', () => {
  it('summarises each area with links to the owning pages', async () => {
    renderApp('/admin', 'admin');
    const requests = await card('Account requests');
    expect(await within(requests).findByText('Nia Newcomer')).toBeVisible();
    expect(within(requests).getByText('Awaiting decision')).toBeVisible();
    expect(within(requests).getByRole('link', { name: 'Account requests' })).toHaveAttribute(
      'href',
      '/admin/requests',
    );

    const users = await card('Users');
    expect(await within(users).findByText('active accounts')).toBeVisible();
    expect(within(users).getByText('One active administrator')).toBeVisible();
    expect(within(users).getByText('No teams yet.')).toBeVisible();
    expect(within(users).getByRole('link', { name: 'Teams' })).toHaveAttribute(
      'href',
      '/admin/teams',
    );

    const sources = await card('Sources');
    expect(await within(sources).findByText('sources live')).toBeVisible();
    expect(within(sources).getByText('1 failing')).toBeVisible();
    expect(within(sources).getByText('GDACS disaster alerts')).toBeVisible();
    expect(within(sources).getByText('3 failed polls')).toBeVisible();

    const ai = await card('AI connections');
    expect(await within(ai).findByText('Role-based connections in use')).toBeVisible();

    const usage = await card('AI usage');
    expect(await within(usage).findByText('Recording only')).toBeVisible();

    const audit = await card('Audit log');
    expect(await within(audit).findByText('Login succeeded')).toBeVisible();

    const security = await card('Security');
    expect(await within(security).findByText('No factor enrolled')).toBeVisible();
    expect(within(security).getByText('No factors enrolled.')).toBeVisible();
  });

  it('shows clear queues, healthy feeds, allowances and enrolled factors', async () => {
    server.use(
      http.get('/api/admin/account-requests', () => HttpResponse.json({ items: [] })),
      http.get('/api/admin/users', () =>
        HttpResponse.json({ items: [adminUser, { ...adminUser, id: 'second-admin' }] }),
      ),
      http.get('/api/teams', () =>
        HttpResponse.json({
          items: [
            {
              id: '44444444-4444-4444-8444-444444444444',
              name: 'Desk',
              is_active: true,
              created_by: adminUser.id,
              created_at: '2026-09-01T00:00:00Z',
              updated_at: '2026-09-01T00:00:00Z',
              description: null,
            },
          ],
        }),
      ),
      http.get('/api/admin/sources', () => HttpResponse.json({ items: [source()] })),
      http.get('/api/admin/llm/profiles', () =>
        HttpResponse.json({
          items: [{ ...llmProfiles[0], is_bound: true, is_tested: false }],
          encryption_available: false,
        }),
      ),
      http.get('/api/admin/llm/connections', () =>
        HttpResponse.json({
          items: [
            {
              team_id: null,
              user_id: null,
              profile_id: llmProfiles[0]?.id,
              profile_revision: 1,
              tested_config_hash: 'hash',
              activated_at: '2026-09-01T00:00:00Z',
              activated_by: adminUser.id,
              revision: 1,
            },
          ],
        }),
      ),
      http.get('/api/admin/ai-usage/preview', () =>
        HttpResponse.json({
          items: [aiSummary({ policy: aiPolicy(), used_requests: 9 })],
          observed: aiTotals({ used_requests: 3 }),
          unknown_calls: 1,
        }),
      ),
      http.get('/api/admin/audit-log', () => HttpResponse.json({ items: [], next_before: null })),
      http.get('/api/auth/mfa', () =>
        HttpResponse.json({
          methods: ['authenticator', 'email'],
          available_methods: [],
          required: true,
        }),
      ),
    );
    renderApp('/admin', 'admin');
    expect(await within(await card('Account requests')).findByText('Queue clear')).toBeVisible();
    expect(await within(await card('Users')).findByText('2 administrators')).toBeVisible();
    expect(within(await card('Users')).getByText('1 active team.')).toBeVisible();
    expect(await within(await card('Sources')).findByText('No failing feeds')).toBeVisible();
    const ai = await card('AI connections');
    expect(await within(ai).findByText('Global connection needs a test')).toBeVisible();
    expect(within(ai).getByText('Key storage unavailable')).toBeVisible();
    const usage = await card('AI usage');
    expect(await within(usage).findByRole('progressbar', { name: 'Requests used' })).toBeVisible();
    expect(within(usage).getByText(/Unconfirmed calls remain charged/)).toBeVisible();
    expect(
      await within(await card('Audit log')).findByText(/No administrative activity/),
    ).toBeVisible();
    const security = await card('Security');
    expect(await within(security).findByText('Protected')).toBeVisible();
    expect(within(security).getByText('Email code')).toBeVisible();
  });

  it('keeps other tiles working when one fails, and retries the failed tile', async () => {
    let attempts = 0;
    server.use(
      http.get('/api/admin/sources', () => {
        attempts += 1;
        return attempts === 1
          ? apiError(503, 'unavailable', 'Registry unavailable.')
          : HttpResponse.json({ items: [] });
      }),
      http.get('/api/admin/audit-log', () => apiError(403, 'forbidden', 'Admins only.')),
    );
    const { user } = renderApp('/admin', 'admin');
    const sources = await card('Sources');
    expect(await within(sources).findByRole('alert')).toHaveTextContent('Registry unavailable.');
    expect(await within(await card('Account requests')).findByText('Nia Newcomer')).toBeVisible();
    const audit = await card('Audit log');
    expect(await within(audit).findByText(/This session cannot view audit log/)).toBeVisible();
    expect(within(audit).queryByRole('button', { name: /Retry/ })).not.toBeInTheDocument();

    await user.click(within(sources).getByRole('button', { name: 'Retry sources' }));
    expect(await within(sources).findByText('No collection sources are registered.')).toBeVisible();
    expect(attempts).toBe(2);
  });

  it('refreshes every tile on request', async () => {
    let calls = 0;
    server.use(
      http.get('/api/admin/account-requests', () => {
        calls += 1;
        return HttpResponse.json({ items: [] });
      }),
    );
    const { user } = renderApp('/admin', 'admin');
    expect(await within(await card('Account requests')).findByText('Queue clear')).toBeVisible();
    await user.click(screen.getByRole('button', { name: 'Refresh overview' }));
    await waitFor(() => expect(calls).toBe(2));
    expect(await within(await card('Account requests')).findByText('Queue clear')).toBeVisible();
    expect(screen.getByText('Signed in as', { exact: false })).toHaveTextContent(
      adminUser.display_name,
    );
  });

  it('flags blocked sources and a missing global connection', async () => {
    server.use(
      http.get('/api/admin/sources', () =>
        HttpResponse.json({
          items: [
            source({
              id: 'blocked',
              name: 'Blocked feed',
              environment_disabled: true,
              health: sourceHealth({ status: 'disabled', last_error: null }),
            }),
          ],
        }),
      ),
      http.get('/api/admin/llm/profiles', () =>
        HttpResponse.json({ items: [], encryption_available: true }),
      ),
    );
    renderApp('/admin', 'admin');
    const sources = await card('Sources');
    expect(await within(sources).findByText('Blocked feed')).toBeVisible();
    expect(within(sources).getByText('Blocked')).toBeVisible();
    const ai = await card('AI connections');
    expect(await within(ai).findByText('No global connection')).toBeVisible();
  });
});
