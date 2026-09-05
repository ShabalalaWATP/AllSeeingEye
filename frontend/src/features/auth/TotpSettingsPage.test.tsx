import { render, screen, waitFor } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { delay, http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';

import { useAuthStore } from '@/stores/auth';
import { apiError } from '@/test/handlers';
import { applySession } from '@/test/render';
import { server } from '@/test/server';

import { TotpSettingsPage } from './TotpSettingsPage';

function settings(enabled = false, available = true) {
  server.use(http.get('/api/auth/totp', () => HttpResponse.json({ enabled, available })));
  applySession('admin');
  return { user: userEvent.setup(), ...render(<TotpSettingsPage />) };
}

describe('TotpSettingsPage', () => {
  it('shows loading and a status error', async () => {
    server.use(
      http.get('/api/auth/totp', async () => {
        await delay(50);
        return apiError(503, 'unavailable', 'Settings are unavailable.');
      }),
    );
    applySession('admin');
    const view = render(<TotpSettingsPage />);
    expect(screen.getByText('Loading second-factor settings...')).toBeInTheDocument();
    expect(await screen.findByRole('alert')).toHaveTextContent('Settings are unavailable.');
    expect(screen.queryByRole('button')).not.toBeInTheDocument();
    view.unmount();
  });

  it('explains a missing server encryption key', async () => {
    settings(false, false);
    expect(await screen.findByText(/server encryption key must be configured/)).toBeInTheDocument();
    expect(screen.queryByRole('button')).not.toBeInTheDocument();
  });

  it('enrols with the password, confirms a code and ends the current session', async () => {
    let enrolBody: unknown;
    let confirmBody: unknown;
    server.use(
      http.post('/api/auth/totp/enrol', async ({ request }) => {
        enrolBody = await request.json();
        return HttpResponse.json({
          secret: 'TEST-SETUP-KEY',
          provisioning_uri: 'otpauth://test',
          expires_in: 600,
        });
      }),
      http.post('/api/auth/totp/confirm', async ({ request }) => {
        confirmBody = await request.json();
        return new HttpResponse(null, { status: 204 });
      }),
    );
    const { user } = settings();
    await user.type(await screen.findByLabelText('Current password'), 'test-password');
    await user.click(screen.getByRole('button', { name: 'Set up TOTP' }));
    expect(enrolBody).toEqual({ password: 'test-password' });
    expect(await screen.findByLabelText('Authenticator setup key')).toHaveValue('TEST-SETUP-KEY');
    expect(screen.queryByLabelText('Current password')).not.toBeInTheDocument();
    expect(sessionStorage.length).toBe(0);
    expect(localStorage.length).toBe(0);
    await user.type(screen.getByLabelText('Authenticator code'), '123456');
    await user.click(screen.getByRole('button', { name: 'Confirm and enable TOTP' }));
    await waitFor(() => {
      expect(useAuthStore.getState().status).toBe('anonymous');
    });
    expect(confirmBody).toEqual({ code: '123456' });
    expect(screen.queryByLabelText('Authenticator setup key')).not.toBeInTheDocument();
  });

  it('shows enrolment and confirmation errors without clearing the pending setup', async () => {
    server.use(
      http.post('/api/auth/totp/enrol', () =>
        apiError(422, 'invalid_request', 'Password rejected.'),
      ),
    );
    const { user } = settings();
    await user.type(await screen.findByLabelText('Current password'), 'test-password');
    await user.click(screen.getByRole('button', { name: 'Set up TOTP' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Password rejected.');
    server.use(
      http.post('/api/auth/totp/enrol', () =>
        HttpResponse.json({
          secret: 'TEST-KEY',
          provisioning_uri: 'otpauth://test',
          expires_in: 600,
        }),
      ),
      http.post('/api/auth/totp/confirm', () => apiError(422, 'invalid_request', 'Code rejected.')),
    );
    await user.click(screen.getByRole('button', { name: 'Set up TOTP' }));
    await user.type(await screen.findByLabelText('Authenticator code'), '123456');
    await user.click(screen.getByRole('button', { name: 'Confirm and enable TOTP' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Code rejected.');
    expect(screen.getByLabelText('Authenticator setup key')).toHaveValue('TEST-KEY');
    expect(useAuthStore.getState().status).toBe('authenticated');
    await user.click(screen.getByRole('button', { name: 'Restart setup' }));
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    expect(screen.queryByLabelText('Authenticator setup key')).not.toBeInTheDocument();
    expect(screen.getByLabelText('Current password')).toHaveValue('');
  });

  it('disables only after submitting both proofs and shows failures', async () => {
    let received: unknown;
    server.use(
      http.post('/api/auth/totp/disable', () =>
        apiError(422, 'invalid_request', 'Code already used.'),
      ),
    );
    const { user } = settings(true);
    await user.type(await screen.findByLabelText('Current password'), 'test-password');
    await user.type(screen.getByLabelText('Authenticator code'), '123456');
    await user.click(screen.getByRole('button', { name: 'Disable TOTP' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Code already used.');
    expect(useAuthStore.getState().status).toBe('authenticated');
    server.use(
      http.post('/api/auth/totp/disable', async ({ request }) => {
        received = await request.json();
        return new HttpResponse(null, { status: 204 });
      }),
    );
    await user.click(screen.getByRole('button', { name: 'Disable TOTP' }));
    await waitFor(() => {
      expect(useAuthStore.getState().status).toBe('anonymous');
    });
    expect(received).toEqual({ password: 'test-password', code: '123456' });
  });
});
