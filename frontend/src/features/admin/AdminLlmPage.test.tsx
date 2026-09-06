import { screen, waitFor, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';

import { apiError } from '@/test/handlers';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';

import { binding, draft, installConnections, proof, team } from './llmTestFixtures';

async function openDraft(user: ReturnType<typeof renderApp>['user'], name = 'OpenAI Luna') {
  const region = await screen.findByRole('region', { name: 'Saved connection drafts' });
  const summary = within(region).getByText(name, { exact: false });
  await user.click(summary);
  return summary.closest('li')!;
}

describe('AI connections', () => {
  it('reuses one bound profile across teams and globally without editing it or re-entering credentials', async () => {
    const global = draft({
      id: '88888888-8888-4888-8888-888888888888',
      name: 'Current global',
      is_bound: true,
    });
    const shared = draft({
      is_bound: true,
      is_tested: true,
      tested_revision: 1,
      tested_config_hash: proof,
      tested_at: '2026-09-06T12:00:00Z',
    });
    const otherTeam = {
      ...team,
      id: '99999999-9999-4999-8999-999999999999',
      name: 'Southern desk',
    };
    const state = installConnections([global, shared], [binding(global), binding(shared, team.id)]);
    server.use(http.get('/api/teams', () => HttpResponse.json({ items: [team, otherTeam] })));
    const { user } = renderApp('/admin/llm', 'admin');
    const teams = await screen.findByRole('region', { name: 'Team AI overrides' });
    await user.click(within(teams).getByRole('button', { name: 'Reuse OpenAI Luna' }));
    const reused = screen.getByRole('region', { name: 'Reuse active connection' });
    expect(
      within(reused).queryByRole('button', { name: 'Edit OpenAI Luna' }),
    ).not.toBeInTheDocument();
    expect(
      within(reused).queryByRole('button', { name: 'Delete OpenAI Luna' }),
    ).not.toBeInTheDocument();
    expect(screen.queryByLabelText('API key')).not.toBeInTheDocument();
    await user.selectOptions(within(reused).getByLabelText('Apply OpenAI Luna to'), otherTeam.id);
    await user.click(within(reused).getByRole('button', { name: 'Review and apply' }));
    expect(
      within(reused).getByRole('group', { name: 'Confirm connection switch' }),
    ).toHaveTextContent('Shared feed translation keeps the global connection.');
    await user.click(within(reused).getByRole('button', { name: 'Confirm switch' }));
    await screen.findByText('Southern desk switched to gpt-5.6-luna.');
    expect(state.bindings.filter((item) => item.profile_id === shared.id)).toHaveLength(2);
    const reuseButton = within(
      screen.getByRole('region', { name: 'Team AI overrides' }),
    ).getAllByRole('button', { name: 'Reuse OpenAI Luna' })[0];
    if (reuseButton === undefined) throw new Error('Missing reuse action');
    await user.click(reuseButton);
    await user.click(screen.getByRole('button', { name: 'Close connection reuse' }));
    expect(
      screen.queryByRole('region', { name: 'Reuse active connection' }),
    ).not.toBeInTheDocument();
    await user.click(reuseButton);
    await user.click(screen.getByRole('button', { name: 'Test OpenAI Luna' }));
    await screen.findByText(/Connection test passed/);
    await user.click(screen.getByRole('button', { name: 'Review and apply' }));
    await user.click(screen.getByRole('button', { name: 'Confirm switch' }));
    await screen.findByText('Global connection switched to gpt-5.6-luna.');
    expect(state.bindings.every((item) => item.profile_id === shared.id)).toBe(true);
    expect(state.profiles).toHaveLength(2);
    expect(state.saves).toHaveLength(0);
  });
  it('shows only the first enabled legacy winner per role and identifies protected unused legacy profiles', async () => {
    const winner = draft({ enabled: true, roles: ['assessment'] });
    const later = draft({
      id: '88888888-8888-4888-8888-888888888888',
      name: 'Later profile',
      enabled: true,
      roles: ['assessment'],
    });
    installConnections([winner, later]);
    const { user } = renderApp('/admin/llm', 'admin');
    const global = await screen.findByRole('region', { name: 'Global AI connection' });
    expect(within(global).getByText('OpenAI Luna')).toBeVisible();
    expect(within(global).queryByText('Later profile')).not.toBeInTheDocument();
    const row = await openDraft(user, 'Later profile');
    expect(within(row).getByRole('button', { name: 'Edit Later profile' })).toBeDisabled();
    expect(within(row).getByText(/Apply a tested global replacement before editing/)).toBeVisible();
  });
  it('shows legacy active profiles without offering an in-place edit', async () => {
    installConnections([draft({ enabled: true, reasoning_effort: null })]);
    renderApp('/admin/llm', 'admin');
    expect(await screen.findByText('Current role-based connections')).toBeVisible();
    expect(screen.queryByRole('button', { name: 'Edit OpenAI Luna' })).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Replace OpenAI Luna' })).toBeVisible();
  });

  it('retries a failed load without making any provider requests', async () => {
    const state = installConnections();
    let failed = true;
    server.use(
      http.get('/api/admin/llm/connections', () =>
        failed
          ? apiError(503, 'unavailable', 'Connections unavailable.')
          : HttpResponse.json({ items: [] }),
      ),
    );
    const { user } = renderApp('/admin/llm', 'admin');
    expect(await screen.findByText('Connections unavailable.')).toBeVisible();
    failed = false;
    await user.click(screen.getByRole('button', { name: 'Retry' }));
    await screen.findByRole('region', { name: 'Saved connection drafts' });
    expect(state.models).toBe(0);
    expect(state.tests).toBe(0);
  });

  it('leaves routing unchanged when a concurrent switch invalidates confirmation', async () => {
    const current = draft({
      id: '88888888-8888-4888-8888-888888888888',
      name: 'Current global',
      is_bound: true,
    });
    const state = installConnections([current, draft()], [binding(current)]);
    server.use(
      http.put('/api/admin/llm/connections', () =>
        apiError(409, 'stale_binding', 'The connection changed.'),
      ),
    );
    const { user } = renderApp('/admin/llm', 'admin');
    const row = await openDraft(user);
    await user.click(within(row).getByRole('button', { name: 'Test OpenAI Luna' }));
    await within(row).findByText(/Connection test passed/);
    await user.click(within(row).getByRole('button', { name: 'Review and apply' }));
    await user.click(screen.getByRole('button', { name: 'Confirm switch' }));
    expect(await screen.findByText(/The connection changed/)).toBeVisible();
    expect(state.bindings[0]?.profile_id).toBe(current.id);
  });

  it('resets a team override to global only after explicit confirmation', async () => {
    const global = draft({
      id: '88888888-8888-4888-8888-888888888888',
      name: 'Current global',
      is_bound: true,
    });
    const override = draft({ is_bound: true });
    const state = installConnections(
      [global, override],
      [binding(global), binding(override, team.id)],
    );
    const { user } = renderApp('/admin/llm', 'admin');
    const region = await screen.findByRole('region', { name: 'Team AI overrides' });
    await user.click(within(region).getByRole('button', { name: 'Use global connection' }));
    expect(state.bindings).toHaveLength(2);
    await user.click(within(region).getByRole('button', { name: 'Keep override' }));
    expect(state.bindings).toHaveLength(2);
    await user.click(within(region).getByRole('button', { name: 'Use global connection' }));
    await user.click(within(region).getByRole('button', { name: 'Confirm use global' }));
    expect(await screen.findByText(`${team.name} now uses the global connection.`)).toBeVisible();
    expect(state.bindings).toHaveLength(1);
  });
  it('does not call the provider automatically and requires test, review and confirmation to apply globally', async () => {
    const state = installConnections();
    const { user } = renderApp('/admin/llm', 'admin');
    const row = await openDraft(user);
    expect(state.tests).toBe(0);
    expect(state.models).toBe(0);
    expect(state.applies).toHaveLength(0);
    expect(within(row).getByText('Stored key ending 1234', { exact: false })).toBeVisible();
    expect(within(row).queryByRole('button', { name: 'Review and apply' })).not.toBeInTheDocument();
    await user.click(within(row).getByRole('button', { name: 'Test OpenAI Luna' }));
    expect(await within(row).findByText(/Connection test passed/)).toBeVisible();
    expect(
      within(row).getByText(/Apply a global connection before adding team overrides/),
    ).toBeVisible();
    await user.click(within(row).getByRole('button', { name: 'Review and apply' }));
    expect(state.applies).toHaveLength(0);
    expect(screen.getByRole('button', { name: 'Confirm switch' })).toHaveFocus();
    expect(screen.getByText(/Existing team overrides keep their current connection/)).toBeVisible();
    await user.click(screen.getByRole('button', { name: 'Confirm switch' }));
    expect(await screen.findByText('Global connection switched to gpt-5.6-luna.')).toBeVisible();
    expect(state.applies).toEqual([
      {
        team_id: null,
        profile_id: draft().id,
        expected_profile_revision: 1,
        tested_config_hash: proof,
        expected_binding_revision: null,
      },
    ]);
    expect(
      within(screen.getByRole('region', { name: 'Global AI connection' })).getByText(
        '· max reasoning',
      ),
    ).toBeVisible();
    expect(screen.queryByRole('button', { name: 'Edit OpenAI Luna' })).not.toBeInTheDocument();
  });

  it('saves a write-only credential draft without activating or testing it', async () => {
    const state = installConnections([]);
    const { user } = renderApp('/admin/llm', 'admin');
    await screen.findByText('No saved drafts.');
    await user.click(screen.getByRole('button', { name: 'Configure connection' }));
    await user.type(screen.getByLabelText('API key'), 'synthetic-test-key');
    await user.click(screen.getByRole('button', { name: 'Save draft' }));
    expect(await screen.findByText(/OpenAI Luna saved/)).toBeVisible();
    expect(state.saves[0]).toMatchObject({
      model: 'gpt-5.6-luna',
      reasoning_effort: 'max',
      enabled: false,
      api_key: 'synthetic-test-key',
    });
    expect(state.tests).toBe(0);
    expect(state.models).toBe(0);
    expect(state.applies).toHaveLength(0);
    expect(screen.queryByLabelText('API key')).not.toBeInTheDocument();
  });

  it('loads account models explicitly and editing invalidates the previous test', async () => {
    const state = installConnections();
    const { user } = renderApp('/admin/llm', 'admin');
    const row = await openDraft(user);
    await user.click(within(row).getByRole('button', { name: 'Test OpenAI Luna' }));
    await within(row).findByText(/Connection test passed/);
    await user.click(within(row).getByRole('button', { name: 'Load models for OpenAI Luna' }));
    await within(row).findByText(/2 models returned by this account/);
    await user.click(within(row).getByRole('button', { name: 'Edit OpenAI Luna' }));
    await user.selectOptions(
      screen.getByLabelText('Models returned by this account'),
      'manual-alternative',
    );
    await user.click(screen.getByRole('button', { name: 'Save draft' }));
    await screen.findByText(/OpenAI Luna saved/);
    const updated = await openDraft(user);
    expect(within(updated).getByText('manual-alternative', { exact: false })).toBeVisible();
    expect(
      within(updated).queryByRole('button', { name: 'Review and apply' }),
    ).not.toBeInTheDocument();
    expect(state.saves[0]).not.toHaveProperty('api_key');
    expect(state.models).toBe(1);
  });

  it('never offers apply after failed testing and explains unavailable discovery', async () => {
    installConnections();
    server.use(
      http.post('/api/admin/llm/profiles/:id/test', () =>
        HttpResponse.json({
          ok: false,
          latency_ms: 30,
          model: null,
          error: 'The model rejected this configuration.',
          revision: null,
          tested_at: null,
          tested_config_hash: null,
        }),
      ),
      http.get('/api/admin/llm/profiles/:id/models', () =>
        apiError(502, 'discovery_failed', 'Model discovery unavailable.'),
      ),
    );
    const { user } = renderApp('/admin/llm', 'admin');
    const row = await openDraft(user);
    await user.click(within(row).getByRole('button', { name: 'Test OpenAI Luna' }));
    expect(await within(row).findByText(/Connection test failed/)).toBeVisible();
    expect(within(row).queryByRole('button', { name: 'Review and apply' })).not.toBeInTheDocument();
    await user.click(within(row).getByRole('button', { name: 'Load models for OpenAI Luna' }));
    expect(await within(row).findByText('Model discovery unavailable.')).toBeVisible();
  });

  it('shows the selected team before a switch and preserves the global binding', async () => {
    const global = draft({
      id: '88888888-8888-4888-8888-888888888888',
      name: 'Current global',
      is_bound: true,
    });
    const state = installConnections([global, draft()], [binding(global)]);
    const { user } = renderApp('/admin/llm', 'admin');
    const row = await openDraft(user);
    await user.click(within(row).getByRole('button', { name: 'Test OpenAI Luna' }));
    await within(row).findByText(/Connection test passed/);
    await user.selectOptions(within(row).getByLabelText('Apply OpenAI Luna to'), team.id);
    await user.click(within(row).getByRole('button', { name: 'Review and apply' }));
    expect(screen.getByRole('group', { name: 'Confirm connection switch' })).toHaveTextContent(
      team.name,
    );
    await user.click(screen.getByRole('button', { name: 'Keep current connection' }));
    expect(state.applies).toHaveLength(0);
    await user.click(within(row).getByRole('button', { name: 'Review and apply' }));
    await user.click(screen.getByRole('button', { name: 'Confirm switch' }));
    expect(await screen.findByText(`${team.name} switched to gpt-5.6-luna.`)).toBeVisible();
    expect(state.applies[0]?.team_id).toBe(team.id);
    expect(state.bindings.find((item) => item.team_id === null)?.profile_id).toBe(global.id);
  });

  it('uses a new draft for a bound connection replacement and requires the key again', async () => {
    const profile = draft({ is_bound: true });
    installConnections([profile], [binding(profile)]);
    const { user } = renderApp('/admin/llm', 'admin');
    await screen.findByText('No saved drafts.');
    await user.click(screen.getByRole('button', { name: 'Replace OpenAI Luna' }));
    expect(screen.getByLabelText('Connection name')).toHaveValue('OpenAI Luna replacement');
    expect(screen.getByLabelText('API key')).toBeRequired();
    expect(screen.getByLabelText('API key')).toHaveValue('');
    await user.click(screen.getByRole('button', { name: 'Cancel' }));
    expect(screen.queryByRole('form')).not.toBeInTheDocument();
  });

  it('deletes only an unbound draft after confirmation', async () => {
    const state = installConnections();
    const { user } = renderApp('/admin/llm', 'admin');
    const row = await openDraft(user);
    await user.click(within(row).getByRole('button', { name: 'Delete OpenAI Luna' }));
    expect(state.profiles).toHaveLength(1);
    await user.click(within(row).getByRole('button', { name: 'Confirm delete OpenAI Luna' }));
    await waitFor(() => expect(screen.getByText('No saved drafts.')).toBeVisible());
    expect(state.profiles).toHaveLength(0);
  });

  it('disables configuration if encryption is unavailable and handles loading failure', async () => {
    installConnections([]);
    server.use(
      http.get('/api/admin/llm/profiles', () =>
        HttpResponse.json({ items: [], encryption_available: false }),
      ),
    );
    renderApp('/admin/llm', 'admin');
    expect(await screen.findByText('Keys cannot be stored')).toBeVisible();
    expect(screen.getByRole('button', { name: 'Configure connection' })).toBeDisabled();
  });
});
