import { act, screen, waitFor } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';

import { useAuthStore } from '@/stores/auth';
import { plainUser, USER_PASSWORD, tokenFor, adminUser } from '@/test/fixtures';
import { apiError } from '@/test/handlers';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';

const pending = {
  mfa_required: true,
  challenge_token: 'synthetic-login-challenge',
  expires_at: '2099-01-01T00:00:00Z',
  methods: ['authenticator'],
  enrollment_required: false,
  email_sent: false,
};
async function begin(overrides = {}) {
  server.use(http.post('/api/auth/login', () => HttpResponse.json({ ...pending, ...overrides })));
  const rendered = renderApp('/login', 'anonymous');
  await rendered.user.type(screen.getByLabelText('Email'), plainUser.email);
  await rendered.user.type(screen.getByLabelText('Password'), USER_PASSWORD);
  expect(screen.queryByText('Use an authenticator code')).not.toBeInTheDocument();
  await rendered.user.click(screen.getByRole('button', { name: 'Sign in' }));
  await screen.findByRole('heading', { name: /Verify your sign-in|Secure your account/ });
  return rendered;
}

describe('MFA sign-in', () => {
  it('shows the code only after password verification and authenticates only after MFA', async () => {
    let body: unknown;
    server.use(
      http.post('/api/auth/mfa/verify', async ({ request }) => {
        body = await request.json();
        return HttpResponse.json(tokenFor(plainUser));
      }),
    );
    const { user } = await begin();
    expect(useAuthStore.getState().accessToken).toBeNull();
    expect(screen.queryByLabelText('Password')).not.toBeInTheDocument();
    await user.type(screen.getByLabelText('Authenticator code'), '123456');
    await user.click(screen.getByRole('button', { name: 'Verify and sign in' }));
    await waitFor(() => {
      expect(useAuthStore.getState().status).toBe('authenticated');
    });
    expect(body).toEqual({
      challenge_token: pending.challenge_token,
      method: 'authenticator',
      code: '123456',
    });
  });

  it('keeps an invalid or expired challenge anonymous and allows restarting without the password', async () => {
    server.use(
      http.post('/api/auth/mfa/verify', () =>
        apiError(401, 'invalid_credentials', 'Invalid or expired code.'),
      ),
    );
    const { user } = await begin();
    await user.type(screen.getByLabelText('Authenticator code'), '000000');
    await user.click(screen.getByRole('button', { name: 'Verify and sign in' }));
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'The code or sign-in request is invalid or has expired.',
    );
    expect(useAuthStore.getState().status).toBe('anonymous');
    await user.click(screen.getByRole('button', { name: 'Back to sign in' }));
    expect(screen.getByLabelText('Password')).toHaveValue('');
    expect(screen.getByLabelText('Email')).toHaveValue(plainUser.email);
  });

  it('automatically shows an emailed code when email is the enabled factor', async () => {
    let body: unknown;
    server.use(
      http.post('/api/auth/mfa/verify', async ({ request }) => {
        body = await request.json();
        return HttpResponse.json(tokenFor(plainUser));
      }),
    );
    const { user } = await begin({ methods: ['email'], email_sent: true });
    expect(screen.getByRole('status')).toHaveTextContent('has been sent');
    await user.type(screen.getByLabelText('Email verification code'), '654321');
    await user.click(screen.getByRole('button', { name: 'Verify and sign in' }));
    await waitFor(() => {
      expect(useAuthStore.getState().status).toBe('authenticated');
    });
    expect(body).toEqual({
      challenge_token: pending.challenge_token,
      method: 'email',
      code: '654321',
    });
  });

  it('lets accounts with both methods request email and discards the previous method code', async () => {
    let sent = 0;
    server.use(
      http.post('/api/auth/mfa/email', () => {
        sent += 1;
        return HttpResponse.json({ ...pending, email_sent: true });
      }),
    );
    const { user } = await begin({ methods: ['authenticator', 'email'] });
    await user.type(screen.getByLabelText('Authenticator code'), '123456');
    await user.click(screen.getByRole('button', { name: 'Email code' }));
    await user.click(screen.getByRole('button', { name: 'Send email code' }));
    expect(await screen.findByLabelText('Email verification code')).toHaveValue('');
    expect(sent).toBe(1);
    await user.click(screen.getByRole('button', { name: 'Send a new code' }));
    await waitFor(() => {
      expect(sent).toBe(2);
    });
  });

  it('requires an administrator to enrol before issuing an authenticated session', async () => {
    server.use(
      http.post('/api/auth/mfa/enrol-app', () =>
        HttpResponse.json({
          secret: 'SYNTHETICSETUPKEY',
          provisioning_uri: 'otpauth://totp/test',
          expires_in: 600,
        }),
      ),
      http.post('/api/auth/mfa/verify', () => HttpResponse.json(tokenFor(adminUser))),
    );
    const { user, router } = await begin({ enrollment_required: true });
    expect(screen.getByText(/Administrators must enable/)).toBeInTheDocument();
    expect(useAuthStore.getState().accessToken).toBeNull();
    expect(screen.queryByLabelText('Authenticator code')).not.toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Set up authenticator app' }));
    expect(await screen.findByText('SYNTHETICSETUPKEY')).toBeVisible();
    expect(
      screen.getByRole('img', { name: 'Scan this QR code with your authenticator app' }),
    ).toBeVisible();
    await user.type(screen.getByLabelText('Authenticator code'), '123456');
    await user.click(screen.getByRole('button', { name: 'Enable MFA and continue' }));
    await waitFor(() => {
      expect(router.state.location.pathname).toBe('/admin');
    });
  });
});

it('discards verification when its page is abandoned and another identity signs in', async () => {
  let release: (() => void) | undefined;
  const response = new Promise<void>((resolve) => {
    release = resolve;
  });
  let started = false;
  let aborted = false;
  server.use(
    http.post('/api/auth/mfa/verify', async ({ request }) => {
      request.signal.addEventListener('abort', () => {
        aborted = true;
      });
      started = true;
      await response;
      return HttpResponse.json(tokenFor(plainUser));
    }),
  );
  const { user } = await begin();
  await user.type(screen.getByLabelText('Authenticator code'), '123456');
  await user.click(screen.getByRole('button', { name: 'Verify and sign in' }));
  await waitFor(() => {
    expect(started).toBe(true);
  });
  await user.click(screen.getByRole('link', { name: 'Sign up' }));
  await screen.findByRole('heading', { name: 'Request an account' });
  await waitFor(() => {
    expect(aborted).toBe(true);
  });
  await act(async () => {
    useAuthStore.getState().setSession(tokenFor(adminUser));
    release?.();
    await response;
  });
  expect(useAuthStore.getState().user?.id).toBe(adminUser.id);
});

it('accepts a one-use recovery code only after the password challenge', async () => {
  let body: unknown;
  server.use(
    http.post('/api/auth/mfa/verify', async ({ request }) => {
      body = await request.json();
      return HttpResponse.json(tokenFor(plainUser));
    }),
  );
  const { user } = await begin({ methods: ['authenticator', 'recovery'] });
  await user.click(screen.getByRole('button', { name: 'Recovery code' }));
  const code = 'abcd-1234-abcd-1234-abcd-1234-abcd-1234';
  await user.type(screen.getByLabelText('Recovery code'), code);
  expect(screen.queryByRole('button', { name: 'Send email code' })).not.toBeInTheDocument();
  await user.click(screen.getByRole('button', { name: 'Verify and sign in' }));
  await waitFor(() => expect(useAuthStore.getState().status).toBe('authenticated'));
  expect(body).toEqual({ challenge_token: pending.challenge_token, method: 'recovery', code });
});
