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
      renderApp('/account');
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
    let requests = 0;
    server.use(
      http.post('/api/me/password', () => {
        requests += 1;
        return new HttpResponse(null, { status: 204 });
      }),
    );
    const { user } = renderApp('/account', 'user');
    await fill(user, 'A different confirmation');
    await user.click(screen.getByRole('button', { name: 'Change password' }));
    expect(screen.getByRole('alert')).toHaveTextContent('The two passwords do not match.');
    await user.clear(screen.getByLabelText('Confirm new password'));
    await user.type(screen.getByLabelText('Confirm new password'), NEW_PASSWORD);
    await user.click(screen.getByText('Use an authenticator code'));
    await user.type(screen.getByLabelText('Authenticator code'), '123');
    await user.click(screen.getByRole('button', { name: 'Change password' }));
    expect(screen.getByRole('alert')).toHaveTextContent('Enter a six-digit authenticator code');
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
    const { user } = renderApp('/account', 'user');
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
    const { user, router } = renderApp('/account', 'user');
    await fill(user);
    await user.click(screen.getByText('Use an authenticator code'));
    await user.type(screen.getByLabelText('Authenticator code'), '123456');
    await user.click(screen.getByRole('button', { name: 'Change password' }));
    expect(await screen.findByRole('button', { name: 'Changing password…' })).toBeDisabled();
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

  it('can reveal passwords from the keyboard without submitting', async () => {
    const { user } = renderApp('/account', 'user');
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
    const { user } = renderApp('/account', 'user');
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
