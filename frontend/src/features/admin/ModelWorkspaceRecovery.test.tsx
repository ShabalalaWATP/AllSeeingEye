import { screen, waitFor, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { beforeEach, expect, it } from 'vitest';

import { apiError } from '@/test/handlers';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';

import { binding, proof, team } from './llmTestFixtures';
import { mockModelSetupDialog } from './ModelSetupTestSupport';
import { installModelWorkspace, luna, sol } from './modelWorkspaceTestFixtures';

beforeEach(mockModelSetupDialog);

const unproven = () => ({
  ...luna,
  is_tested: false,
  tested_revision: null,
  tested_config_hash: null,
  tested_at: null,
});

it('retests an assigned model and uses the recovered proof for a new team assignment', async () => {
  const profile = unproven();
  const workspace = installModelWorkspace([profile, sol], [binding(profile)]);
  const { user } = renderApp('/admin/llm', 'admin');
  const card = await screen.findByRole('article', { name: 'Luna model card' });
  expect(
    within(screen.getByLabelText(`Model for ${team.name}`)).queryByRole('option', { name: 'Luna' }),
  ).not.toBeInTheDocument();
  expect(workspace.state.tests).toBe(0);
  await user.click(within(card).getByRole('button', { name: 'Test connection' }));
  await screen.findByText('Luna passed its connection test.');
  expect(workspace.state.tests).toBe(1);
  const models = screen.getByLabelText(`Model for ${team.name}`);
  expect(within(models).getByRole('option', { name: 'Luna' })).toBeEnabled();
  expect(within(card).queryByRole('button', { name: 'Test connection' })).not.toBeInTheDocument();
  expect(workspace.writes).toHaveLength(0);
  await user.selectOptions(models, luna.id);
  await user.click(screen.getByRole('button', { name: `Save ${team.name}` }));
  await screen.findByText('Assignments and limits saved. Model cards are up to date.');
  expect(workspace.writes[0]?.changes).toEqual([
    {
      scope: 'team',
      target_id: team.id,
      model: {
        profile_id: luna.id,
        expected_profile_revision: profile.revision,
        expected_binding_revision: null,
        tested_config_hash: proof,
      },
      allowance: null,
    },
  ]);
  expect(card).toHaveTextContent(team.name);
  expect(card).toHaveTextContent('Default');
});

it.each([
  {
    name: 'provider rejection',
    ok: false,
    revision: 1,
    hash: proof,
    error: 'The provider rejected this model.',
  },
  { name: 'stale revision', ok: true, revision: 2, hash: proof, error: null },
  { name: 'missing proof', ok: true, revision: 1, hash: null, error: null },
])(
  'keeps an assigned model unavailable after $name and permits a deliberate retry',
  async (outcome) => {
    const profile = unproven();
    const workspace = installModelWorkspace([profile, sol], [binding(profile)]);
    const before = structuredClone(workspace.state.bindings);
    let valid = false;
    let calls = 0;
    server.use(
      http.post('/api/admin/llm/profiles/:id/test', () => {
        calls++;
        return HttpResponse.json({
          ok: valid || outcome.ok,
          revision: valid ? profile.revision : outcome.revision,
          tested_config_hash: valid ? proof : outcome.hash,
          error: valid ? null : outcome.error,
          latency_ms: 12,
          model: profile.model,
          tested_at: '2026-09-17T12:00:00Z',
        });
      }),
    );
    const { user } = renderApp('/admin/llm', 'admin');
    const card = await screen.findByRole('article', { name: 'Luna model card' });
    await user.click(within(card).getByRole('button', { name: 'Test connection' }));
    expect(await screen.findByRole('alert')).toHaveTextContent(
      outcome.error ?? 'The current configuration did not pass its test.',
    );
    expect(
      within(screen.getByLabelText(`Model for ${team.name}`)).queryByRole('option', {
        name: 'Luna',
      }),
    ).not.toBeInTheDocument();
    expect(
      within(screen.getByLabelText('Model for Global / site')).getByRole('option', {
        name: 'Luna · test required',
      }),
    ).toBeDisabled();
    expect(workspace.state.bindings).toEqual(before);
    expect(workspace.writes).toHaveLength(0);
    expect(within(card).getByRole('button', { name: 'Test connection' })).toBeEnabled();
    valid = true;
    await user.click(within(card).getByRole('button', { name: 'Test connection' }));
    await screen.findByText('Luna passed its connection test.');
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    expect(
      within(screen.getByLabelText(`Model for ${team.name}`)).getByRole('option', { name: 'Luna' }),
    ).toBeEnabled();
    expect(calls).toBe(2);
    expect(workspace.state.bindings).toEqual(before);
  },
);

it('keeps an unused card and its slot after removal fails, then removes it only after a retry', async () => {
  const workspace = installModelWorkspace();
  let fail = true;
  let calls = 0;
  server.use(
    http.delete('/api/admin/llm/profiles/:id', ({ params }) => {
      calls++;
      if (fail)
        return apiError(409, 'conflict', 'The model is now assigned. Refresh before removing it.');
      workspace.state.profiles = workspace.state.profiles.filter(
        (profile) => profile.id !== params.id,
      );
      return new HttpResponse(null, { status: 204 });
    }),
  );
  const { user } = renderApp('/admin/llm', 'admin');
  const card = await screen.findByRole('article', { name: 'Sol model card' });
  await user.click(within(card).getByRole('button', { name: 'Remove' }));
  await user.click(within(card).getByRole('button', { name: 'Confirm removal' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('The model is now assigned.');
  expect(card).toBeVisible();
  expect(screen.getByText(/2 of 5 connections/)).toBeVisible();
  expect(workspace.state.profiles).toHaveLength(2);
  await user.click(within(card).getByRole('button', { name: 'Cancel' }));
  expect(within(card).queryByRole('button', { name: 'Confirm removal' })).not.toBeInTheDocument();
  expect(calls).toBe(1);
  fail = false;
  await user.click(within(card).getByRole('button', { name: 'Remove' }));
  await user.click(within(card).getByRole('button', { name: 'Confirm removal' }));
  await screen.findByText('Saved model removed. A model slot is now available.');
  expect(screen.queryByRole('article', { name: 'Sol model card' })).not.toBeInTheDocument();
  expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  expect(screen.getByText(/1 of 5 connections/)).toBeVisible();
  expect(workspace.state.bindings).toEqual([binding(luna)]);
});

it('switches the global default and resets a team override while keeping both cards in sync', async () => {
  const workspace = installModelWorkspace([luna, sol], [binding(luna), binding(luna, team.id)]);
  const { user } = renderApp('/admin/llm', 'admin');
  const previous = await screen.findByRole('article', { name: 'Luna model card' });
  const replacement = screen.getByRole('article', { name: 'Sol model card' });
  expect(previous).toHaveTextContent('Default');
  expect(previous).toHaveTextContent(team.name);
  await user.selectOptions(screen.getByLabelText('Model for Global / site'), sol.id);
  await user.click(screen.getByRole('button', { name: 'Save Global / site' }));
  await waitFor(() => expect(replacement).toHaveTextContent('Default'));
  expect(previous).toHaveTextContent('Assigned');
  expect(previous).not.toHaveTextContent('Everyone without an override');
  expect(previous).toHaveTextContent(team.name);
  expect(screen.getByLabelText(`Model for ${team.name}`)).toHaveValue(luna.id);
  await user.selectOptions(screen.getByLabelText(`Model for ${team.name}`), '');
  await user.click(screen.getByRole('button', { name: `Save ${team.name}` }));
  await waitFor(() => expect(previous).toHaveTextContent('Ready to assign to users or teams.'));
  expect(previous).not.toHaveTextContent(team.name);
  expect(replacement).toHaveTextContent('Default');
  expect(screen.getByLabelText(`Model for ${team.name}`)).toHaveValue('');
  expect(
    within(screen.getByLabelText(`Model for ${team.name}`)).getByRole('option', {
      name: 'Use default (Sol)',
    }),
  ).toBeInTheDocument();
  expect(workspace.writes[1]?.changes).toEqual([
    {
      scope: 'team',
      target_id: team.id,
      model: {
        profile_id: null,
        expected_binding_revision: 1,
        expected_profile_revision: null,
        tested_config_hash: null,
      },
      allowance: null,
    },
  ]);
  expect(workspace.state.bindings).toHaveLength(1);
  expect(workspace.state.bindings[0]?.profile_id).toBe(sol.id);
  expect(within(previous).getByRole('button', { name: 'Remove' })).toBeEnabled();
  expect(within(replacement).queryByRole('button', { name: 'Remove' })).not.toBeInTheDocument();
});

it('offers setup from an empty workspace without sending automatic provider requests', async () => {
  const workspace = installModelWorkspace([], []);
  const { user } = renderApp('/admin/llm', 'admin');
  const add = await screen.findByRole('button', { name: '+ Connect your first model' });
  expect(screen.getByText(/0 of 5 connections/)).toBeVisible();
  expect(screen.queryByRole('article')).not.toBeInTheDocument();
  expect(screen.getByLabelText(`Model for ${team.name}`)).toBeDisabled();
  await user.click(add);
  expect(screen.getByRole('dialog', { name: 'New model connection' })).toBeVisible();
  expect(screen.getByLabelText('Connection name')).toHaveValue('');
  expect(workspace.state.models).toBe(0);
  expect(workspace.state.tests).toBe(0);
  expect(workspace.state.saves).toHaveLength(0);
  expect(workspace.writes).toHaveLength(0);
  await user.click(screen.getByRole('button', { name: 'Close model setup' }));
  expect(add).toHaveFocus();
});
