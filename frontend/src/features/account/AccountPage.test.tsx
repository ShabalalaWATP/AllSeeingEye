import { act, fireEvent, screen, waitFor, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { describe, expect, it, vi } from 'vitest';

import { useAuthStore } from '@/stores/auth';
import { plainUser, tokenFor, USER_PASSWORD } from '@/test/fixtures';
import { apiError } from '@/test/handlers';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';
import * as accountApi from '@/lib/api/account';

const NEW_PASSWORD = 'A new meaningful passphrase 2026';
async function fill(user: ReturnType<typeof renderApp>['user'], confirmation = NEW_PASSWORD) {
  await user.type(await screen.findByLabelText('Current password'), USER_PASSWORD);
  await user.type(screen.getByLabelText('New password'), NEW_PASSWORD);
  await user.type(screen.getByLabelText('Confirm new password'), confirmation);
}

describe('account settings', () => {
  it.each(['user', 'manager', 'admin'] as const)(
    'shows %s identity with account controls and a teams link',
    async (role) => {
      useAuthStore.getState().setSession(tokenFor({ ...plainUser, role }));
      renderApp('/account?section=security');
      expect(await screen.findByRole('heading', { name: 'Account' })).toBeVisible();
      expect(screen.getByText(plainUser.email)).toBeVisible();
      expect(screen.getByRole('link', { name: 'View your teams' })).toHaveAttribute(
        'href',
        '/teams',
      );
      expect(screen.getByRole('form', { name: 'Change password' })).toBeVisible();
      expect(screen.queryByRole('combobox', { name: 'Account role' })).not.toBeInTheDocument();
    },
  );

  it('requires authentication', async () => {
    const { router } = renderApp('/account', 'anonymous');
    expect(await screen.findByRole('heading', { name: 'Sign in' })).toBeVisible();
    expect(router.state.location.pathname).toBe('/login');
  });

  it('rejects mismatches and incomplete authenticator codes without submitting', async () => {
    server.use(
      http.get('/api/auth/mfa', () =>
        HttpResponse.json({
          methods: ['authenticator'],
          available_methods: ['authenticator'],
          required: false,
        }),
      ),
    );
    let requests = 0;
    server.use(
      http.post('/api/me/password', () => {
        requests += 1;
        return new HttpResponse(null, { status: 204 });
      }),
    );
    const { user } = renderApp('/account?section=security', 'user');
    await fill(user, 'A different confirmation');
    await user.click(screen.getByRole('button', { name: 'Change password' }));
    expect(screen.getByRole('alert')).toHaveTextContent('The two passwords do not match.');
    await user.clear(screen.getByLabelText('Confirm new password'));
    await user.type(screen.getByLabelText('Confirm new password'), NEW_PASSWORD);
    await user.type(screen.getByLabelText('Authenticator code'), '123');
    await user.click(screen.getByRole('button', { name: 'Change password' }));
    expect(screen.getByRole('alert')).toHaveTextContent('Enter a six-digit verification code');
    expect(requests).toBe(0);
  });

  it('shows wrong-proof and password-policy failures while retaining the session', async () => {
    server.use(
      http.post('/api/me/password', () =>
        apiError(
          422,
          'invalid_request',
          'The current password or authenticator code is incorrect.',
        ),
      ),
    );
    const { user } = renderApp('/account?section=security', 'user');
    await fill(user);
    await user.click(screen.getByRole('button', { name: 'Change password' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('current password or authenticator');
    expect(useAuthStore.getState().status).toBe('authenticated');
    server.use(
      http.post('/api/me/password', () =>
        apiError(422, 'weak_password', 'Password not accepted.', {
          new_password: 'Choose a less common password.',
        }),
      ),
    );
    await user.click(screen.getByRole('button', { name: 'Change password' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Choose a less common password.');
    expect(useAuthStore.getState().status).toBe('authenticated');
  });

  it('disables editing while saving and signs out with a success notice', async () => {
    server.use(
      http.get('/api/auth/mfa', () =>
        HttpResponse.json({
          methods: ['authenticator'],
          available_methods: ['authenticator'],
          required: false,
        }),
      ),
    );
    let release: () => void = () => undefined;
    const pending = new Promise<void>((resolve) => {
      release = resolve;
    });
    const bodies: unknown[] = [];
    server.use(
      http.post('/api/me/password', async ({ request }) => {
        bodies.push(await request.json());
        await pending;
        return new HttpResponse(null, { status: 204 });
      }),
    );
    const { user, router } = renderApp('/account?section=security', 'user');
    await fill(user);
    await user.type(screen.getByLabelText('Authenticator code'), '123456');
    await user.click(screen.getByRole('button', { name: 'Change password' }));
    expect(await screen.findByRole('button', { name: 'Please wait...' })).toBeDisabled();
    expect(screen.getByLabelText('Current password')).toBeDisabled();
    fireEvent.submit(screen.getByRole('form', { name: 'Change password' }));
    await waitFor(() => expect(bodies).toHaveLength(1));
    expect(bodies[0]).toEqual({
      current_password: USER_PASSWORD,
      new_password: NEW_PASSWORD,
      totp_code: '123456',
    });
    release();
    expect(
      await screen.findByText('Your password has changed. Sign in with your new password.'),
    ).toBeVisible();
    expect(router.state.location.pathname).toBe('/login');
    expect(useAuthStore.getState().status).toBe('anonymous');
    expect(useAuthStore.getState().accessToken).toBeNull();
  });

  it('verifies an email code before changing an email-protected password', async () => {
    let proof: unknown;
    let passwordBody: unknown;
    server.use(
      http.get('/api/auth/mfa', () =>
        HttpResponse.json({ methods: ['email'], available_methods: ['email'], required: false }),
      ),
      http.post('/api/auth/mfa/password-change', async ({ request }) => {
        proof = await request.json();
        return HttpResponse.json({
          mfa_required: true,
          challenge_token: 'password-challenge',
          expires_at: '2026-09-06T12:00:00Z',
          methods: ['email'],
          enrollment_required: false,
          email_sent: true,
        });
      }),
      http.post('/api/me/password', async ({ request }) => {
        passwordBody = await request.json();
        return new HttpResponse(null, { status: 204 });
      }),
    );
    const { user } = renderApp('/account?section=security', 'user');
    await fill(user);
    expect(screen.queryByLabelText('Authenticator code')).not.toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Send verification code' }));
    await user.type(await screen.findByLabelText('Email verification code'), '123456');
    expect(proof).toEqual({ password: USER_PASSWORD });
    expect(passwordBody).toBeUndefined();
    await user.click(screen.getByRole('button', { name: 'Change password' }));
    await waitFor(() => expect(useAuthStore.getState().status).toBe('anonymous'));
    expect(passwordBody).toEqual({
      current_password: USER_PASSWORD,
      new_password: NEW_PASSWORD,
      totp_code: null,
      mfa_challenge_token: 'password-challenge',
      mfa_code: '123456',
    });
  });

  it('allows correcting the password proof for an email challenge without refreshing the session', async () => {
    let proofs = 0;
    let refreshes = 0;
    server.use(
      http.get('/api/auth/mfa', () =>
        HttpResponse.json({ methods: ['email'], available_methods: ['email'], required: false }),
      ),
      http.post('/api/auth/mfa/password-change', () => {
        proofs += 1;
        return proofs === 1
          ? apiError(422, 'invalid_request', 'The current password is incorrect.')
          : HttpResponse.json({
              mfa_required: true,
              challenge_token: 'password-challenge',
              expires_at: '2026-09-06T12:00:00Z',
              methods: ['email'],
              enrollment_required: false,
              email_sent: true,
            });
      }),
      http.post('/api/auth/refresh', () => {
        refreshes += 1;
        return apiError(401, 'invalid_refresh', 'Session expired.');
      }),
    );
    const { user } = renderApp('/account?section=security', 'user');
    await fill(user);
    await user.click(screen.getByRole('button', { name: 'Send verification code' }));
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'The current password is incorrect.',
    );
    expect(proofs).toBe(1);
    expect(refreshes).toBe(0);
    expect(useAuthStore.getState().status).toBe('authenticated');
    await user.clear(screen.getByLabelText('Current password'));
    await user.type(screen.getByLabelText('Current password'), 'Corrected password');
    await user.click(screen.getByRole('button', { name: 'Send verification code' }));
    expect(await screen.findByLabelText('Email verification code')).toBeVisible();
    expect(proofs).toBe(2);
    expect(refreshes).toBe(0);
    expect(useAuthStore.getState().status).toBe('authenticated');
  });

  it('can reveal passwords from the keyboard without submitting', async () => {
    const { user } = renderApp('/account?section=security', 'user');
    await fill(user);
    await user.tab();
    const show = screen.getByRole('button', { name: 'Show passwords' });
    expect(show).toHaveFocus();
    await user.keyboard('{Enter}');
    const form = screen.getByRole('form', { name: 'Change password' });
    expect(within(form).getByLabelText('New password')).toHaveAttribute('type', 'text');
    await user.keyboard('{Enter}');
    expect(within(form).getByLabelText('New password')).toHaveAttribute('type', 'password');
    expect(useAuthStore.getState().status).toBe('authenticated');
  });

  it('does not sign out a replacement identity when an earlier request finishes', async () => {
    let release: () => void = () => undefined;
    const pending = new Promise<void>((resolve) => {
      release = resolve;
    });
    vi.spyOn(accountApi, 'changePassword').mockReturnValue(pending);
    const { user } = renderApp('/account?section=security', 'user');
    await fill(user);
    await user.click(screen.getByRole('button', { name: 'Change password' }));
    const replacement = {
      ...plainUser,
      id: '99999999-9999-4999-8999-999999999999',
      display_name: 'Another analyst',
    };
    act(() => useAuthStore.getState().setSession(tokenFor(replacement)));
    await act(async () => {
      release();
      await pending;
    });
    expect(useAuthStore.getState().status).toBe('authenticated');
    expect(useAuthStore.getState().user?.id).toBe(replacement.id);
    expect(screen.getByLabelText('Current password')).toHaveValue('');
  });
});
