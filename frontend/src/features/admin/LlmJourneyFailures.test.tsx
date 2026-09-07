import { act, screen, waitFor } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { expect, it } from 'vitest';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';
import { installConnections, proof } from './llmTestFixtures';
async function prepare() {
  const view = renderApp('/admin/llm', 'admin');
  await screen.findByText('No saved drafts.');
  await view.user.click(screen.getByRole('button', { name: 'Configure connection' }));
  await view.user.type(screen.getByLabelText('API key'), 'synthetic-test-key');
  await view.user.click(screen.getByRole('button', { name: 'Continue to model' }));
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
