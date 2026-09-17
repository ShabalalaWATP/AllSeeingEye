import { screen, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { http, HttpResponse } from 'msw';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';
import { apiError } from '@/test/handlers';
import { draft, team } from './llmTestFixtures';
import { installModelWorkspace, luna } from './modelWorkspaceTestFixtures';

describe('Model workspace recovery', () => {
  it('retains assignments after a rejected atomic update and offers refresh', async () => {
    const workspace = installModelWorkspace();
    server.use(
      http.put('/api/admin/llm/workspace', () =>
        apiError(409, 'conflict', 'The team changed. Refresh and retry.'),
      ),
    );
    const { user } = renderApp('/admin/llm', 'admin');
    await user.selectOptions(
      await screen.findByLabelText(`Daily allowance for ${team.name}`),
      'light',
    );
    await user.click(screen.getByRole('button', { name: `Save ${team.name}` }));
    expect(await screen.findByRole('alert')).toHaveTextContent('The team changed.');
    expect(workspace.policies).toHaveLength(0);
    expect(workspace.state.bindings).toHaveLength(1);
    expect(screen.getByRole('button', { name: 'Refresh workspace' })).toBeEnabled();
  });

  it('recovers failed initial loading without sending a provider request', async () => {
    const workspace = installModelWorkspace();
    let fail = true;
    server.use(
      http.get('/api/admin/llm/connections', () =>
        fail
          ? apiError(503, 'unavailable', 'Connections unavailable.')
          : HttpResponse.json({ items: workspace.state.bindings }),
      ),
    );
    const { user } = renderApp('/admin/llm', 'admin');
    expect(await screen.findByRole('alert')).toHaveTextContent('Connections unavailable.');
    expect(screen.queryByRole('button', { name: 'Add model' })).not.toBeInTheDocument();
    fail = false;
    await user.click(screen.getByRole('button', { name: 'Refresh workspace' }));
    expect(await screen.findByRole('article', { name: 'Luna model card' })).toBeVisible();
    expect(workspace.state.models).toBe(0);
    expect(workspace.state.tests).toBe(0);
  });

  it('requires confirmation for removing an unused model, and protects assigned cards', async () => {
    const workspace = installModelWorkspace();
    const { user } = renderApp('/admin/llm', 'admin');
    const globalCard = await screen.findByRole('article', { name: 'Luna model card' });
    expect(within(globalCard).queryByRole('button', { name: 'Remove' })).not.toBeInTheDocument();
    const unused = screen.getByRole('article', { name: 'Sol model card' });
    await user.click(within(unused).getByRole('button', { name: 'Remove' }));
    expect(workspace.state.profiles).toHaveLength(2);
    await user.click(within(unused).getByRole('button', { name: 'Confirm removal' }));
    await screen.findByText('Saved model removed. A model slot is now available.');
    expect(screen.queryByRole('article', { name: 'Sol model card' })).not.toBeInTheDocument();
    expect(workspace.state.profiles).toHaveLength(1);
  });

  it('protects legacy active profiles and explains the transition', async () => {
    installModelWorkspace([draft({ ...luna, enabled: true, is_tested: false })], []);
    renderApp('/admin/llm', 'admin');
    const card = await screen.findByRole('article', { name: 'Luna model card' });
    expect(card).toHaveTextContent('Legacy active');
    expect(within(card).queryByRole('button', { name: 'Remove' })).not.toBeInTheDocument();
    expect(within(card).getByRole('button', { name: 'Test connection' })).toBeEnabled();
  });

  it('disables mutations when encrypted credential storage is unavailable', async () => {
    const workspace = installModelWorkspace();
    server.use(
      http.get('/api/admin/llm/profiles', () =>
        HttpResponse.json({ items: workspace.state.profiles, encryption_available: false }),
      ),
    );
    renderApp('/admin/llm', 'admin');
    expect(await screen.findByText('Credential storage unavailable')).toBeVisible();
    expect(screen.getByRole('button', { name: 'Add model' })).toBeDisabled();
    expect(screen.getByLabelText(`Model for ${team.name}`)).toBeDisabled();
  });
});
