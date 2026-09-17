import { act, renderHook, waitFor } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { expect, it } from 'vitest';
import { server } from '@/test/server';
import { apiError } from '@/test/handlers';
import { applySession } from '@/test/render';
import { useModelSetupDiscovery } from './ModelSetupDiscovery';

it('automatically retries transient errors at most three times, with an explicit refresh to try again', async () => {
  applySession('admin');
  let calls = 0;
  server.use(
    http.post('/api/admin/llm/models/discover', () => {
      calls++;
      return apiError(503, 'unavailable', 'Temporarily unavailable.');
    }),
  );
  const { result } = renderHook(() =>
    useModelSetupDiscovery(true, 'https://api.openai.com/v1', 'synthetic-key'),
  );
  await waitFor(() => expect(result.current.error).toBe('Temporarily unavailable.'));
  expect(calls).toBe(3);
  server.use(
    http.post('/api/admin/llm/models/discover', () =>
      HttpResponse.json({ models: ['available-model'] }),
    ),
  );
  act(() => result.current.refresh());
  await waitFor(() => expect(result.current.models).toEqual(['available-model']));
});

it('does not retry an invalid credential response', async () => {
  applySession('admin');
  let calls = 0;
  server.use(
    http.post('/api/admin/llm/models/discover', () => {
      calls++;
      return apiError(422, 'invalid_key', 'Check the key.');
    }),
  );
  const { result } = renderHook(() =>
    useModelSetupDiscovery(true, 'https://api.openai.com/v1', 'synthetic-key'),
  );
  await waitFor(() => expect(result.current.error).toBe('Check the key.'));
  expect(calls).toBe(1);
  expect(result.current.busy).toBe(false);
});

it('cancels discovery on leaving the model step and discards the old account result', async () => {
  applySession('admin');
  let signal: AbortSignal | undefined;
  let finish!: () => void;
  server.use(
    http.post('/api/admin/llm/models/discover', async ({ request }) => {
      signal = request.signal;
      await new Promise<void>((resolve) => {
        finish = resolve;
      });
      return HttpResponse.json({ models: ['old-account-model'] });
    }),
  );
  const { result, rerender } = renderHook(
    ({ visible }) => useModelSetupDiscovery(visible, 'https://api.openai.com/v1', 'synthetic-key'),
    { initialProps: { visible: true } },
  );
  await waitFor(() => expect(signal).toBeDefined());
  rerender({ visible: false });
  await waitFor(() => expect(signal?.aborted).toBe(true));
  await act(async () => {
    finish();
    await Promise.resolve();
  });
  expect(result.current.models).toEqual([]);
});
