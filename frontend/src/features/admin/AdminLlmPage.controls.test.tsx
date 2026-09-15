import { screen, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';

import { plainUser } from '@/test/fixtures';
import { apiError } from '@/test/handlers';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';

import { binding, draft, installConnections, team } from './llmTestFixtures';

const globalProfile = draft({
  id: '88888888-8888-4888-8888-888888888888',
  name: 'Current global',
  is_bound: true,
});

describe('AI connections controls', () => {
  it('opens and closes allowance controls even when connections fail to load', async () => {
    installConnections();
    server.use(
      http.get('/api/admin/llm/connections', () =>
        apiError(503, 'unavailable', 'Connections unavailable.'),
      ),
      http.get('/api/admin/ai-usage/policies', () => HttpResponse.json([])),
    );
    const { user } = renderApp('/admin/llm', 'admin');
    expect(await screen.findByText('Connections unavailable.')).toBeVisible();
    await user.click(screen.getByRole('button', { name: 'Open allowance controls' }));
    expect(await screen.findByText(/No policies are active/)).toBeVisible();
    // Without loaded accounts the preview offers only the placeholder and system work.
    expect(within(screen.getByLabelText('Charged to')).getAllByRole('option')).toHaveLength(2);

    await user.click(screen.getByRole('button', { name: 'Close allowance controls' }));
    expect(screen.queryByRole('region', { name: 'AI access and usage' })).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Open allowance controls' })).toBeVisible();
  });

  it('explains a failed team reset and keeps the override', async () => {
    const override = draft({ is_bound: true });
    const state = installConnections(
      [globalProfile, override],
      [binding(globalProfile), binding(override, team.id)],
    );
    server.use(
      http.delete('/api/admin/llm/connections/team/:id', () =>
        apiError(409, 'stale_binding', 'The team connection changed.'),
      ),
    );
    const { user } = renderApp('/admin/llm', 'admin');
    const region = await screen.findByRole('region', { name: 'Team AI overrides' });
    await user.click(within(region).getByRole('button', { name: 'Use global connection' }));
    await user.click(within(region).getByRole('button', { name: 'Confirm use global' }));
    expect(
      await screen.findByText(/The team connection changed\. Refresh the connections/),
    ).toBeVisible();
    expect(state.bindings).toHaveLength(2);
  });

  it('resets a personal override to global and reports a failed personal reset', async () => {
    const personal = draft({ is_bound: true });
    const state = installConnections(
      [globalProfile, personal],
      [binding(globalProfile), { ...binding(personal), user_id: plainUser.id }],
    );
    let fail = true;
    server.use(
      http.delete('/api/admin/llm/connections/user/:id', ({ params }) => {
        if (fail) return apiError(409, 'stale_binding', 'The personal connection changed.');
        state.bindings = state.bindings.filter((item) => item.user_id !== params.id);
        return new HttpResponse(null, { status: 204 });
      }),
    );
    const { user } = renderApp('/admin/llm', 'admin');
    const region = await screen.findByRole('region', { name: 'Personal AI overrides' });
    await user.click(within(region).getByRole('button', { name: 'Use global connection' }));
    await user.click(within(region).getByRole('button', { name: 'Confirm personal reset' }));
    expect(await screen.findByText(/The personal connection changed\. Refresh/)).toBeVisible();
    expect(state.bindings).toHaveLength(2);

    fail = false;
    const refreshed = await screen.findByRole('region', { name: 'Personal AI overrides' });
    await user.click(within(refreshed).getByRole('button', { name: 'Use global connection' }));
    await user.click(within(refreshed).getByRole('button', { name: 'Confirm personal reset' }));
    expect(
      await screen.findByText('Personal workspace now uses the global connection.'),
    ).toBeVisible();
    expect(state.bindings).toHaveLength(1);
  });
});
