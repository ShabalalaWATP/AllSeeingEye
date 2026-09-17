import { act, screen, waitFor, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { expect, it } from 'vitest';

import { aiDefaults, aiOverride, aiPolicy } from '@/test/fixtures.aiUsage';
import { apiError } from '@/test/handlers';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';

import { draft } from './llmTestFixtures';
import { installModelWorkspace } from './modelWorkspaceTestFixtures';

function deferredResponse() {
  let release!: () => void;
  const pending = new Promise<void>((resolve) => {
    release = resolve;
  });
  return { pending, release };
}

async function openAdvanced() {
  const view = renderApp('/admin/llm', 'admin');
  await view.user.click(
    await screen.findByRole('button', {
      name: 'Advanced limits and embedding connections',
    }),
  );
  await screen.findByRole('heading', { name: 'Allowance policies' });
  return view;
}

it.each(['success', 'failure'])(
  'waits for an advanced policy save before closing on %s and refreshes the matrix afterwards',
  async (outcome) => {
    const workspace = installModelWorkspace();
    const response = deferredResponse();
    let started = false;
    server.use(
      http.post('/api/admin/ai-usage/policies', async () => {
        started = true;
        await response.pending;
        if (outcome === 'failure') return apiError(409, 'conflict', 'Policy changed. Try again.');
        const saved = aiPolicy({ period: 'day', request_limit: 250, token_limit: 500_000 });
        workspace.policies = [saved];
        return HttpResponse.json(saved, { status: 201 });
      }),
    );
    const { user } = await openAdvanced();
    await user.selectOptions(screen.getByLabelText('Reset'), 'day');
    await user.type(screen.getByLabelText('Requests'), '250');
    await user.type(screen.getByLabelText('Tokens'), '500000');
    await user.click(screen.getByRole('button', { name: 'Add policy' }));
    await waitFor(() => expect(started).toBe(true));
    const done = screen.getByRole('button', { name: 'Done with advanced settings' });
    try {
      expect(done).toBeDisabled();
      await user.click(done);
      expect(screen.getByRole('heading', { name: 'Allowance policies' })).toBeVisible();
    } finally {
      await act(() => {
        response.release();
        return response.pending;
      });
    }
    await waitFor(() => expect(done).toBeEnabled());
    if (outcome === 'failure')
      expect(await screen.findByRole('alert')).toHaveTextContent('Policy changed.');
    await user.click(done);
    await waitFor(() =>
      expect(screen.getByLabelText('Daily allowance for Global / site')).toHaveValue(
        outcome === 'success' ? 'standard' : 'inherit',
      ),
    );
  },
);

it('keeps the advanced panel and policy form locked while suggested policies are being applied', async () => {
  installModelWorkspace();
  const response = deferredResponse();
  let started = false;
  server.use(
    http.get('/api/admin/ai-usage/defaults', () => HttpResponse.json(aiDefaults())),
    http.post('/api/admin/ai-usage/defaults', async () => {
      started = true;
      await response.pending;
      return HttpResponse.json({ created: [aiPolicy()] }, { status: 201 });
    }),
  );
  const { user } = await openAdvanced();
  await user.click(await screen.findByRole('button', { name: 'Apply 1 suggested policies' }));
  await waitFor(() => expect(started).toBe(true));
  try {
    expect(screen.getByRole('button', { name: 'Done with advanced settings' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Add policy' })).toBeDisabled();
  } finally {
    await act(() => {
      response.release();
      return response.pending;
    });
  }
  await waitFor(() =>
    expect(screen.getByRole('button', { name: 'Done with advanced settings' })).toBeEnabled(),
  );
});

it.each(['create', 'revoke'] as const)(
  'cannot close or switch an override editor during %s',
  async (operation) => {
    const workspace = installModelWorkspace();
    const policy = aiPolicy();
    workspace.policies = [
      policy,
      aiPolicy({ id: '88888888-8888-4888-8888-888888888888', scope: 'system' }),
    ];
    const response = deferredResponse();
    let started = false;
    const save = async () => {
      started = true;
      await response.pending;
      return HttpResponse.json(
        aiOverride({ revoked_at: operation === 'revoke' ? '2026-09-17T12:00:00Z' : null }),
      );
    };
    server.use(
      http.get(`/api/admin/ai-usage/policies/${policy.id}/overrides`, () =>
        HttpResponse.json({ items: operation === 'revoke' ? [aiOverride()] : [] }),
      ),
      http.post(`/api/admin/ai-usage/policies/${policy.id}/overrides`, save),
      http.delete('/api/admin/ai-usage/overrides/:id', save),
    );
    const { user } = await openAdvanced();
    await user.click(await screen.findByRole('button', { name: 'Overrides for Everyone' }));
    const panel = screen.getByRole('region', { name: 'Temporary overrides for Everyone' });
    await user.click(
      await within(panel).findByRole('button', {
        name: operation === 'revoke' ? 'Revoke' : 'Add override',
      }),
    );
    await waitFor(() => expect(started).toBe(true));
    try {
      expect(screen.getByRole('button', { name: 'Done with advanced settings' })).toBeDisabled();
      for (const name of [
        'Overrides for Everyone',
        'Overrides for System work',
        'Disable Everyone',
      ]) {
        const button = screen.getByRole('button', { name });
        expect(button).toBeDisabled();
        await user.click(button);
      }
      expect(panel).toBeVisible();
    } finally {
      await act(() => {
        response.release();
        return response.pending;
      });
    }
    await waitFor(() =>
      expect(screen.getByRole('button', { name: 'Done with advanced settings' })).toBeEnabled(),
    );
  },
);

it('keeps embedding settings mounted until the encrypted profile save finishes', async () => {
  const workspace = installModelWorkspace();
  const response = deferredResponse();
  let started = false;
  server.use(
    http.post('/api/admin/llm/models/discover', () => HttpResponse.json({ models: [] })),
    http.post('/api/admin/llm/profiles', async () => {
      started = true;
      await response.pending;
      const saved = draft({
        id: '99999999-9999-4999-8999-999999999999',
        name: 'Search',
        model: 'embedding-model',
        roles: ['embeddings'],
      });
      workspace.state.profiles.push(saved);
      return HttpResponse.json(saved, { status: 201 });
    }),
  );
  const { user } = await openAdvanced();
  await user.click(screen.getByRole('button', { name: 'Add embedding connection' }));
  await user.type(screen.getByLabelText('API key'), 'synthetic-key');
  await user.type(screen.getByLabelText('Model ID'), 'embedding-model');
  await user.click(screen.getByRole('button', { name: 'Save draft' }));
  await waitFor(() => expect(started).toBe(true));
  try {
    expect(screen.getByRole('button', { name: 'Done with advanced settings' })).toBeDisabled();
  } finally {
    await act(() => {
      response.release();
      return response.pending;
    });
  }
  await screen.findByRole('button', { name: 'Edit Search' });
  await user.click(screen.getByRole('button', { name: 'Done with advanced settings' }));
  await waitFor(() =>
    expect(screen.getByRole('button', { name: 'Refresh workspace' })).toBeEnabled(),
  );
  expect(screen.getAllByRole('article')).toHaveLength(2);
});
