import { act, fireEvent, screen, waitFor } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { beforeEach, expect, it } from 'vitest';
import { server } from '@/test/server';
import { apiError } from '@/test/handlers';
import { useAuthStore } from '@/stores/auth';
import { plainUser, tokenFor } from '@/test/fixtures';
import { draft, installConnections, proof } from './llmTestFixtures';
import { advanceToTest, mockModelSetupDialog, openWizard } from './ModelSetupTestSupport';

beforeEach(mockModelSetupDialog);

it('retains the key on a failed save and retries without re-entering it', async () => {
  const view = await openWizard();
  await advanceToTest(view);
  server.use(
    http.post('/api/admin/llm/profiles', () =>
      apiError(500, 'internal_error', 'Save unavailable.'),
    ),
  );
  await view.user.click(screen.getByRole('button', { name: 'Test connection' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('The connection could not be saved.');
  for (let step = 0; step < 3; step++)
    await view.user.click(screen.getByRole('button', { name: 'Back' }));
  expect(screen.getByLabelText('API key')).toHaveValue('synthetic-test-key');
  const retry = installConnections([]);
  for (let step = 0; step < 3; step++)
    await view.user.click(screen.getByRole('button', { name: 'Continue' }));
  await view.user.click(screen.getByRole('button', { name: 'Test connection' }));
  await screen.findByText(/Connection test passed/);
  expect(retry.saves[0]).toMatchObject({ api_key: 'synthetic-test-key' });
  expect(view.onApply).not.toHaveBeenCalled();
});

it.each([
  { ok: false, revision: 1, tested_config_hash: proof, error: 'Model unavailable.' },
  { ok: true, revision: 99, tested_config_hash: proof, error: null },
  { ok: true, revision: 1, tested_config_hash: null, error: null },
])('rejects invalid provider proof and never opens assignment: %j', async (outcome) => {
  const view = await openWizard();
  await advanceToTest(view);
  server.use(
    http.post('/api/admin/llm/profiles/:id/test', () =>
      HttpResponse.json({
        ...outcome,
        model: 'gpt-5.6-luna',
        tested_at: '2026-09-01T00:00:00Z',
        latency_ms: 4,
      }),
    ),
  );
  await view.user.click(screen.getByRole('button', { name: 'Test connection' }));
  expect(await screen.findByRole('alert')).toHaveTextContent(
    'The draft was saved, but the test failed.',
  );
  expect(screen.queryByRole('button', { name: 'Choose audience' })).not.toBeInTheDocument();
  expect(view.onApply).not.toHaveBeenCalled();
  for (let step = 0; step < 3; step++)
    await view.user.click(screen.getByRole('button', { name: 'Back' }));
  expect(screen.getByLabelText('API key')).toHaveValue('');
  expect(screen.getByLabelText('API key')).not.toBeRequired();
});

it('reuses the saved key after a rejected test and returns to editing a conflicting name', async () => {
  const view = await openWizard();
  await advanceToTest(view);
  server.use(
    http.post('/api/admin/llm/profiles/:id/test', () =>
      apiError(502, 'provider_unavailable', 'Try again.'),
    ),
  );
  await view.user.click(screen.getByRole('button', { name: 'Test connection' }));
  await screen.findByRole('alert');
  const retry = installConnections(view.state.profiles);
  await view.user.click(screen.getByRole('button', { name: 'Test connection' }));
  await screen.findByText(/Connection test passed/);
  expect(retry.saves[0]).not.toHaveProperty('api_key');
  expect(retry.profiles).toHaveLength(1);
});

it('returns a duplicate name conflict to the visible name field', async () => {
  const view = await openWizard();
  await advanceToTest(view);
  server.use(
    http.post('/api/admin/llm/profiles', () =>
      HttpResponse.json(
        {
          error: {
            code: 'conflict',
            message: 'Name already used.',
            fields: { name: 'Choose another name.' },
          },
        },
        { status: 409 },
      ),
    ),
  );
  await view.user.click(screen.getByRole('button', { name: 'Test connection' }));
  expect(await screen.findByLabelText('Connection name')).toBeVisible();
  expect(screen.getByRole('alert')).toHaveTextContent('Name already used.');
  await view.user.click(screen.getByRole('button', { name: 'Continue' }));
  expect(screen.getByLabelText('API key')).toHaveValue('synthetic-test-key');
});

it.each(['navigation', 'authority'])(
  'discards late test results after %s and blocks Escape while testing',
  async (exit) => {
    const view = await openWizard();
    await advanceToTest(view);
    let finish!: () => void;
    let signal: AbortSignal | undefined;
    server.use(
      http.post('/api/admin/llm/profiles/:id/test', async ({ request }) => {
        signal = request.signal;
        await new Promise<void>((resolve) => {
          finish = resolve;
        });
        return HttpResponse.json({
          ok: true,
          revision: 1,
          tested_config_hash: proof,
          error: null,
          model: 'gpt-5.6-luna',
          tested_at: '2026-09-01T00:00:00Z',
          latency_ms: 4,
        });
      }),
    );
    await view.user.click(screen.getByRole('button', { name: 'Test connection' }));
    await waitFor(() => expect(signal).toBeDefined());
    expect(screen.getByRole('button', { name: 'Back' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Close model setup' })).toBeDisabled();
    fireEvent(screen.getByRole('dialog'), new Event('cancel', { bubbles: true, cancelable: true }));
    expect(view.onClose).not.toHaveBeenCalled();
    if (exit === 'navigation') view.unmount();
    else act(() => useAuthStore.getState().setSession(tokenFor(plainUser)));
    await waitFor(() => expect(signal?.aborted).toBe(true));
    await act(async () => {
      finish();
      await Promise.resolve();
    });
    expect(view.onSaved).toHaveBeenCalledTimes(1);
    expect(view.onApply).not.toHaveBeenCalled();
    expect(screen.queryByText(/Connection test passed/)).not.toBeInTheDocument();
  },
);

it('discards an assignment completion after navigation has closed the popup', async () => {
  const view = await openWizard(
    draft({ is_tested: true, tested_revision: 1, tested_config_hash: proof }),
  );
  let complete!: () => void;
  view.onApply.mockImplementationOnce(
    () =>
      new Promise<void>((resolve) => {
        complete = resolve;
      }),
  );
  await view.user.click(screen.getByRole('button', { name: 'Save and close' }));
  expect(screen.getByRole('button', { name: 'Saving assignment…' })).toBeDisabled();
  view.unmount();
  await act(async () => {
    complete();
    await Promise.resolve();
  });
  expect(view.onClose).not.toHaveBeenCalled();
});
