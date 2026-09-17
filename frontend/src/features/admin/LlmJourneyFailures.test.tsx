import { act, screen, waitFor } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { expect, it } from 'vitest';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';
import { apiError } from '@/test/handlers';
import { installConnections, proof } from './llmTestFixtures';
async function prepare() {
  const view = renderApp('/admin/llm', 'admin');
  await screen.findByText('No additional connections.');
  await view.user.click(screen.getByRole('button', { name: 'Add model connection' }));
  await view.user.type(screen.getByLabelText('API key'), 'synthetic-test-key');
  await view.user.click(screen.getByRole('button', { name: 'Continue to model' }));
  await view.user.selectOptions(
    await screen.findByLabelText('Models returned by this account'),
    'gpt-5.6-luna',
  );
  return view;
}
it.each([
  { ok: false, revision: 1, tested_config_hash: proof, error: 'The provider rejected this model.' },
  { ok: true, revision: 99, tested_config_hash: proof, error: null },
  { ok: true, revision: 1, tested_config_hash: null, error: null },
])('does not permit routing when test proof is invalid: %j', async (outcome) => {
  const state = installConnections([]);
  server.use(
    http.post('/api/admin/llm/profiles/:id/test', () =>
      HttpResponse.json({
        ...outcome,
        latency_ms: 2,
        model: 'test-model',
        tested_at: '2026-09-01T00:00:00Z',
      }),
    ),
  );
  const view = await prepare();
  await view.user.click(screen.getByRole('button', { name: 'Test connection' }));
  expect(await screen.findByRole('alert')).toHaveTextContent(
    outcome.error ?? 'This configuration did not pass the compatibility test.',
  );
  expect(screen.queryByRole('button', { name: 'Review and apply' })).not.toBeInTheDocument();
  expect(state.applies).toHaveLength(0);
  expect(screen.getByLabelText('API key')).toHaveValue('');
});
it('drops an in-flight test receipt when setup is closed by navigation', async () => {
  const state = installConnections([]);
  let resolve!: () => void;
  let started = false;
  let signal: AbortSignal | undefined;
  server.use(
    http.post('/api/admin/llm/profiles/:id/test', async ({ request }) => {
      signal = request.signal;
      started = true;
      await new Promise<void>((done) => {
        resolve = done;
      });
      return HttpResponse.json({
        ok: true,
        revision: 1,
        tested_config_hash: proof,
        error: null,
        latency_ms: 2,
        model: 'test-model',
        tested_at: '2026-09-01T00:00:00Z',
      });
    }),
  );
  const view = await prepare();
  await view.user.click(screen.getByRole('button', { name: 'Test connection' }));
  await waitFor(() => expect(started).toBe(true));
  view.unmount();
  expect(signal?.aborted).toBe(true);
  await act(async () => {
    resolve();
    await Promise.resolve();
  });
  expect(state.applies).toHaveLength(0);
  expect(screen.queryByText(/Connection test passed/)).not.toBeInTheDocument();
});

it('keeps credentials after a save failure and retries without re-entering the key', async () => {
  installConnections([]);
  server.use(
    http.post('/api/admin/llm/profiles', () =>
      apiError(500, 'internal_error', 'Something went wrong on our side.'),
    ),
  );
  const view = await prepare();
  await view.user.click(screen.getByRole('button', { name: 'Test connection' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('Could not save this draft.');
  expect(screen.getByRole('alert')).toHaveTextContent('The active connection has not changed.');
  expect(screen.getByLabelText('API key')).toHaveValue('synthetic-test-key');
  const state = installConnections([]);
  await view.user.click(screen.getByRole('button', { name: 'Test connection' }));
  await screen.findByText(/Connection test passed in/);
  expect(state.saves[0]).toMatchObject({ api_key: 'synthetic-test-key' });
  expect(screen.getByLabelText('API key')).toHaveValue('');
  expect(state.applies).toHaveLength(0);
});

it('returns to provider details after a duplicate name conflict without losing the key or model', async () => {
  installConnections([]);
  server.use(
    http.post('/api/admin/llm/profiles', () =>
      HttpResponse.json(
        {
          error: {
            code: 'conflict',
            message: 'A connection with this name already exists.',
            fields: { name: 'Choose a different connection name.' },
          },
        },
        { status: 409 },
      ),
    ),
  );
  const view = await prepare();
  await view.user.click(screen.getByRole('button', { name: 'Test connection' }));
  expect(await screen.findByRole('alert')).toHaveTextContent(
    'A connection with this name already exists.',
  );
  expect(screen.getByLabelText('Connection name')).toBeVisible();
  expect(screen.getByLabelText('API key')).toHaveValue('synthetic-test-key');
  await view.user.clear(screen.getByLabelText('Connection name'));
  await view.user.type(screen.getByLabelText('Connection name'), 'Second connection');
  const state = installConnections([]);
  await view.user.click(screen.getByRole('button', { name: 'Continue to model' }));
  await view.user.click(screen.getByRole('button', { name: 'Test connection' }));
  await screen.findByText(/Connection test passed in/);
  expect(state.saves[0]).toMatchObject({
    name: 'Second connection',
    model: 'gpt-5.6-luna',
    api_key: 'synthetic-test-key',
  });
});
