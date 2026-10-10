import { act, renderHook, waitFor } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { expect, it } from 'vitest';

import { useAuthStore } from '@/stores/auth';
import { setCsrfCookie } from '@/test/env';
import { adminUser, plainUser, tokenFor } from '@/test/fixtures';
import { server } from '@/test/server';

import { useTotpSettings } from './useTotpSettings';

const status = {
  methods: ['authenticator'],
  available_methods: ['authenticator', 'email'],
  required: false,
};

it('does not report a selected factor as enabled before its status has loaded', async () => {
  let release!: () => void;
  const response = new Promise<void>((resolve) => {
    release = resolve;
  });
  server.use(
    http.get('/api/auth/mfa', async () => {
      await response;
      return HttpResponse.json(status);
    }),
  );
  useAuthStore.getState().setSession(tokenFor(plainUser));
  const { result } = renderHook(useTotpSettings);
  act(() => result.current.setMethod('authenticator'));
  expect(result.current.resource.loading).toBe(true);
  expect(result.current.resource.data).toBeNull();
  expect(result.current.enabled).toBe(false);

  await act(async () => {
    release();
    await response;
  });
  await waitFor(() => expect(result.current.resource.loading).toBe(false));
  expect(result.current.enabled).toBe(true);
  expect(result.current.resource.error).toBeNull();
});

it('submitting without selecting a method does not mutate factors or the session', async () => {
  let mutations = 0;
  const unexpectedMutation = () => {
    mutations += 1;
    return new HttpResponse(null, { status: 204 });
  };
  server.use(
    http.get('/api/auth/mfa', () => HttpResponse.json(status)),
    http.post('/api/auth/totp/*', unexpectedMutation),
    http.post('/api/auth/mfa/email/*', unexpectedMutation),
  );
  const original = tokenFor(plainUser);
  useAuthStore.getState().setSession(original);
  const { result } = renderHook(useTotpSettings);
  await waitFor(() => expect(result.current.resource.loading).toBe(false));
  await act(async () => result.current.action.run());

  expect(mutations).toBe(0);
  expect(result.current.method).toBeNull();
  expect(result.current.action).toMatchObject({ busy: false, error: null });
  expect(useAuthStore.getState()).toMatchObject({
    status: 'authenticated',
    user: plainUser,
    accessToken: original.access_token,
  });
});

it.each(['authenticator', 'email'] as const)(
  'preserves pending %s setup through a token refresh within the same login',
  async (method) => {
    const original = tokenFor(plainUser);
    const rotated = tokenFor(plainUser, { revision: 'rotated' });
    const enrolment = {
      secret: 'SYNTHETIC-SETUP-KEY',
      provisioning_uri: 'otpauth://test',
      expires_in: 600,
    };
    let confirmation: unknown;
    let confirmationAuthorization: string | null = null;
    server.use(
      http.get('/api/auth/mfa', () => HttpResponse.json({ ...status, methods: [] })),
      http.post('/api/auth/totp/enrol', () => HttpResponse.json(enrolment)),
      http.post('/api/auth/mfa/email/enrol', () =>
        HttpResponse.json({
          mfa_required: true,
          challenge_token: 'synthetic-email-challenge',
          expires_at: '2026-09-06T12:00:00Z',
          methods: ['email'],
          email_sent: true,
          authenticator_email_proof: false,
          enrollment_required: false,
        }),
      ),
      http.post('/api/auth/refresh', () => HttpResponse.json(rotated)),
      http.post(
        method === 'email' ? '/api/auth/mfa/email/enrol/confirm' : '/api/auth/totp/confirm',
        async ({ request }) => {
          confirmation = await request.json();
          confirmationAuthorization = request.headers.get('Authorization');
          return new HttpResponse(null, { status: 204 });
        },
      ),
    );
    setCsrfCookie('synthetic-refresh-csrf');
    useAuthStore.getState().setSession(original);
    const generation = useAuthStore.getState().sessionGeneration;
    const { result } = renderHook(useTotpSettings);
    await waitFor(() => expect(result.current.resource.loading).toBe(false));
    act(() => {
      result.current.setMethod(method);
      result.current.setPassword('synthetic-current-password');
    });
    await act(async () => result.current.action.run());
    act(() => result.current.setCode('123456'));

    await act(async () => {
      expect(await useAuthStore.getState().refresh()).toBe(rotated.access_token);
    });

    expect(useAuthStore.getState()).toMatchObject({
      status: 'authenticated',
      accessToken: rotated.access_token,
      sessionGeneration: generation,
    });
    expect(result.current).toMatchObject({
      method,
      password: '',
      code: '123456',
      enrolment: method === 'authenticator' ? enrolment : null,
      challenge: method === 'email' ? 'synthetic-email-challenge' : null,
      action: { busy: false, error: null },
    });
    await act(async () => result.current.action.run());
    expect(confirmation).toEqual(
      method === 'email'
        ? { challenge_token: 'synthetic-email-challenge', code: '123456' }
        : { code: '123456' },
    );
    expect(confirmationAuthorization).toBe(`Bearer ${rotated.access_token}`);
    expect(useAuthStore.getState().status).toBe('anonymous');
    expect(result.current).toMatchObject({
      method: null,
      code: '',
      enrolment: null,
      challenge: null,
      action: { busy: false, error: null },
    });
  },
);

it.each(['another account', 'same account new family'])(
  'clears factor proofs and retains %s after an earlier session changes MFA',
  async (kind) => {
    let release!: () => void;
    const response = new Promise<void>((resolve) => {
      release = resolve;
    });
    let submitted: unknown;
    server.use(
      http.get('/api/auth/mfa', () => HttpResponse.json(status)),
      http.post('/api/auth/totp/disable', async ({ request }) => {
        submitted = await request.json();
        await response;
        return new HttpResponse(null, { status: 204 });
      }),
    );
    useAuthStore.getState().setSession(tokenFor(plainUser));
    const { result } = renderHook(useTotpSettings);
    await waitFor(() => expect(result.current.resource.loading).toBe(false));
    act(() => {
      result.current.setMethod('authenticator');
      result.current.setPassword('synthetic-current-password');
      result.current.setCode('123456');
    });
    let confirmation!: Promise<void>;
    act(() => {
      confirmation = result.current.action.run();
    });
    await waitFor(() =>
      expect(submitted).toEqual({ password: 'synthetic-current-password', code: '123456' }),
    );

    const replacement =
      kind === 'another account'
        ? tokenFor(adminUser)
        : tokenFor(plainUser, { familyId: 'new-login' });
    act(() => useAuthStore.getState().setSession(replacement));
    expect(result.current).toMatchObject({ password: '', code: '', method: null });
    await act(async () => {
      release();
      await confirmation;
    });

    expect(result.current).toMatchObject({
      method: null,
      password: '',
      code: '',
      challenge: null,
      enrolment: null,
      action: { busy: false, error: null },
    });
    expect(useAuthStore.getState()).toMatchObject({
      status: 'authenticated',
      user: replacement.user,
      accessToken: replacement.access_token,
    });
  },
);
