import { render, screen, waitFor } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';

import { useAuthStore } from '@/stores/auth';
import { apiError } from '@/test/handlers';
import { applySession, renderApp } from '@/test/render';
import { server } from '@/test/server';

import { TotpSettingsPage } from './TotpSettingsPage';

function settings(methods: ('authenticator' | 'email')[] = [], required = false, available = true) {
  server.use(
    http.get('/api/auth/mfa', () =>
      HttpResponse.json({
        methods,
        required,
        available_methods: available ? ['authenticator', 'email'] : [],
      }),
    ),
  );
  applySession(required ? 'admin' : 'user');
  return { user: userEvent.setup(), ...render(<TotpSettingsPage />) };
}
const enrolment = { secret: 'TEST-SETUP-KEY', provisioning_uri: 'otpauth://test', expires_in: 600 };
const pending = {
  mfa_required: true,
  challenge_token: 'synthetic-challenge',
  expires_at: '2026-09-06T12:00:00Z',
  methods: ['email'],
  email_sent: true,
  enrollment_required: false,
};

describe('personal MFA settings', () => {
  it('shows loading and a status error', async () => {
    server.use(
      http.get('/api/auth/mfa', () => apiError(503, 'unavailable', 'Settings are unavailable.')),
    );
    applySession('user');
    render(<TotpSettingsPage />);
    expect(screen.getByText('Loading security settings...')).toBeInTheDocument();
    expect(await screen.findByRole('alert')).toHaveTextContent('Settings are unavailable.');
    expect(screen.queryByRole('button')).not.toBeInTheDocument();
  });

  it('makes personal security available to a non-administrator', async () => {
    renderApp('/account/security', 'user');
    expect(
      await screen.findByRole('heading', { name: 'Multi-factor authentication' }),
    ).toBeVisible();
  });

  it('explains unavailable methods without offering setup', async () => {
    settings([], false, false);
    expect(await screen.findByRole('button', { name: 'Set up authenticator app' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Set up email verification' })).toBeDisabled();
    expect(screen.getAllByText('Unavailable. Contact your administrator.')).toHaveLength(2);
  });

  it('prevents an administrator removing the last enabled method', async () => {
    settings(['authenticator'], true);
    expect(await screen.findByRole('button', { name: 'Disable authenticator app' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Set up email verification' })).toBeEnabled();
    expect(screen.getByText(/must keep at least one/)).toBeInTheDocument();
  });

  it('enrols an ordinary account, confirms its code and ends the current session', async () => {
    let enrolBody: unknown;
    let confirmBody: unknown;
    server.use(
      http.post('/api/auth/totp/enrol', async ({ request }) => {
        enrolBody = await request.json();
        return HttpResponse.json(enrolment);
      }),
      http.post('/api/auth/totp/confirm', async ({ request }) => {
        confirmBody = await request.json();
        return new HttpResponse(null, { status: 204 });
      }),
    );
    const { user } = settings();
    await user.click(await screen.findByRole('button', { name: 'Set up authenticator app' }));
    await user.type(screen.getByLabelText('Current password'), 'test-password');
    await user.click(screen.getByRole('button', { name: 'Continue setup' }));
    expect(enrolBody).toEqual({ password: 'test-password' });
    expect(await screen.findByLabelText('Authenticator setup key')).toHaveValue('TEST-SETUP-KEY');
    expect(screen.queryByLabelText('Current password')).not.toBeInTheDocument();
    expect(sessionStorage.length).toBe(0);
    expect(localStorage.length).toBe(0);
    await user.type(screen.getByLabelText('Authenticator code'), '123456');
    await user.click(screen.getByRole('button', { name: 'Confirm and enable' }));
    await waitFor(() => expect(useAuthStore.getState().status).toBe('anonymous'));
    expect(confirmBody).toEqual({ code: '123456' });
    expect(screen.queryByLabelText('Authenticator setup key')).not.toBeInTheDocument();
  });

  it('retains pending setup on verification failure and clears secrets when cancelled', async () => {
    server.use(
      http.post('/api/auth/totp/enrol', () => HttpResponse.json(enrolment)),
      http.post('/api/auth/totp/confirm', () => apiError(422, 'invalid_request', 'Code rejected.')),
    );
    const { user } = settings();
    await user.click(await screen.findByRole('button', { name: 'Set up authenticator app' }));
    await user.type(screen.getByLabelText('Current password'), 'test-password');
    await user.click(screen.getByRole('button', { name: 'Continue setup' }));
    await user.type(await screen.findByLabelText('Authenticator code'), '123456');
    await user.click(screen.getByRole('button', { name: 'Confirm and enable' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Code rejected.');
    expect(useAuthStore.getState().status).toBe('authenticated');
    await user.click(screen.getByRole('button', { name: 'Cancel' }));
    expect(screen.queryByLabelText('Authenticator setup key')).not.toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Set up authenticator app' }));
    expect(screen.getByLabelText('Current password')).toHaveValue('');
  });

  it('disables an authenticator with both proofs', async () => {
    let body: unknown;
    server.use(
      http.post('/api/auth/totp/disable', async ({ request }) => {
        body = await request.json();
        return new HttpResponse(null, { status: 204 });
      }),
    );
    const { user } = settings(['authenticator']);
    await user.click(await screen.findByRole('button', { name: 'Disable authenticator app' }));
    await user.type(screen.getByLabelText('Current password'), 'test-password');
    await user.type(screen.getByLabelText('Authenticator code'), '123456');
    await user.click(screen.getByRole('button', { name: 'Confirm and disable' }));
    await waitFor(() => expect(useAuthStore.getState().status).toBe('anonymous'));
    expect(body).toEqual({ password: 'test-password', code: '123456' });
  });

  it.each(['enrol', 'disable'] as const)(
    'keeps the session after an email %s code typo without retrying automatically',
    async (operation) => {
      let confirmations = 0;
      let refreshes = 0;
      server.use(
        http.post(`/api/auth/mfa/email/${operation}`, () => HttpResponse.json(pending)),
        http.post(`/api/auth/mfa/email/${operation}/confirm`, () => {
          confirmations += 1;
          return confirmations === 1
            ? apiError(422, 'invalid_request', 'The verification code is incorrect.')
            : new HttpResponse(null, { status: 204 });
        }),
        http.post('/api/auth/refresh', () => {
          refreshes += 1;
          return apiError(401, 'invalid_refresh', 'Session expired.');
        }),
      );
      const { user } = settings(operation === 'disable' ? ['email'] : []);
      await user.click(
        await screen.findByRole('button', {
          name: `${operation === 'disable' ? 'Disable' : 'Set up'} email verification`,
        }),
      );
      await user.type(screen.getByLabelText('Current password'), 'test-password');
      await user.click(screen.getByRole('button', { name: 'Send verification code' }));
      await user.type(await screen.findByLabelText('Email verification code'), '111111');
      const confirmLabel = `Confirm and ${operation === 'disable' ? 'disable' : 'enable'}`;
      await user.click(screen.getByRole('button', { name: confirmLabel }));
      expect(await screen.findByRole('alert')).toHaveTextContent(
        'The verification code is incorrect.',
      );
      expect(confirmations).toBe(1);
      expect(refreshes).toBe(0);
      expect(useAuthStore.getState().status).toBe('authenticated');
      await user.clear(screen.getByLabelText('Email verification code'));
      await user.type(screen.getByLabelText('Email verification code'), '123456');
      await user.click(screen.getByRole('button', { name: confirmLabel }));
      await waitFor(() => expect(useAuthStore.getState().status).toBe('anonymous'));
      expect(confirmations).toBe(2);
      expect(refreshes).toBe(0);
    },
  );

  it.each(['enrol', 'disable'] as const)(
    'confirms email %s before revoking the session',
    async (operation) => {
      let startBody: unknown;
      let confirmBody: unknown;
      server.use(
        http.post(`/api/auth/mfa/email/${operation}`, async ({ request }) => {
          startBody = await request.json();
          return HttpResponse.json(pending);
        }),
        http.post(`/api/auth/mfa/email/${operation}/confirm`, async ({ request }) => {
          confirmBody = await request.json();
          return new HttpResponse(null, { status: 204 });
        }),
      );
      const { user } = settings(operation === 'disable' ? ['email'] : []);
      await user.click(
        await screen.findByRole('button', {
          name: `${operation === 'disable' ? 'Disable' : 'Set up'} email verification`,
        }),
      );
      await user.type(screen.getByLabelText('Current password'), 'test-password');
      await user.click(screen.getByRole('button', { name: 'Send verification code' }));
      await user.type(await screen.findByLabelText('Email verification code'), '123456');
      expect(startBody).toEqual({ password: 'test-password' });
      expect(useAuthStore.getState().status).toBe('authenticated');
      await user.click(
        screen.getByRole('button', {
          name: `Confirm and ${operation === 'disable' ? 'disable' : 'enable'}`,
        }),
      );
      await waitFor(() => expect(useAuthStore.getState().status).toBe('anonymous'));
      expect(confirmBody).toEqual({ challenge_token: 'synthetic-challenge', code: '123456' });
    },
  );
});
