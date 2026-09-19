import { screen, within } from '@testing-library/react';
import { beforeEach, describe, expect, it } from 'vitest';
import { http, HttpResponse } from 'msw';
import { plainUser } from '@/test/fixtures';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';
import { binding, draft, team } from './llmTestFixtures';
import { mockModelSetupDialog } from './ModelSetupTestSupport';
import { installModelWorkspace, luna, sol } from './modelWorkspaceTestFixtures';

beforeEach(mockModelSetupDialog);

describe('Model workspace', () => {
  it('shows model cards and a matrix, and opens setup as a modal only on request', async () => {
    installModelWorkspace();
    const { user } = renderApp('/admin/llm', 'admin');
    expect(await screen.findByRole('article', { name: 'Luna model card' })).toHaveTextContent(
      'Default',
    );
    expect(screen.getByRole('article', { name: 'Sol model card' })).toHaveTextContent('Ready');
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Add model' }));
    expect(screen.getByRole('dialog', { name: 'New model connection' })).toBeVisible();
    expect(screen.getByLabelText('Connection name')).toBeVisible();
    expect(screen.queryByLabelText('API key')).not.toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Close model setup' }));
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Add model' })).toHaveFocus();
  });

  it('moves a person and their allowance atomically and updates both model cards', async () => {
    const workspace = installModelWorkspace(
      [luna, sol],
      [binding(luna), { ...binding(luna), user_id: plainUser.id }],
    );
    const { user } = renderApp('/admin/llm', 'admin');
    const oldCard = await screen.findByRole('article', { name: 'Luna model card' });
    expect(oldCard).toHaveTextContent(plainUser.display_name);
    await user.click(screen.getByRole('button', { name: /^Users/ }));
    await user.selectOptions(screen.getByLabelText(`Model for ${plainUser.display_name}`), sol.id);
    await user.selectOptions(
      screen.getByLabelText(`Daily allowance for ${plainUser.display_name}`),
      'standard',
    );
    await user.click(screen.getByRole('button', { name: `Save ${plainUser.display_name}` }));
    await screen.findByText('Assignments and limits saved. Model cards are up to date.');
    expect(workspace.writes).toHaveLength(1);
    expect(workspace.writes[0]?.changes).toMatchObject([
      {
        scope: 'user',
        target_id: plainUser.id,
        model: { profile_id: sol.id, expected_binding_revision: 1 },
        allowance: { preset: 'standard' },
      },
    ]);
    expect(oldCard).not.toHaveTextContent(plainUser.display_name);
    expect(screen.getByRole('article', { name: 'Sol model card' })).toHaveTextContent(
      plainUser.display_name,
    );
    expect(
      workspace.state.bindings.find((item) => !item.user_id && !item.team_id)?.profile_id,
    ).toBe(luna.id);
    expect(screen.getByLabelText(`Daily allowance for ${plainUser.display_name}`)).toHaveValue(
      'standard',
    );
  });

  it('assigns an already tested card to multiple teams without repeating the provider test', async () => {
    const second = { ...team, id: '99999999-9999-4999-8999-999999999999', name: 'Second team' };
    const workspace = installModelWorkspace();
    server.use(http.get('/api/teams', () => HttpResponse.json({ items: [team, second] })));
    const { user } = renderApp('/admin/llm', 'admin');
    const card = await screen.findByRole('article', { name: 'Sol model card' });
    await user.click(within(card).getByRole('button', { name: 'Assign model' }));
    await user.click(screen.getByLabelText('Specific teams'));
    await user.click(screen.getByRole('checkbox', { name: new RegExp(team.name) }));
    await user.click(screen.getByRole('checkbox', { name: /Second team/ }));
    await user.click(screen.getByRole('button', { name: 'Save and close' }));
    await screen.findByText('Assignments and limits saved. Model cards are up to date.');
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    expect(workspace.writes[0]?.changes).toHaveLength(2);
    expect(workspace.state.tests).toBe(0);
    expect(workspace.state.bindings).toHaveLength(3);
    expect(card).toHaveTextContent(team.name);
    expect(card).toHaveTextContent(second.name);
  });

  it('counts five research slots separately from embedding profiles', async () => {
    const profiles = [
      luna,
      sol,
      ...[3, 4, 5].map((index) =>
        draft({
          id: `00000000-0000-4000-8000-00000000000${index}`,
          name: `Model ${index}`,
        }),
      ),
      draft({
        id: '99999999-9999-4999-8999-999999999999',
        name: 'Embeddings',
        roles: ['embeddings'],
      }),
    ];
    installModelWorkspace(profiles);
    renderApp('/admin/llm', 'admin');
    expect(await screen.findByText(/5 of 5 connections/)).toBeVisible();
    expect(screen.getByRole('button', { name: 'Add model' })).toBeDisabled();
    expect(screen.getAllByRole('article')).toHaveLength(5);
    expect(screen.queryByText('Embeddings')).not.toBeInTheDocument();
  });
});
