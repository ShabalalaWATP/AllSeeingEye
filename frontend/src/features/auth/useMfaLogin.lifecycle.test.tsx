import { act, renderHook, waitFor } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { expect, it } from 'vitest';

import type { PendingMfa } from '@/lib/api/mfa';
import { useAuthStore } from '@/stores/auth';
import { adminUser, plainUser, tokenFor } from '@/test/fixtures';
import { server } from '@/test/server';

import { useMfaLogin } from './useMfaLogin';

const challenge: PendingMfa = {
  mfa_required: true,
  challenge_token: 'synthetic-lifecycle-challenge',
  expires_at: '2099-01-01T00:00:00Z',
  methods: ['authenticator'],
  enrollment_required: false,
  email_sent: false,
};

it('keeps a replacement identity when an earlier MFA request completes while still mounted', async () => {
  let release!: () => void;
  const response = new Promise<void>((resolve) => {
    release = resolve;
  });
  let requestSignal: AbortSignal | undefined;
  server.use(
    http.post('/api/auth/mfa/verify', async ({ request }) => {
      requestSignal = request.signal;
      await response;
      return HttpResponse.json(tokenFor(plainUser));
    }),
  );
  useAuthStore.getState().clearSession();
  const { result } = renderHook(() => useMfaLogin(challenge));
  act(() => result.current.setCode('123456'));
  let verification!: Promise<void>;
  act(() => {
    verification = result.current.run('verify');
  });
  await waitFor(() => expect(requestSignal).toBeDefined());
  expect(result.current.busy).toBe(true);

  const replacement = tokenFor(adminUser);
  act(() => useAuthStore.getState().setSession(replacement));
  await act(async () => {
    release();
    await verification;
  });

  expect(requestSignal?.aborted).toBe(false);
  expect(result.current.busy).toBe(false);
  expect(result.current.error).toBeNull();
  expect(useAuthStore.getState()).toMatchObject({
    status: 'authenticated',
    user: adminUser,
    accessToken: replacement.access_token,
  });
});
