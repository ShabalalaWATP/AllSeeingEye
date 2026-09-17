import { act, screen, waitFor, within } from '@testing-library/react';
import { expect, it, vi } from 'vitest';
import { http, HttpResponse } from 'msw';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';
import { useAuthStore } from '@/stores/auth';
import { plainUser, tokenFor } from '@/test/fixtures';
import { binding, draft, installConnections, proof, team } from './llmTestFixtures';

it('keeps keyboard focus on the step heading when delayed model discovery replaces the input', async () => {
  installConnections([]);
  let finish!: () => void;
  server.use(
    http.post('/api/admin/llm/models/discover', async () => {
      await new Promise<void>((resolve) => {
        finish = resolve;
      });
      return HttpResponse.json({ models: ['gpt-5.6-luna'] });
    }),
  );
  const { user } = renderApp('/admin/llm', 'admin');
  await user.click(await screen.findByRole('button', { name: 'Add model connection' }));
  await user.type(screen.getByLabelText('API key'), 'synthetic-key');
  await user.click(screen.getByRole('button', { name: 'Continue to model' }));
  const heading = screen.getByRole('heading', { name: 'Choose and test your model' });
  expect(heading).toHaveFocus();
  expect(screen.getByLabelText('Model ID')).toBeVisible();
  await waitFor(() => expect(finish).toBeTypeOf('function'));
  await act(async () => {
    finish();
    await Promise.resolve();
  });
  await screen.findByLabelText('Models returned by this account');
  expect(heading).toHaveFocus();
});
it('progresses from credentials to catalogue and test, then review and exact confirmation', async () => {
  const state = installConnections([]);
  const { user } = renderApp('/admin/llm', 'admin');
  await screen.findByText('No additional connections.');
  await user.click(screen.getByRole('button', { name: 'Add model connection' }));
  expect(screen.queryByLabelText('Model ID')).not.toBeInTheDocument();
  await user.type(screen.getByLabelText('API key'), 'synthetic-key');
  expect(state.models).toBe(0);
  await user.click(screen.getByRole('button', { name: 'Continue to model' }));
  await screen.findByText(/2 models returned by this account/);
  expect(screen.getByLabelText('API key')).not.toBeVisible();
  expect(screen.queryByRole('button', { name: 'Confirm switch' })).not.toBeInTheDocument();
  expect(screen.getByLabelText('Reasoning effort')).toHaveValue('');
  await user.type(screen.getByLabelText('Search account models'), 'luna');
  await user.selectOptions(
    screen.getByLabelText('Models returned by this account'),
    'gpt-5.6-luna',
  );
  await user.click(screen.getByRole('button', { name: 'Test connection' }));
  await screen.findByText(/Connection test passed in/);
  expect(screen.getByLabelText('API key')).toHaveValue('');
  expect(screen.getByLabelText('Model ID')).not.toBeVisible();
  expect(state.applies).toHaveLength(0);
  await user.click(screen.getByRole('button', { name: 'Review and apply' }));
  expect(screen.getByRole('group', { name: 'Confirm connection switch' })).toHaveTextContent(
    'gpt-5.6-luna',
  );
  await user.click(screen.getByRole('button', { name: 'Confirm switch' }));
  await screen.findByText('Global connection switched to gpt-5.6-luna.');
  expect(state.applies[0]).toMatchObject({
    tested_config_hash: proof,
    expected_profile_revision: 1,
    team_id: null,
  });
});
it('invalidates test review on returning to model settings and preserves provider fields', async () => {
  installConnections([]);
  const { user } = renderApp('/admin/llm', 'admin');
  await screen.findByText('No additional connections.');
  await user.click(screen.getByRole('button', { name: 'Add model connection' }));
  await user.type(screen.getByLabelText('API key'), 'synthetic-key');
  await user.click(screen.getByRole('button', { name: 'Continue to model' }));
  await user.selectOptions(
    await screen.findByLabelText('Models returned by this account'),
    'gpt-5.6-luna',
  );
  await user.click(screen.getByRole('button', { name: 'Test connection' }));
  await screen.findByText(/Connection test passed in/);
  await user.click(screen.getByRole('button', { name: 'Back to model settings' }));
  expect(screen.queryByRole('button', { name: 'Review and apply' })).not.toBeInTheDocument();
  await user.click(screen.getByRole('button', { name: 'Back to provider' }));
  expect(screen.getByLabelText('Base URL')).toHaveValue('https://api.openai.com/v1');
  expect(screen.getByLabelText('API key')).toHaveValue('');
});
it('applies a personal override without replacing global routing and resets it deliberately', async () => {
  const active = draft({
    is_bound: true,
    is_tested: true,
    tested_revision: 1,
    tested_config_hash: proof,
  });
  const state = installConnections([active], [binding(active)]);
  const { user } = renderApp('/admin/llm', 'admin');
  await screen.findByRole('region', { name: 'Global AI connection' });
  await user.click(screen.getByRole('button', { name: 'Reuse OpenAI Luna' }));
  await user.type(screen.getByLabelText('Find a personal workspace'), plainUser.email);
  await user.selectOptions(screen.getByLabelText('Apply OpenAI Luna to'), `user:${plainUser.id}`);
  await user.click(screen.getByRole('button', { name: 'Review and apply' }));
  expect(screen.getByRole('group', { name: 'Confirm connection switch' })).toHaveTextContent(
    'Their team research uses the team or global connection',
  );
  await user.click(screen.getByRole('button', { name: 'Confirm switch' }));
  await screen.findByText('Personal workspace connection switched to gpt-5.6-luna.');
  expect(state.bindings).toHaveLength(2);
  expect(state.applies[0]).toMatchObject({
    team_id: null,
    user_id: plainUser.id,
    expected_binding_revision: null,
  });
  const personal = screen.getByRole('region', { name: 'Personal AI overrides' });
  await user.click(within(personal).getByRole('button', { name: 'Use global connection' }));
  expect(state.bindings).toHaveLength(2);
  await user.click(within(personal).getByRole('button', { name: 'Confirm personal reset' }));
  await waitFor(() => expect(state.bindings).toHaveLength(1));
});
it('preserves a team replacement audience instead of defaulting to global', async () => {
  const active = draft({ is_bound: true });
  installConnections([active], [binding(active), binding(active, team.id)]);
  const { user } = renderApp('/admin/llm', 'admin');
  const teams = await screen.findByRole('region', { name: 'Team AI overrides' });
  await user.click(within(teams).getByRole('button', { name: 'Replace OpenAI Luna' }));
  await user.type(screen.getByLabelText('API key'), 'synthetic-replacement');
  await user.click(screen.getByRole('button', { name: 'Continue to model' }));
  await user.click(screen.getByRole('button', { name: 'Test connection' }));
  await screen.findByText(/Connection test passed in/);
  expect(screen.getByLabelText('Apply OpenAI Luna replacement to')).toHaveValue(team.id);
});

it('keeps Luna as the default while assigning a second model to a team and personal workspace', async () => {
  const luna = draft({
    is_bound: true,
    is_tested: true,
    tested_revision: 1,
    tested_config_hash: proof,
  });
  const state = installConnections([luna], [binding(luna)]);
  const { user } = renderApp('/admin/llm', 'admin');
  await user.click(await screen.findByRole('button', { name: 'Add model connection' }));
  await user.type(screen.getByLabelText('API key'), 'synthetic-second-key');
  await user.click(screen.getByRole('button', { name: 'Continue to model' }));
  await user.selectOptions(
    await screen.findByLabelText('Models returned by this account'),
    'manual-alternative',
  );
  await user.selectOptions(screen.getByLabelText('Reasoning effort'), 'high');
  await user.click(screen.getByRole('button', { name: 'Test connection' }));
  await screen.findByText(/Connection test passed in/);
  await user.selectOptions(screen.getByLabelText('Apply manual-alternative to'), team.id);
  await user.click(screen.getByRole('button', { name: 'Review and apply' }));
  await user.click(screen.getByRole('button', { name: 'Confirm switch' }));
  await screen.findByText(`${team.name} switched to manual-alternative.`);
  expect(state.bindings.find((item) => item.team_id === null)?.profile_id).toBe(luna.id);
  expect(state.profiles.find((item) => item.id === luna.id)?.model).toBe('gpt-5.6-luna');
  const teamConnections = screen.getByRole('region', { name: 'Team AI overrides' });
  await user.click(
    within(teamConnections).getByRole('button', { name: 'Reuse manual-alternative' }),
  );
  await user.selectOptions(
    screen.getByLabelText('Apply manual-alternative to'),
    `user:${plainUser.id}`,
  );
  await user.click(screen.getByRole('button', { name: 'Review and apply' }));
  await user.click(screen.getByRole('button', { name: 'Confirm switch' }));
  await screen.findByText('Personal workspace connection switched to manual-alternative.');
  expect(state.profiles).toHaveLength(2);
  expect(state.bindings).toHaveLength(3);
  expect(state.saves[0]).toMatchObject({ model: 'manual-alternative', reasoning_effort: 'high' });
  expect(state.applies.map((item) => item.team_id)).toEqual([team.id, null]);
});

it('passes an authority-bound signal from the real confirmation UI and blocks a late 401 retry', async () => {
  const active = draft({ is_tested: true, tested_revision: 1, tested_config_hash: proof });
  installConnections([active]);
  const { user } = renderApp('/admin/llm', 'admin');
  const drafts = await screen.findByRole('region', { name: 'Saved connection drafts' });
  await user.click(within(drafts).getByText('OpenAI Luna', { exact: false, selector: 'summary' }));
  await user.click(screen.getByRole('button', { name: 'Review and apply' }));
  let resolve!: (value: Response) => void;
  const originalFetch = window.fetch.bind(window);
  const fetch = vi.spyOn(window, 'fetch').mockImplementation((url, options) => {
    if (options?.method === 'PUT')
      return new Promise((done) => {
        resolve = done;
      });
    return originalFetch(url, options);
  });
  try {
    await user.click(screen.getByRole('button', { name: 'Confirm switch' }));
    await waitFor(() =>
      expect(fetch.mock.calls.some((call) => call[1]?.method === 'PUT')).toBe(true),
    );
    const signal = fetch.mock.calls.find((call) => call[1]?.method === 'PUT')?.[1]?.signal;
    expect(signal).toBeInstanceOf(AbortSignal);
    act(() => useAuthStore.getState().setSession(tokenFor(plainUser)));
    expect(signal?.aborted).toBe(true);
    await act(async () => {
      resolve(new Response(null, { status: 401 }));
      await Promise.resolve();
    });
    expect(fetch.mock.calls.filter((call) => call[1]?.method === 'PUT')).toHaveLength(1);
  } finally {
    fetch.mockRestore();
  }
});
